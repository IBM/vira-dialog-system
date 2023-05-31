#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

import re
import requests
from urllib.parse import urlparse
from urllib.parse import parse_qsl

from tools.db_manager import DBManager


def get_scores(url, pairs, batch_size, disable_cache):
    scores = []
    for begin in range(0, len(pairs), batch_size):
        batch = pairs[begin: begin + batch_size]
        headers = {'Pragma': 'no-cache'} if disable_cache else None
        resp = requests.post(url, json={'pairs': batch}, headers=headers)
        if resp.status_code != 200:
            raise ConnectionError('Failed calling server at %s: (%d) %s' %
                                  (url, resp.status_code, resp.reason))
        scores += resp.json()
    return scores


def get_query_components(http_request_handler):
    return dict(parse_qsl(urlparse(http_request_handler.path).query))


input_regex = re.compile(r"[-–,?'\"`’:;/+.!@#%^&()[\]$* ¡¿a-zA-Z0-9À-ÿ\u0590-\u05fe]")


class BadInputText(ValueError):
    def __init__(self, message):
        super(BadInputText, self).__init__(message)


def check_input_text(text, max_length):
    if len(text) == 0:
        raise BadInputText("Input is empty")
    elif len(text) > max_length:
        raise BadInputText("Input is too long")
    else:
        remaining_chars = input_regex.sub('', text)
        if len(remaining_chars) > 0:
            raise BadInputText('Input is invalid (%s)' % remaining_chars)


def check_session_id(session_id):
    if not DBManager.is_valid_id(session_id):
        raise ValueError('Bad session id: %s' % session_id)


def verify_bool_feedback(feedback):
    if not isinstance(feedback, bool):
        raise ValueError('Feedback is not a boolean')


def verify_int_feedback(feedback):
    type_check = (not isinstance(feedback, bool)) and isinstance(feedback, int)
    value_check = feedback == 1 or feedback == -1
    if not (type_check and value_check):
        raise ValueError('Feedback is not a +1 or -1')


def verify_message_id(message_id):
    if not isinstance(message_id, int):
        raise ValueError('Message id is not an integer')
    elif message_id > 100:
        raise ValueError('Message id too big')
