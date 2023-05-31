#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

from enum import Enum

from tools.argument import Argument, GENERAL_ARG_TYPE
from tools.db_manager import DBManager
from tools.argument import NO_CANNED_TEXT_TYPE
import itertools


DEFAULT_EXPRESSION = '1-Neutral'


class ConnectingTextType(Enum):
    INTRO_DISCUSSION = 1,
    FAREWELL = 2,
    CONCERN = 3,
    DEFAULT = 9,
    CODE_SUBMITTED = 11,
    NEGATIVE_REACTION = 12,
    POSITIVE_REACTION = 13,
    GREETING = 15,
    QUERY = 16,
    FEEDBACK_NEW_KP = 22,
    FEEDBACK_NONE_OF_KPS = 23,
    FEEDBACK_NO_CONCERN = 24,
    DEFAULT_WITH_FEEDBACK = 25,
    SAME_KP_AFTER_NONE_OF_THE_ABOVE = 26,
    FEEDBACK_NONE_OF_KPS_TWO_IN_A_ROW = 27,
    NO_OTHER_CONCERN = 28,
    SAME_KP_TWICE_IN_A_ROW = 29,
    KP = 30,
    QUESTION = 31,
    AGREEMENT = 32,
    CLOSE_DISCUSSION = 33,
    CHANGE_SUBJECT = 34,
    DISAGREEMENT = 35,
    PROFANITY = 36,
    SURVEY_ORIGIN_QUESTION = 37,
    SURVEY_CLOSING = 38,
    INTRO_DISCUSSION_AFTER_SURVEY = 39

    @staticmethod
    def from_str(connecting_text_type):
        return ConnectingTextType[connecting_text_type.upper()]


class ConnectingTextLibrary:
    def __init__(self, advisory_mode, language_code):
        self.connecting_text_library = {ConnectingTextType[intent_str]: intent_value
                                        for intent_str, intent_value in
                                        DBManager().read_canned_text(language_code).items()}
        self.advisory_mode = advisory_mode

    def create_all_combinations(self, responses):
        combinations = []
        for intent in set(self.connecting_text_library.keys()):
            for persona in set(self.connecting_text_library[intent].keys()):
                combinations.extend(self.rephrase(responses, intent.name, persona, init=True))
        return combinations

    # lower the first char if it in the middle of a sentence
    def lower_if_needed(self, arg1, arg0):
        if len(arg0) > 1 and not arg0.rstrip().endswith(".") and not arg0.rstrip().endswith("!") and arg1[1].islower():
            arg1 = arg1[0].lower() + arg1[1:]
        return arg1

    # creating cartesian product of prefixes, arguments and suffixes
    def rephrase(self, arguments, intent, persona, init=False, both_prefix_and_suffix=False):
        intent_type = ConnectingTextType.from_str(intent)
        new_args = []
        persona_intent_args = self.connecting_text_library[intent_type][persona]
        # handling separately responses that need canned text, and those that don't
        arguments_need_canned_text = [arg for arg in arguments if arg.type != NO_CANNED_TEXT_TYPE]
        arguments_no_need_canned_text = [arg for arg in arguments if arg.type == NO_CANNED_TEXT_TYPE]
        # start by collecting all prefix-arg-suffix combinations
        for arg_type in persona_intent_args.keys():
            # get all arguments from argument list, matching the canned text arg type
            if arg_type != GENERAL_ARG_TYPE:
                arg_type_arguments_need_canned_text = [arg for arg in arguments_need_canned_text
                                                       if arg.type == arg_type]
            else:
                arg_type_arguments_need_canned_text = arguments_need_canned_text

            if len(arg_type_arguments_need_canned_text) > 0:
                prefix_suffix_args = self.connecting_text_library[intent_type][persona][arg_type]
                cartesian_args = []
                prefixes = []
                suffixes = []
                # collecting all combinations of: prefixes+arguments, arguments+suffixes, prefixes+arguments+suffixes
                if 'prefix' in prefix_suffix_args.keys():
                    prefixes = [(prefix + ' ', emoji)
                                for prefix, emoji in prefix_suffix_args['prefix']]
                    cartesian_args.extend([arg for arg in itertools.product(prefixes,
                                                                            arg_type_arguments_need_canned_text,
                                                                            [('', '')])])

                if 'suffix' in prefix_suffix_args.keys():
                    suffixes = [(' ' + suffix, emoji)
                                for suffix, emoji in prefix_suffix_args['suffix']]
                    cartesian_args.extend([arg for arg in itertools.product([('', '')],
                                                                            arg_type_arguments_need_canned_text,
                                                                            suffixes)])
                if both_prefix_and_suffix:
                    if len(prefixes) > 0 and len(suffixes) > 0:
                        cartesian_args.extend([arg for arg in itertools.product(prefixes,
                                                                                arg_type_arguments_need_canned_text,
                                                                                suffixes)])
                # converting to Argument object
                new_args.extend([Argument(text=(arg[0][0] + self.lower_if_needed(arg[1].text,
                                                                                 arg[0][0]) + arg[2][0]).strip(),
                                          arg_type=arg[1].type,
                                          base_response=arg[1].text,
                                          canned_text=[arg[0][0], arg[2][0]],
                                          expression=arg[0][1] if arg[0][1] != '' else arg[2][1])
                                 for arg in cartesian_args])
        # adding arguments that don't need canned text
        new_args.extend([Argument(text=arg.text,
                                  arg_type=arg.type, base_response=arg.text, canned_text=['', ''],
                                  expression=DEFAULT_EXPRESSION)
                         for arg in arguments_no_need_canned_text])
        # if no combination exists, take generic full responses (i.e., that do not use the response DB)
        if len(new_args) == 0 or init:
            for arg_type in persona_intent_args.keys():
                # adding canned texts that don't need arguments
                new_args.extend([Argument(text=arg, arg_type=arg_type,
                                          base_response=arg,
                                          canned_text=['', ''], expression=emoji) for arg, emoji
                                in persona_intent_args[arg_type]['full']]
                                if 'full' in persona_intent_args[arg_type] else [])
        return new_args

    def get_single_text(self, intent, persona):
        return self.rephrase([], intent['label'],
                             persona='general')[0].text

        intent_type = ConnectingTextType.from_str(intent)
        return self.connecting_text_library[intent_type][persona]


class ConnectingTextLibraryML:
    def __init__(self, advisory_mode, language_codes):
        self.libraries = {language_code: ConnectingTextLibrary(advisory_mode, language_code)
                          for language_code in language_codes}

    def __getitem__(self, item):
        return self.libraries[item]


def main():
    conn = ConnectingTextLibraryML(advisory_mode=False, language_codes=['en'])
    args = []
    rephrased_args = conn.get_connecting_text_library('en').rephrase(args, intent="undo")


if __name__ == "__main__":
    main()
