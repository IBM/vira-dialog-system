#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

import re
from tools.db_manager import DBManager


class ProfanityClassifier:

    def __init__(self):
        self.lexicon = DBManager().read_profanity_lexicon()
        self.regex_lexicon = re.compile(r"\b(" + "|".join([re.escape(item.strip().lower())
                                                           for item in self.lexicon]) + r")\b")
        self.texts = DBManager().read_profanity_texts()
        self.regex_texts = re.compile(r"^(" + "|".join([re.escape(text.strip().lower())
                                                        for text in self.texts]) + r")$")
        self.regex_cleaner = re.compile(r"[^A-Za-z0-9\-]")

    def apply(self, user_text):
        user_text = self.regex_cleaner.sub(" ", user_text).lower()
        user_text = ' '.join(user_text.split())
        return self.regex_texts.match(user_text) is not None or self.regex_lexicon.search(user_text) is not None


if __name__ == "__main__":
    lex = ProfanityClassifier()
    assert lex.apply('Nigga please')
    assert lex.apply('cocksucker')
    assert lex.apply('I dont like you. alabama hot  pocket')
    assert lex.apply('jews')
    assert lex.apply('Are you a jew?')
    assert lex.apply('The jews did 9/11')
    assert not lex.apply('what are the side effects?')
    assert not lex.apply('Does the profanity classifier pushed to production?')
    assert not lex.apply('Can jews have covid?')
    print("All passed")
