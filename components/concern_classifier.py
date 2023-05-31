#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

from tools.text_cleansing import clean_text, clean_words


class ConcernClassifier:

    def apply(self, user_text, dialog_data):
        pass


class LexicalConcernClassifier(ConcernClassifier):

    COMMON_NO_CONCERN_WORDS = clean_words('agree hi bye disagree support concern ' +
                                          'good nice please ok yes no idea thank ' +
                                          'thanks never mind nothing forget move on ' +
                                          'understand clear clarify not')
    CONCERN_WORDS_THRESHOLD = 0

    def apply(self, user_text, dialog_data):
        text = clean_text(user_text, ignore_words=self.COMMON_NO_CONCERN_WORDS)
        n_words = len(text.split())
        return n_words > self.CONCERN_WORDS_THRESHOLD


if __name__ == "__main__":
    lex = LexicalConcernClassifier()
    print(lex.apply('good', None))
    print(lex.apply("I'm sorry, but I'm not sure I understood your point.", None))
