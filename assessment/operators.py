#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

import re


def bind_operators(ops):
    regex = re.compile(r'^([a-z_]+)(?:\(([a-z_]+(?:,\s*[a-z_]+)*)\))?$')
    ops_dict = {}
    for op in ops:
        match = regex.match(op)
        if match:
            op_name = match.group(1)
            op_func = globals()[op_name]
            params = match.group(2)
            ops_dict[op_name] = {
                'function': op_func,
                'params': [] if params is None else list(map(str.strip, params.split(',')))
            }
        else:
            raise ValueError('Unknown operator: [%s]' % op)
    return ops_dict


def is_user(message):
    return message['side'] == 'user'


def is_system(message):
    return message['side'] == 'system'


def is_feedback(message):
    return 'is_feedback' in message and message['is_feedback'] is True


def is_not_feedback(message):
    return not is_feedback(message)


def pos_feedback(message):
    return 'feedback' in message and message['feedback'] > 0


def neg_feedback(message):
    return 'feedback' in message and message['feedback'] < 0


def has_feedback(message):
    return pos_feedback(message) or neg_feedback(message)


def has_no_feedback(message):
    return 'feedback' not in message


def has_kp(kp=None):
    def internal(message):
        if kp is not None:
            return message['keypoint'] == kp
        else:
            return not has_no_kp(message)
    return internal


def has_no_kp(message):
    return message['keypoint'] == '' or message['keypoint'] is None


def none_of_kps_intent(message):
    intent = message['intent']
    return isinstance(intent, dict) and 'FEEDBACK_NONE_OF_KPS' in intent['label']


def no_concern_intent(message):
    intent = message['intent']
    return isinstance(intent, dict) and intent['label'] == 'FEEDBACK_NO_CONCERN'


def is_default_intent(message):
    intent = message['intent']
    return isinstance(intent, dict) and intent['label'].lower() in ['default', 'default_with_feedback']


def is_not_default_intent(message):
    return not is_default_intent(message)


def is_goodbye_intent(message):
    intent = message['intent']
    return isinstance(intent, dict) and intent['label'].lower() in ['farewell', 'no_other_concern']


def is_conversation_start(message):
    intent = message['intent']
    return isinstance(intent, dict) and intent['label'] == 'INTRO_DISCUSSION'


def is_not_intro(message):
    intent = message['intent']
    return isinstance(intent, dict) and intent['label'] != 'INTRO_DISCUSSION'


def is_last_message(message_id):
    def internal1(n_messages):
        def internal2(_):
            return message_id == n_messages - 1
        return internal2
    return internal1


def has_profanity(message):
    return 'is_profanity' in message


def is_profanity(message):
    return has_profanity(message) and message['is_profanity']


def is_not_profanity(message):
    return has_profanity(message) and not message['is_profanity']


def get_profanity(message):
    return message['is_profanity']
