#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

from tools.db_manager import DBManager


class KPUtils:

    def __init__(self, language_code):
        self.kp_to_qform = DBManager().read_kp_qform_mapping(language_code)
        self.qform_to_kp = {value: key for key, value in self.kp_to_qform.items()}

    def get_kps_qform(self, kps):
        return [self.kp_to_qform[kp] for kp in kps]

    def get_kp_by_qform(self, qform):
        return self.qform_to_kp[qform]


class KPUtilsML:
    def __init__(self, language_codes):
        self.utils = {language_code: KPUtils(language_code)
                      for language_code in language_codes}

    def __getitem__(self, item):
        return self.utils[item]
