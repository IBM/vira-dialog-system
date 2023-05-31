#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

GENERAL_ARG_TYPE = 'general'
NO_CANNED_TEXT_TYPE = 'no_canned_text'


class Argument:
    def __init__(self, text, arg_type, base_response=None, canned_text=None, expression=None, link_replacement=None):
        self.text = text
        self.type = arg_type
        self.base_response = base_response if base_response is not None else text
        self.canned_text = canned_text
        self.expression = expression
        self.link_replacement = link_replacement

    def __str__(self):
        return self.text
