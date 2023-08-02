#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

import re
from abc import abstractmethod

from assessment.operators import none_of_kps_intent, has_kp
from tools.db_manager import DBManager
from tools.service_utils import get_scores

what_else_regex = re.compile(r'what (else|other)[\w\d\s]*\?$', re.IGNORECASE)


class RuleBasedIntent:

    @abstractmethod
    def apply(self, dialog_data, **kwargs):
        pass

    @abstractmethod
    def get_name(self):
        pass


class SameKPTwiceInARow(RuleBasedIntent):

    # applied if system identifies the same kp twice in a row
    def apply(self, dialog_data, **kwargs):
        # same kp back-to-back
        if kwargs.get('con_kp', None) is not None and len(dialog_data) >= 2 \
                and has_kp(kwargs['con_kp'])(dialog_data[-2]):
            return True
        # same kp with none-of-the-above in the middle
        if kwargs.get('con_kp', None) is not None and len(dialog_data) >= 4 \
                and none_of_kps_intent(dialog_data[-2]) \
                and has_kp(kwargs['con_kp'])(dialog_data[-4]):
            return True
        return False

    def get_name(self):
        return "SAME_KP_TWICE_IN_A_ROW"


class TwoNoneOfTheAboveInARow(RuleBasedIntent):

    # applied if system did not suggest the correct kp twice in a row (not even as an alternative kp)
    def apply(self, dialog_data, **kwargs):
        if kwargs.get('new_intent', None) is not None and len(dialog_data) >= 4 \
                and dialog_data[-4]['intent']['label'] == "FEEDBACK_NONE_OF_KPS" \
                and kwargs['new_intent'] == "FEEDBACK_NONE_OF_KPS":
            return True
        return False

    def get_name(self):
        return "FEEDBACK_NONE_OF_KPS_TWO_IN_A_ROW"


class NoConcernAfterWhatElseConcernsQuestion(RuleBasedIntent):

    # applied when user expressed no concern after being asked "what else would you like to share?"
    def apply(self, dialog_data, **kwargs):
        if kwargs.get('is_concern', None) is False and \
                what_else_regex.search(dialog_data[-1]['text']) is not None:
            return True
        return False

    def get_name(self):
        return "NO_OTHER_CONCERN"


class Profanity(RuleBasedIntent):

    # checks if text was marked as profanity
    def apply(self, dialog_data, **kwargs):
        return kwargs.get('is_profanity', None) is True

    def get_name(self):
        return "PROFANITY"


intent_classes = ['greeting', 'farewell', 'negative_reaction', 'positive_reaction', 'concern', 'query', 'default']


def create_intent(label, score, source=None):
    intent = {
        "label": label,
        "score": score,
        "original_label": label,
    }
    if source is not None:
        intent["source"] = source
    return intent


class IntentClassifierClient:

    def __init__(self):
        configuration = DBManager().read_configuration()
        self.url = configuration.get_intent_classifier_endpoint()
        self.confidence = configuration.get_intent_classifier_confidence()

    def apply(self, user_arg, disable_cache):
        intents, intent_scores = get_scores(self.url, user_arg, disable_cache)
        if intent_scores[0] > self.confidence:
            return create_intent(label=intents[0], score=intent_scores[0], source='classifier')
        return create_intent(intent_classes[-1], score=1, source='classifier')


class IntentDetection:

    def __init__(self, advisory_mode, configuration, kp_utils_ml):
        self.intent_classifier = IntentClassifierClient()
        self.advisory_mode = advisory_mode
        self.configuration = configuration
        self.rule_based_intents = [Profanity(),
                                   SameKPTwiceInARow(),
                                   TwoNoneOfTheAboveInARow(),
                                   NoConcernAfterWhatElseConcernsQuestion()]
        self.kp_utils_ml = kp_utils_ml

    def apply(self, user_arg, dialog_data, disable_cache, **kwargs):
        intent = None
        if user_arg is None:
            intent = create_intent('INTRO_DISCUSSION', score=1)
        # rule-based intents
        if intent is None and 'messages' in dialog_data:
            intent = self.apply_rule_based_intents(context=dialog_data['messages'], **kwargs)
        # dip intent classification
        if intent is None and 'messages' in dialog_data:
            intent = self.intent_classifier.apply(user_arg=user_arg, disable_cache=disable_cache)
        intent = self.modify_label(intent, kwargs['con_kp'])
        return intent

    def apply_to_opening_survey(self, intent_name):
        return create_intent(intent_name, score=1)

    def apply_to_feedback(self, feedback_options, user_arg, dialog_data, language_code):
        result_intent = None
        for intent in feedback_options:
            if re.match(intent['text'], user_arg):
                if 'messages' in dialog_data:
                    # the user_arg in the feedback menu is the con_kp, or one of the two non-kp alternatives
                    result_intent = self.apply_rule_based_intents(
                        context=dialog_data['messages'], new_intent=intent['intent_label'],
                        con_kp=self.kp_utils_ml[language_code].get_kp_by_qform(user_arg)
                        if intent['intent_label'] == "FEEDBACK_NEW_KP" else None)
                if result_intent is None:
                    result_intent = self.create_feedback_intent(intent['intent_label'])
                return result_intent, intent['kp']
        raise ValueError("Intent unrecognized in [%s]" % user_arg)

    def apply_rule_based_intents(self, context, **kwargs):
        for rule in self.rule_based_intents:
            if rule.apply(dialog_data=context, **kwargs):
                return create_intent(rule.get_name(), score=1.0, source='context_rule')
        return None

    # modify the label if:
    # 1) there is no intent detected, but there is a con kp (so there is content)
    # TODO: have a no-canned-text option for an intent
    # 2) there is a "concern"-intent, but no con kp - we resort to default
    def modify_label(self, intent, con_kp):
        if con_kp is not None and intent['label'] == 'default':
            intent['label'] = 'query'
        elif con_kp is None and intent['label'] in ['concern', 'query', 'default']:
            if self.advisory_mode['enabled']:
                intent['label'] = 'default_with_feedback'
            else:
                intent['label'] = 'default'
        return intent

    @classmethod
    def create_feedback_intent(cls, label):
        return create_intent(label, score=1, source='user-feedback')

    @classmethod
    def check_no_response_intent(cls, intent):
        return intent['label'] in ['default_with_feedback', 'default']

    @classmethod
    def no_feedback_intent(cls, intent):
        return intent['label'] in ['greeting', 'farewell', 'negative_reaction', 'positive_reaction']
