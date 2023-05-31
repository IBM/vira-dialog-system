#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

class OpeningSurvey:

    def __init__(self, configuration, language_code):
        self.configuration = configuration
        self.survey_enabled = self.configuration.is_opening_survey_enabled(language_code)
        self.survey_closing_intent = self.configuration.get_opening_survey_closing_intent(language_code)
        self.post_survey_intro_intent = self.configuration.get_opening_survey_intro_intent(language_code)
        self.flows = self.configuration.get_opening_survey_flows(language_code)
        self.all_survey_questions = self.configuration.get_opening_survey_questions(language_code)
        for question_intent, question in self.all_survey_questions.items():
            question['question_intent'] = question_intent
        self.flow_survey_questions = {flow: [self.all_survey_questions[question_intent]
                                             for question_intent in question_intents]
                                      for flow, question_intents in self.flows.items()}
        self.default_flow = self.configuration.get_opening_survey_default_flow(language_code)

    def is_enabled(self):
        return self.survey_enabled

    def get_next_question(self, dialog_data):
        survey_messages = dialog_data.get_opening_survey_messages()
        questions = self.flow_survey_questions[dialog_data.get_opening_survey_flow()]
        return questions[len(survey_messages)] if len(survey_messages) < len(questions) else None

    def has_more_questions(self, dialog_data):
        survey_messages = dialog_data.get_opening_survey_messages()
        questions = self.flow_survey_questions[dialog_data.get_opening_survey_flow()]
        return len(survey_messages) < len(questions)

    @classmethod
    def waiting_for_answer(cls, dialog_data):
        return dialog_data.is_opening_survey_waiting_for_answer()

    @classmethod
    def discontinued(cls, dialog_data):
        return dialog_data.is_opening_survey_discontinued()

    def get_survey_closing_intent(self):
        return self.survey_closing_intent

    def get_post_survey_intent(self):
        return self.post_survey_intro_intent

    def get_flows(self):
        return self.flows

    def get_default_flow(self):
        return self.default_flow


class OpeningSurveyML:

    def __init__(self, configuration, language_codes):
        self.opening_surveys = {language_code: OpeningSurvey(configuration, language_code)
                                for language_code in language_codes}

    def __getitem__(self, item):
        return self.opening_surveys[item]
