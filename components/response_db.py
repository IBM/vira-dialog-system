#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

from tools.argument import Argument
from tools.db_manager import DBManager
import re


class ResponseDB:
    def __init__(self, language_code):
        _, self.kp_mapping, kp_responses = DBManager().read_response_db(language_code)
        self.con_kps = sorted(list(self.kp_mapping.keys()))
        self.pro_kp_args = {keypoint: [Argument(text=text[0], base_response=text[0], arg_type=arg_type,
                                                link_replacement=text[1])
                            for arg_type, texts in keypoint_data.items() for text in texts]
                            for keypoint, keypoint_data in kp_responses.items()}
        self.link_pattern = re.compile(r"(\[(?: )?LINK(?: )?\|(?: )?(.+)(?: )?\|(?: )?(.+)(?: )?\])")

    def get_pro_kp_mapping(self, con_kp):
        return self.kp_mapping[con_kp] if con_kp is not None and con_kp in self.kp_mapping.keys() else None

    def get_pro_kp_args(self, pro_kp, campaign_id=None):
        pro_args = list(self.pro_kp_args[pro_kp]) if pro_kp is not None else []
        if len(pro_args) > 0 and campaign_id is not None:
            for arg in pro_args:
                if campaign_id in arg.link_replacement.keys():
                    arg.text = self.set_link(arg.text, arg.link_replacement, campaign_id)
                    arg.base_response = self.set_link(arg.base_response, arg.link_replacement, campaign_id)
        return pro_args

    def set_link(self, text, link_replacement, campaign_id):
        m = self.link_pattern.search(text)
        if m is not None:
            text = text.replace(m.group(0), link_replacement[campaign_id])
        return text

    def get_con_kps(self):
        return self.con_kps


class ResponseDBML:

    def __init__(self, language_codes):
        self.response_dbs = {language_code: ResponseDB(language_code)
                             for language_code in language_codes}

    def __getitem__(self, item):
        return self.response_dbs[item]
