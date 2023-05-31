#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

import json
import logging
import os
import re
import socket
from datetime import datetime, timedelta

from bson.objectid import ObjectId
from pymongo import MongoClient
from tqdm import tqdm

from tools.configuration import Configuration
from tools.dialog_data import DialogData
from tools.singleton import Singleton


def db_renew_client_on_exception(func):
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error('Exception caught in %s - recreating client' % func.__name__)
            self = args[0]
            self.client = self.create_client()
            raise e
    return inner


class DBManager(metaclass=Singleton):

    def __init__(self):

        db_conf_file = os.path.join('resources', 'db', 'db_credentials.json')
        with open(db_conf_file, 'rt', encoding='utf-8') as fp:
            data = json.load(fp)
        self.url = "mongodb://" + data['username'] + ":" + data['password'] + "@" + ''.join(data['endpoint'])
        self.certificate = os.path.join('resources', 'db', 'certificate.crt')
        self.timeout_ms = 180 * 1000
        self.client = self.create_client()
        self.hostname = socket.gethostname()
        self.db_name = "vira"

        if 'EVAL_LABEL' in os.environ:
            self.label = os.environ['EVAL_LABEL']
            logging.info("Using label: [%s]" % self.label)
        else:
            self.label = None

        logging.info("Using DB: [%s]" % self.db_name)

    def create_client(self):
        return MongoClient(self.url, tls=True, tlsCAFile=self.certificate,
                           socketTimeoutMS=self.timeout_ms, wTimeoutMS=self.timeout_ms)

    @db_renew_client_on_exception
    def create_dialog(self, dialog_label=None, campaign_id=None, opening_survey_flow=None,
                      platform=None, language_code=None):
        record = {
            "date": datetime.now(),
            'data': {}
        }
        if dialog_label is not None:
            record['label'] = dialog_label
        elif self.label is not None:
            record['label'] = self.label
        if campaign_id is not None:
            record['campaign_id'] = campaign_id
        if opening_survey_flow is not None:
            record['opening_survey_flow'] = opening_survey_flow
        if platform is not None:
            record['platform'] = platform
        if language_code is not None:
            record['language_code'] = language_code
        dialog_id = self.client[self.db_name].dialogs.insert_one(record).inserted_id
        dialog_data = record['data']
        return DialogData(dialog_id, dialog_data, opening_survey_flow, campaign_id, platform, language_code)

    @db_renew_client_on_exception
    def get_dialog_data(self, session_id, dialog_label=None, campaign_id=None,
                        opening_survey_flow=None, platform=None, language_code=None):
        if session_id is None:
            return self.create_dialog(dialog_label, campaign_id, opening_survey_flow, platform, language_code)
        dialog_id = ObjectId(session_id) if isinstance(session_id, str) else session_id
        record = self.client[self.db_name].dialogs.find_one({'_id': dialog_id})
        if record is None:
            raise ValueError("Session id not found in database (%s, %s)" % (self.db_name, str(session_id)))
        dialog_id = record['_id']
        dialog_data = record['data']
        if 'opening_survey_flow' in record:
            opening_survey_flow = record['opening_survey_flow']
        if 'campaign_id' in record.keys():
            campaign_id = record['campaign_id']
        if 'platform' in record.keys():
            platform = record['platform']
        if 'language_code' in record.keys():
            language_code = record['language_code']
        return DialogData(dialog_id, dialog_data, opening_survey_flow, campaign_id, platform, language_code)

    @db_renew_client_on_exception
    def read_dialogs(self, start_date=None, end_date=None, label=None, appen_codes=None,
                     campaign_id=None, platform=None, language_code=None):
        start = datetime.strptime(start_date, '%Y-%m-%d') if start_date is not None\
            else datetime.strptime("2021-1-1", '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d') if end_date is not None \
            else datetime.now()
        appen_codes_query = {"data.appen_code": {"$in": appen_codes}} if appen_codes is not None else {}
        label_query = {"label": {"$eq": label}} if label is not None else {}
        campaign_id_query = {"campaign_id": {"$eq": campaign_id}} if campaign_id is not None else {}
        if platform is not None:
            if platform == 'vaxchat':
                platform_query = {"platform": {"$exists": False}}
            else:
                platform_query = {"platform": {"$eq": platform}}
        else:
            platform_query = {}
        if language_code is not None:
            if language_code == 'en':
                language_query = {"$or": [{"language_code": {"$eq": 'en'}},
                                          {"language_code": {"$exists": False}}]}
            else:
                language_query = {"language_code": {"$eq": language_code}}
        else:
            language_query = {}

        cursor = self.client[self.db_name]['dialogs'].find({"$and": [
                                                                        {"date": {"$lt": end, "$gte": start}},
                                                                        label_query,
                                                                        appen_codes_query,
                                                                        campaign_id_query,
                                                                        platform_query,
                                                                        language_query,
                                                                        ]})
        return [doc for doc in tqdm(cursor, desc='Dialogs read', unit='d')]

    @db_renew_client_on_exception
    def commit(self, dialog_data):
        self.client[self.db_name].dialogs.update_one({'_id': dialog_data.dialog_id},
                                                     {"$set": {'data': dialog_data.dialog_data}})

    @db_renew_client_on_exception
    def upload_document(self, collection, name, data):
        self.client[self.db_name][collection].replace_one(
            {'name': name},
            {'name': name, 'data': data}, upsert=True)

    @db_renew_client_on_exception
    def read_document(self, collection, name):
        return self.client[self.db_name][collection].find_one({'name': name})['data']

    def upload_authored_text(self, name, data):
        self.upload_document('authored_texts', name, data)

    def read_authored_text(self, name):
        return self.read_document('authored_texts', name)

    def upload_canned_text(self, data):
        for language_code, canned_texts in data.items():
            self.upload_authored_text(f'canned_text_{language_code}', canned_texts)

    def read_canned_text(self, language_code):
        return self.read_authored_text(f'canned_text_{language_code}')

    def upload_response_db(self, data):
        for language_code, (kp_hierarchy, kp_mapping, kp_responses) in data.items():
            name = f'response_db_{language_code}'
            print(f'uploading: {name}')
            self.upload_authored_text(name, {
                'kp_hierarchy': kp_hierarchy,
                'kp_mapping': kp_mapping,
                'kp_responses': kp_responses
            })

    def upload_kp_qform_mapping(self, data):
        for language_code, kp_qform_mapping in data.items():
            self.upload_authored_text(f'kp_qform_mapping_{language_code}', {
                'kp_qform_mapping': kp_qform_mapping
            })

    def upload_kp_idx_mapping(self, data):
        self.upload_authored_text(f'kp_idx_mapping', {
            'kp_idx_mapping': data
        })

    def read_response_db(self, language_code):
        name = f'response_db_{language_code}'
        logging.info(f'Reading: {name}')
        data = self.read_authored_text(name)
        return data['kp_hierarchy'], data['kp_mapping'], data['kp_responses']

    def upload_configuration(self, configuration):
        self.upload_document('configuration', 'general', configuration.data)

    def read_configuration(self):
        return Configuration(self.read_document('configuration', 'general'))

    def read_kp_qform_mapping(self, language_code):
        data = self.read_authored_text(f'kp_qform_mapping_{language_code}')
        return data['kp_qform_mapping']

    def read_kp_idx_mapping(self):
        data = self.read_authored_text('kp_idx_mapping')
        return data['kp_idx_mapping']

    @db_renew_client_on_exception
    def delete_dialogs(self, dialog_ids=None):
        condition = {} if dialog_ids is None else {'_id': {'$in': [ObjectId(oid) for oid in dialog_ids]}}
        return self.client[self.db_name]['dialogs'].delete_many(condition).deleted_count

    @db_renew_client_on_exception
    def delete_dialogs_by_label(self, label):
        return self.client[self.db_name]['dialogs'].delete_many(
            {"label": {"$regex": '.*' + re.escape(label) + '.*'}}).deleted_count

    @db_renew_client_on_exception
    def replace_dialogs(self, dialogs):
        if 'dialogs' in self.client[self.db_name].collection_names():
            self.client[self.db_name]['dialogs'].drop()
            if 'dialogs' in self.client[self.db_name].collection_names():
                raise RuntimeError("Failed to drop the dialogs collection")
        for dialog in dialogs:
            dialog['_id'] = ObjectId(dialog['_id'])
            dialog['date'] = datetime.fromisoformat(dialog['date'])
            for message in dialog['data']['messages']:
                message['date'] = datetime.fromisoformat(message['date'])

        self.client[self.db_name]['dialogs'].insert_many(dialogs)

    @db_renew_client_on_exception
    def delete_keypoint_analysis(self, label, language_code, status):
        self.client[self.db_name]['evaluation'].delete_many({'name': 'keypoint_analysis', 'data.label': label,
                                                             'data.language_code': language_code,
                                                             'data.status': status})

    @db_renew_client_on_exception
    def upload_keypoint_analysis(self, analysis, summary, label, language_code, status):
        data = {
            'analysis': analysis,
            'summary': summary,
            'label': label,
            'language_code': language_code,
            'date': datetime.now(),
            'status': status
        }
        self.client[self.db_name]['evaluation'].replace_one(
            {'name': 'keypoint_analysis', 'data.label': label, 'data.language_code': language_code},
            {'name': 'keypoint_analysis', 'data': data}, upsert=True)
        return data

    @db_renew_client_on_exception
    def read_keypoint_analysis(self, label, language_code, days_since_creation=None):
        date_query = {"data.date": {"$gt": datetime.now()-timedelta(days_since_creation)}} \
            if days_since_creation is not None else {}
        language_query = {"data.language_code": language_code}
        try:
            data = self.client[self.db_name]['evaluation'].find_one({"$and": [
                date_query,
                language_query,
                {"data.label": label},
            ]})['data']
            return data
        except:
            return None

    @db_renew_client_on_exception
    def get_available_keypoint_analysis_labels(self):
        labels = self.client[self.db_name]['evaluation'].find({}, {"data.label"})
        return [d['data']['label'] for d in labels]

    @db_renew_client_on_exception
    def relabel_dialogs(self, dialog_ids, label):
        condition = {'_id': {'$in': [ObjectId(oid) for oid in dialog_ids]}}
        update = {'$set': {'label': label}}
        return self.client[self.db_name]['dialogs'].update_many(condition, update).modified_count

    @db_renew_client_on_exception
    def upload_profanity_lexicon(self, data):
        self.upload_authored_text('profanity_lexicon', data)

    @db_renew_client_on_exception
    def read_profanity_lexicon(self):
        return self.read_authored_text('profanity_lexicon')

    @db_renew_client_on_exception
    def upload_profanity_texts(self, data):
        self.upload_authored_text('profanity_texts', data)

    @db_renew_client_on_exception
    def read_profanity_texts(self):
        return self.read_authored_text('profanity_texts')

    @classmethod
    def is_valid_id(cls, oid):
        return ObjectId.is_valid(oid)

    def get_campaign_ids(self):
        return self.client[self.db_name]['dialogs'].distinct('campaign_id')

    def get_platforms(self):
        return self.client[self.db_name]['dialogs'].distinct('platform')

    def get_language_codes(self):
        return self.client[self.db_name]['dialogs'].distinct('language_code')

    def remove_whatsapp_user(self, whatsapp_user):
        self.client[self.db_name]['whatsapp_users'].delete_one({'whatsapp_user': whatsapp_user})

    def get_whatsapp_user_session_id(self, whatsapp_user):
        record = self.client[self.db_name]['whatsapp_users'].find_one({'whatsapp_user': whatsapp_user})
        return record['session_id'] if record is not None else None

    def add_whatsapp_user_session_id(self, whatsapp_user, session_id):
        record = {
            'whatsapp_user': whatsapp_user,
            'session_id': session_id
        }
        self.client[self.db_name]['whatsapp_users'].insert_one(record)

    def is_whatsapp_user_show_kps(self, whatsapp_user):
        record = self.client[self.db_name]['whatsapp_users'].find_one({'whatsapp_user': whatsapp_user})
        return record['show_kps'] if 'show_kps' in record else False

    def set_whatsapp_user_show_kps(self, whatsapp_user, status):
        self.client[self.db_name]['whatsapp_users'].update_one({'whatsapp_user': whatsapp_user},
                                                               {"$set": {'show_kps': status}})


def main():
    db_manager = DBManager()
    dialog_data = db_manager.create_dialog()
    print(dialog_data.dialog_id)
    # db_manager.delete_keypoint_analysis("multi_option_pre_trained")


if __name__ == '__main__':
    main()
