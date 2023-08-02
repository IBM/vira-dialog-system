#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

import os
import numpy as np
from time import time
from components.kp_matching import KpMatching
from components.response_selection import ResponseSelection
from components.response_db import ResponseDBML
from components.connecting_text_library import ConnectingTextLibraryML
from components.intent_detection import IntentDetection
from components.persona_detection import PersonaDetection
from components.concern_classifier import LexicalConcernClassifier
from components.profanity_classifier import ProfanityClassifier
from tools.db_manager import DBManager
from tools.coref_resolution import SimpleCoRefResolution
# from tools.code_generator import code_generator
from tools.kp_utils import KPUtilsML
from tools.opening_survey import OpeningSurveyML
from tools.singleton import Singleton
from tools.translator import WatsonTranslator


class DialogManager(metaclass=Singleton):
    RANDOM_SEED = 1024 * 1024
    DATA_DIR = os.path.join('data')

    def __init__(self):
        self.configuration = DBManager().read_configuration()
        self.advisory_mode = self.configuration.get_advisory_mode()
        self.random_state = np.random.RandomState(self.RANDOM_SEED)
        self.response_db_ml = ResponseDBML(self.configuration.get_language_codes())
        self.kp_utils_ml = KPUtilsML(self.configuration.get_language_codes())
        self.kp_matcher = KpMatching()
        self.response_selector = ResponseSelection(self.random_state)
        self.user_intent_detection = IntentDetection(self.advisory_mode, self.configuration, self.kp_utils_ml)
        self.connecting_text_ml = ConnectingTextLibraryML(self.advisory_mode['enabled'],
                                                          self.configuration.get_language_codes())
        self.persona_detection = PersonaDetection()
        self.coref_resolution = SimpleCoRefResolution()
        self.concern_classifier = LexicalConcernClassifier()
        self.profanity_classifier = ProfanityClassifier()
        self.opening_survey_ml = OpeningSurveyML(self.configuration, self.configuration.get_language_codes())
        self.watson_translator = WatsonTranslator(self.configuration)

    @classmethod
    def process_user_feedback(cls, session_id, message_id, feedback):
        dialog_data = DBManager().get_dialog_data(session_id)
        dialog_data.update_message_feedback(message_id, feedback)
        DBManager().commit(dialog_data)
        return {'response': None}

    @classmethod
    def process_user_survey(cls, session_id, survey):
        dialog_data = DBManager().get_dialog_data(session_id)
        dialog_data.set_survey(survey)
        DBManager().commit(dialog_data)
        return {'response': None}

    def process_new_session(self, dialog_label, campaign_id, opening_survey_flow, platform, language_code):
        if language_code is None:
            language_code = self.configuration.get_default_language()
        if opening_survey_flow is None:
            opening_survey_flow = self.opening_survey_ml[language_code].get_default_flow()
        if opening_survey_flow not in self.opening_survey_ml[language_code].get_flows():
            raise ValueError('Invalid opening survey flow: [%s]' % opening_survey_flow)
        response = self.process_user_text(session_id=None, user_arg_raw=None, feedback=False, answer=False,
                                          disable_cache=False, dialog_label=dialog_label, campaign_id=campaign_id,
                                          opening_survey_flow=opening_survey_flow, platform=platform,
                                          language_code=language_code)
        response['ui_texts'] = self.configuration.get_ui_texts(language_code)
        response['advisory_mode'] = self.advisory_mode['enabled']
        response['language_direction'] = self.configuration.get_language_direction(language_code)
        return response

    def process_opening_survey(self, dialog_data, answer, language_code):

        # get the session id
        session_id = str(dialog_data.get_dialog_id())

        # in case this is a response to a previous question
        if answer is not None:
            dialog_data.update_question_answer(answer)

            # sync to db
            DBManager().commit(dialog_data)

        # get the next question
        question = self.opening_survey_ml[language_code].get_next_question(dialog_data)

        if question:
            # store the question in the dialog data
            dialog_data.add_question(question)

            # sync to db
            DBManager().commit(dialog_data)

            # submit survey question
            response = {
                'question': question['question'],
                'choices': question['choices'],
                "session_id": session_id,
                'opening_survey': True,
            }
        else:
            # get the closing comment intent
            survey_closing_intent = self.user_intent_detection.apply_to_opening_survey(
                self.opening_survey_ml[language_code].get_survey_closing_intent())

            # create text for the system closing comment
            connecting_text = self.connecting_text_ml[language_code]
            text = connecting_text.rephrase([], intent=survey_closing_intent['label'], persona='general')[0].text

            # get the intent for the dialog intro
            post_survey_intent = self.user_intent_detection.apply_to_opening_survey(
                self.opening_survey_ml[language_code].get_post_survey_intent())

            # switch to the normal dialog flow
            response = self.process_user_text(session_id, user_arg_raw=None, feedback=False, answer=False,
                                              disable_cache=False, intent=post_survey_intent)

            # add the survey closing comment
            response['survey_response'] = text

        return response

    def discontinue_opening_survey(self, dialog_data):
        # mark the opening survey of this session as discontinued
        dialog_data.set_opening_survey_discontinued()

        # sync to db
        DBManager().commit(dialog_data)

        # get the session id
        session_id = str(dialog_data.get_dialog_id())

        # run with empty user text just for generating the messages
        # array starting with an empty user message
        self.process_user_text(session_id, user_arg_raw=None, feedback=False,
                               answer=False, disable_cache=False)

        # read the updated dialog data
        dialog_data = DBManager().get_dialog_data(session_id)

        # we won't show the system opening so mark it as hidden
        dialog_data.set_skipped_system_opening()

        # sync to db
        DBManager().commit(dialog_data)

    # con_arg => con_kp => pro_kp => pro_args
    def process_user_text(self, session_id, user_arg_raw, feedback, answer, disable_cache,
                          dialog_label=None, campaign_id=None, intent=None,
                          opening_survey_flow=None, platform=None, language_code=None):
        start_time = time()

        # retrieve the dialog data
        dialog_data = DBManager().get_dialog_data(session_id, dialog_label, campaign_id,
                                                  opening_survey_flow, platform, language_code)

        if language_code is None:
            language_code = dialog_data.get_language_code()

        response_db = self.response_db_ml[language_code]

        campaign_id = dialog_data.get_campaign_id()

        # switch to the opening survey if its enabled and not over yet
        if self.opening_survey_ml[language_code].is_enabled() and \
                not self.opening_survey_ml[language_code].discontinued(dialog_data):
            if self.opening_survey_ml[language_code].waiting_for_answer(dialog_data) and not answer:
                # we waited for answer but the user sent a question/concern, so we
                # discontinue the survey and after that handle the user input normally.
                self.discontinue_opening_survey(dialog_data)

                # re-read the dialog data since it was updated
                dialog_data = DBManager().get_dialog_data(session_id)

            elif self.opening_survey_ml[language_code].has_more_questions(dialog_data) or answer:
                # we just started the chat, so we have more questions, or we are in the middle
                # of the survey and still have more questions, or we don't have any more
                # questions but the user sent an answer to the last question.
                return self.process_opening_survey(dialog_data=dialog_data, answer=user_arg_raw,
                                                   language_code=language_code)

        feedback_options = self.configuration.get_feedback_options(language_code)

        # extract the history as a list of strings and add the new user argument if it exists
        dialog_history = dialog_data.get_history()

        system_argument_history = dialog_data.get_system_argument_history()

        skip_kp_feedback = False
        con_kp_candidates = None
        con_kps = None
        con_kp_scores = None
        is_concern = False
        is_profanity = False
        # whether to request feedback or not
        request_feedback = False

        user_arg_translated = self.watson_translator.translate(user_arg_raw, language_code)[0] if \
            user_arg_raw is not None and self.configuration.is_translator_enabled(language_code) and not feedback \
            else user_arg_raw
        # apply co-ref resolution to the user-arg
        user_arg = self.coref_resolution.apply(user_arg_translated) if user_arg_translated is not None else None

        # if the user arg is a feedback, it can be either a kp or
        # 'none of the above' or 'not a concern'. in that case we
        # handle the intent and con_kp as a special case. if the
        # user arg is not a feedback (and not none) we apply the
        # kp-matching and intent detection.
        con_kp = None
        if feedback:
            intent, new_kp = self.user_intent_detection.apply_to_feedback(feedback_options, user_arg_raw,
                                                                          dialog_data.dialog_data, language_code)
            if new_kp:
                # if the feedback is a new kp, we first need
                # to apply reversed-mapping from a question
                # form to the normal norm.
                con_kp = self.kp_utils_ml[language_code].get_kp_by_qform(user_arg_raw)
                is_concern = True
                request_feedback = True
        else:
            if user_arg is not None:
                dialog_history.append(user_arg)

                # check if we have a profanity in the text
                is_profanity = self.profanity_classifier.apply(user_arg)

                if not is_profanity:

                    # check if we have a concern in the user-arg
                    is_concern = self.concern_classifier.apply(user_arg, dialog_data)

                    if is_concern:
                        if self.advisory_mode['enabled']:
                            request_feedback = True

                            # determine the number of kps and get the top k
                            n_candidates = self.advisory_mode['candidates']
                            con_kps, con_kp_scores = self.kp_matcher.get_top_k_kps(arg=user_arg, k=n_candidates,
                                                                                   disable_cache=disable_cache,
                                                                                   response_db_kps=response_db.get_con_kps())

                            # if our top kp is above the confidence threshold
                            # we will use it in the response
                            if self.kp_matcher.is_confident(con_kp_scores[0]):
                                con_kp = con_kps[0]

                            # detect intent, context is a list of all utterances except the last user_arg
                            intent = self.user_intent_detection.apply(user_arg,
                                                                      dialog_data=dialog_data.dialog_data,
                                                                      disable_cache=disable_cache,
                                                                      con_kp=con_kp)

                            if con_kp is None:
                                # if no kp is above the confidence threshold, and the intent type is
                                # of no response (e.g. "I'm sorry I didn't understand"), then there
                                # is no point in asking the user to tell if the kp is to the point or not.
                                if self.user_intent_detection.check_no_response_intent(intent):
                                    skip_kp_feedback = True

                                # for specific intent types, we don't want to ask for any feedback
                                if self.user_intent_detection.no_feedback_intent(intent):
                                    request_feedback = False
                            # transform the candidates to question form
                            con_kp_candidates = self.kp_utils_ml[language_code].get_kps_qform(con_kps)

                            # add the common feedback options ('no concern', 'none of the above')
                            for option in feedback_options:
                                if option['candidate'] and (not option['location_specific'] or campaign_id is not None):
                                    con_kp_candidates.append(option['text'])
                        else:
                            # in normal mode, we just pick the kp with the highest likelihood.
                            con_kps, con_kp_scores = self.kp_matcher.get_top_k_kps(user_arg, 1, disable_cache)
                            if self.kp_matcher.is_confident(con_kp_scores[0]):
                                con_kp = con_kps[0]

            if intent is None:
                intent = self.user_intent_detection.apply(user_arg,
                                                          dialog_data=dialog_data.dialog_data,
                                                          disable_cache=disable_cache,
                                                          is_concern=is_concern, con_kp=con_kp,
                                                          is_profanity=is_profanity)

        # get manual mapped pro_kp
        pro_kp = response_db.get_pro_kp_mapping(con_kp)

        # detect user persona
        persona = self.persona_detection.apply(user_arg, dialog_history)

        # record the user argument and associated kp and intent in the db
        dialog_data.add_user_input(text=user_arg, keypoint=con_kp, intent=intent,
                                   feedback=feedback, orig_text=user_arg_raw,
                                   is_concern=is_concern, is_profanity=is_profanity,
                                   orig_translated_text=user_arg_translated)

        # get the arguments of the pro_kp
        pro_args = response_db.get_pro_kp_args(pro_kp, campaign_id)

        # create argument combinations
        connecting_text = self.connecting_text_ml[language_code]
        rephrased_arguments = connecting_text.rephrase(pro_args, intent=intent['label'], persona=persona)

        # select the argument by questioning a parlai model
        selected_argument, candidates, scores, orig_scores = \
            self.response_selector.apply(rephrased_arguments, dialog_history, system_argument_history)

        # extract the internal data
        base_response = selected_argument.base_response
        full_response = selected_argument.text
        canned_text = selected_argument.canned_text
        expression = selected_argument.expression

        end_time = time()

        # record the system response and associated kp in the db
        message_id = dialog_data.add_system_response(
            text=full_response, base_response=base_response, keypoint=pro_kp, candidates=candidates,
            scores=scores, orig_scores=orig_scores, canned_text=canned_text, processing_time=(end_time - start_time),
            is_concern=is_concern, request_feedback=request_feedback, skip_kp_feedback=skip_kp_feedback,
            keypoint_candidates=con_kps, keypoint_candidates_qform=con_kp_candidates)

        # determine if we should end the dialog here
        code_msg = None
        code = None

        # commit the changes in the dialog data to the database
        DBManager().commit(dialog_data)

        # whether to request feedback or not
        request_feedback = message_id > 1 and request_feedback

        return {
            'text_translated': user_arg_translated if user_arg_translated is not None else '',
            'text': user_arg_raw,
            'con_kp': con_kp if con_kp is not None else '',
            'pro_kp': pro_kp if pro_kp is not None else '',
            'pro_arg': base_response,
            'response': full_response,
            'code_msg': code_msg,
            'code': code,
            'intent': intent,
            "message_id": message_id,
            "session_id": str(dialog_data.get_dialog_id()),
            "request_feedback": request_feedback,
            'con_kps': con_kps,
            'con_kp_scores': con_kp_scores,
            "con_kp_candidates": con_kp_candidates,
            "skip_kp_feedback": skip_kp_feedback,
            "expression": expression,
            "is_concern": is_concern,
            "is_profanity": is_profanity,
        }
