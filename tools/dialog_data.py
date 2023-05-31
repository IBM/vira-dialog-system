#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

from datetime import datetime
from tools.argument import Argument


class DialogData:

    def __init__(self, dialog_id, dialog_data, dialog_opening_survey_flow, campaign_id, platform, language_code):
        self.dialog_id = dialog_id
        self.dialog_data = dialog_data
        self.dialog_opening_survey_flow = dialog_opening_survey_flow
        self.campaign_id = campaign_id
        self.platform = platform
        self.language_code = language_code

    def get_dialog_id(self):
        return self.dialog_id

    def add_user_input(self, text, keypoint, intent, feedback, orig_text, is_concern, is_profanity,
                       orig_translated_text):
        return self.add_message('user', text, keypoint, intent=intent, feedback=feedback, orig_text=orig_text,
                                is_concern=is_concern, is_profanity=is_profanity,
                                orig_translated_text=orig_translated_text)

    def add_system_response(self, text, base_response, keypoint, candidates,
                            scores, orig_scores, canned_text, processing_time,
                            is_concern, request_feedback, skip_kp_feedback,
                            keypoint_candidates, keypoint_candidates_qform):
        return self.add_message('system', text, keypoint, base_response=base_response, canned_text=canned_text,
                                candidates=candidates, scores=scores, orig_scores=orig_scores,
                                processing_time=processing_time, is_concern=is_concern,
                                request_feedback=request_feedback, skip_kp_feedback=skip_kp_feedback,
                                keypoint_candidates=keypoint_candidates,
                                keypoint_candidates_qform=keypoint_candidates_qform)

    def add_message(self, side, text, keypoint, orig_text=None, intent=None, base_response=None, canned_text=None,
                    candidates=None, scores=None, orig_scores=None, feedback=None, processing_time=None,
                    is_concern=None, request_feedback=None, skip_kp_feedback=None, keypoint_candidates=None,
                    keypoint_candidates_qform=None, is_profanity=None, orig_translated_text=None):
        if side != 'user' and side != 'system':
            raise ValueError('Unsupported side %s' % side)
        if 'messages' not in self.dialog_data:
            self.dialog_data['messages'] = []
        record = {
            "side": side,
            "text": text,
            'keypoint': keypoint,
            "date": datetime.now()
        }
        if intent:
            record['intent'] = intent
        if base_response:
            record['base_response'] = base_response
        if canned_text:
            record['canned_text'] = canned_text
        if candidates:
            record['candidates'] = candidates
        if scores:
            record['scores'] = scores
        if orig_scores:
            record['orig_scores'] = orig_scores
        if feedback is not None:
            record['is_feedback'] = feedback
        if orig_text is not None:
            record['orig_text'] = orig_text
        if processing_time is not None:
            record['processing_time'] = processing_time
        if is_concern is not None:
            record['is_concern'] = is_concern
        if request_feedback is not None:
            record['request_feedback'] = request_feedback
        if skip_kp_feedback is not None:
            record['request_thumbs_feedback'] = not skip_kp_feedback
        if keypoint_candidates is not None:
            record['keypoint_candidates'] = keypoint_candidates
        if keypoint_candidates_qform is not None:
            record['keypoint_candidates_qform'] = keypoint_candidates_qform
        if is_profanity is not None:
            record['is_profanity'] = is_profanity
        if orig_translated_text is not None:
            record['orig_translated_text'] = orig_translated_text
        self.dialog_data['messages'].append(record)
        return len(self.dialog_data['messages']) - 1

    def get_last_system_keypoint(self):
        messages = self.get_side_messages('system')
        return messages[-1]['keypoint'] if len(messages) > 0 else None

    def get_used_system_base_responses(self):
        messages = self.get_side_messages('system')
        return [message['base_response'] for message in messages if 'base_response' in message]

    def get_user_message_count_skip_feedback(self):
        user_messages = self.get_side_messages('user')
        user_messages = [message for message in user_messages
                         if 'is_feedback' not in message or
                         message['is_feedback'] is False]
        return len(user_messages)

    def get_messages(self):
        return self.dialog_data['messages']

    def get_side_messages(self, side):
        return [message for message in self.dialog_data['messages']
                if message['side'] == side and message['text'] is not None] \
            if 'messages' in self.dialog_data else []

    def get_history(self):
        return [message['text'] for message in self.dialog_data['messages']
                if message['text'] is not None] \
            if 'messages' in self.dialog_data else []

    def get_system_argument_history(self):
        messages = self.get_side_messages('system')
        return [Argument(text=m['text'], arg_type='general',
                         base_response=m['base_response'],
                         canned_text=m['canned_text'])
                for m in messages]

    def update_message_feedback(self, message_id, feedback):
        messages = self.get_messages()
        if len(messages) > message_id:
            messages[message_id]['feedback'] = feedback
        else:
            raise ValueError('Invalid message id')

    def add_appen_code(self, code):
        self.dialog_data['appen_code'] = code

    def has_appen_code(self):
        return 'appen_code' in self.dialog_data

    def get_appen_code(self):
        return self.dialog_data['appen_code'] if self.has_appen_code() else None

    def set_survey(self, survey):
        self.dialog_data['survey'] = survey

    def get_survey(self):
        return self.dialog_data['survey'] if 'survey' in self.dialog_data else None

    def set_profanity_retro(self, message_id):
        messages = self.get_messages()
        if len(messages) > message_id:
            message = messages[message_id]
            message['is_profanity'] = True
            message['is_retrospective_profanity'] = True
        else:
            raise ValueError('Invalid message id')

    def add_question(self, question):
        if 'opening_survey' not in self.dialog_data:
            self.dialog_data['opening_survey'] = []
        record = {
            "question": question,
            "question_date": datetime.now()
        }
        self.dialog_data['opening_survey'].append(record)

    def update_question_answer(self, answer):
        message = self.dialog_data['opening_survey'][-1]
        message['answer'] = answer
        message['answer_date'] = datetime.now()

    def is_opening_survey_waiting_for_answer(self):
        return 'opening_survey' in self.dialog_data and \
               'answer' not in self.dialog_data['opening_survey'][-1]

    def set_opening_survey_discontinued(self):
        message = self.dialog_data['opening_survey'][-1]
        message['discontinued'] = True

    def is_opening_survey_discontinued(self):
        return 'opening_survey' in self.dialog_data and \
               'discontinued' in self.dialog_data['opening_survey'][-1]

    def get_opening_survey_messages(self):
        return self.dialog_data['opening_survey'] if 'opening_survey' in self.dialog_data else []

    def get_opening_survey_flow(self):
        return self.dialog_opening_survey_flow

    def get_campaign_id(self):
        return self.campaign_id

    def get_platform(self):
        return self.platform

    def set_skipped_system_opening(self):
        system_messages = self.get_side_messages('system')
        system_messages[0]['skipped'] = True

    def get_language_code(self):
        return self.language_code
