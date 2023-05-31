#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

import re
from tools.text_cleansing import clean_words


class CoRefResolution:

    GLOBAL_THEME = 'the vaccine'
    CONDITION_THEME = 'vaccine'
    MAX_LENGTH = 5

    def apply(self, text):
        pass


class SimpleCoRefResolution(CoRefResolution):

    def apply(self, text):
        if len(clean_words(text)) <= self.MAX_LENGTH and self.CONDITION_THEME not in text:
            text = re.sub(r"\bit's\b", self.GLOBAL_THEME + ' is', text)
            text = re.sub(r"\bit\b", self.GLOBAL_THEME, text)
        return text
