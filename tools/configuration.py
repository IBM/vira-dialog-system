#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

import os


class Configuration:

    def __init__(self, data):
        self.data = data

    def get_kp_matching_endpoint(self):
        return self.data['kp_matching']['endpoint']

    def get_kp_matching_confidence(self):
        return self.data['kp_matching']['confidence']

    def get_wa_endpoint(self):
        return self.data['wa']['endpoint']

    def get_wa_apikey(self):
        return self.data['wa']['apikey']

    def get_wa_assistant_id(self):
        return self.data['wa']['assistant_id']

    def get_wa_version(self):
        return self.data['wa']['version']

    def get_wa_intent_confidence(self):
        return self.data['wa']['intent_confidence']

    def get_model_name(self):
        return self.data['candidate_scorer']['model_name']

    def get_candidate_scorer_model_dir(self):
        return os.path.join(
            self.data['candidate_scorer']['base_dir'],
            self.data['candidate_scorer']['model_name'])

    def get_last_usage_factors(self):
        model_name = self.data['candidate_scorer']['model_name']
        return self.data['candidate_scorer']['last_usage_factors'][model_name]

    def get_intent_classifier_endpoint(self):
        return self.data['intent_classifier']['endpoint']

    def get_intent_classifier_confidence(self):
        return self.data['intent_classifier']['confidence']

    def get_feedback_options(self, language_code):
        return self.data['languages'][language_code]['feedback_options']

    def get_ui_texts(self, language_code):
        return self.data['languages'][language_code]['ui_texts']

    def get_advisory_mode(self):
        return self.data['advisory_mode']

    def get_assessment_operators(self):
        return self.data['dialog_assessment']['operators']

    def get_assessment_indicators(self):
        return self.data['dialog_assessment']['indicators']

    def get_keypoint_analysis_host(self):
        return self.data['keypoint_analysis']['host']

    def get_keypoint_analysis_apikey(self):
        return self.data['keypoint_analysis']['apikey']

    def get_keypoint_analysis_limit(self):
        return self.data['keypoint_analysis']['limit']

    def get_assessment_ui_entrance_code(self):
        return self.data['dialog_assessment']['ui_entrance_code']

    def is_opening_survey_enabled(self, language_code):
        return self.data['languages'][language_code]['opening_survey']['enabled']

    def get_opening_survey_questions(self, language_code):
        return self.data['languages'][language_code]['opening_survey']['questions']

    def get_opening_survey_closing_intent(self, language_code):
        return self.data['languages'][language_code]['opening_survey']['survey_closing_intent']

    def get_opening_survey_intro_intent(self, language_code):
        return self.data['languages'][language_code]['opening_survey']['post_survey_intro_intent']

    def get_opening_survey_flows(self, language_code):
        return self.data['languages'][language_code]['opening_survey']['flows']

    def get_opening_survey_default_flow(self, language_code):
        return self.data['languages'][language_code]['opening_survey']['default_flow']

    def get_translator_apikey(self):
        return self.data['watson_translator']['apikey']

    def get_translator_model_id(self, language_code):
        return self.data['watson_translator'][language_code]['model_id']

    def get_translator_base_model_id(self, language_code):
        return self.data['watson_translator'][language_code]['base_model_id']

    def get_translator_endpoint(self):
        return self.data['watson_translator']['endpoint']

    def is_translator_enabled(self, language_code):
        return self.data['watson_translator'][language_code]['enabled']

    def get_language_codes(self):
        return list(self.data['languages'].keys())

    def get_language_direction(self, language_code):
        return self.data['languages'][language_code]['direction']

    def get_default_language(self):
        for language_code, data in self.data['languages'].items():
            if 'default' in data and data['default'] is True:
                return language_code
        raise ValueError('No language is indicated as default')

    def get_twilio_auth_token(self):
        return self.data['twilio_auth_token']

    def get_whatsapp_terms_url(self):
        return self.data['whatsapp_template']['terms_url']

    def get_whatsapp_logo_url(self):
        return self.data['whatsapp_template']['logo_url']
