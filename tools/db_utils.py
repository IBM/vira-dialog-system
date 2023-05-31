#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

import fnmatch
import json
import logging
import os.path
from argparse import ArgumentParser
from collections import defaultdict

import math
import pandas as pd

from tools.configuration import Configuration
from tools.db_manager import DBManager
from tools.response_db_utils import clean_response_db


def import_profanity_lexicon(path):
    path = os.path.join('resources', 'response_db', path)
    df = pd.read_csv(path)
    import_profanity_lexicon_df(df)


def import_profanity_lexicon_df(df):
    logging.info("uploading profanity lexicon")
    terms = [w.strip().lower() for w in df['lexicon'].tolist()]
    terms = [term for term in terms if len(term) > 0]
    DBManager().upload_profanity_lexicon(terms)


def import_profanity_texts(path):
    path = os.path.join('resources', 'response_db', path)
    df = pd.read_csv(path)
    import_profanity_texts_df(df)


def import_profanity_texts_df(df):
    logging.info("uploading profanity texts")
    texts = [w.strip().lower() for w in df['text'].tolist()]
    texts = [text for text in texts if len(text) > 0]
    DBManager().upload_profanity_texts(texts)


def import_kp_qform_path(name_prefix):
    logging.info("uploading kp-question mapping")
    resources_dir = os.path.join('resources', "response_db")
    name_pattern = f'{name_prefix}_*.csv'
    data = {
        get_language_code(fn, name_prefix): process_kp_qform_df(pd.read_csv(os.path.join(resources_dir, fn), encoding="ISO-8859-1"))
        for fn in fnmatch.filter(os.listdir(resources_dir), name_pattern)}
    DBManager().upload_kp_qform_mapping(data)
    logging.info("kp-question mappings uploaded")


def process_kp_qform_df(df):
    return {kp.strip().replace("’", "'").replace("’", "'").replace("–", "-"):
            q_form.strip().replace("’", "'").replace("’", "'").replace("–", "-")
            for kp, q_form in zip(df['user_kp'].tolist(), df['q_form'].tolist())}


def import_kp_idx_path(path):
    logging.info("uploading kp-idx mapping")
    path = os.path.join('resources', 'response_db', path)
    DBManager().upload_kp_idx_mapping(process_kp_idx_df(pd.read_csv(path)))
    logging.info("kp-idx mappings uploaded")


def process_kp_idx_df(df):
    return [kp.strip().replace("’", "'").replace("’", "'").replace("–", "-")
            for kp in df['user_kp'].tolist()]


def import_canned_text_path(name_prefix):
    logging.info("uploading canned text")
    name_pattern = f'{name_prefix}_*.csv'
    resources_dir = os.path.join('resources', 'response_db')
    data = {get_language_code(fn, name_prefix): process_canned_text_df(pd.read_csv(os.path.join(resources_dir, fn)))
            for fn in fnmatch.filter(os.listdir(resources_dir), name_pattern)}
    DBManager().upload_canned_text(data)
    logging.info("canned text uploaded")


def construnct_link_dict(link_replacement):
    links_dict = {}
    if link_replacement != '':
        link_replacement = link_replacement.split("\n")
        for link in link_replacement:
            first_colon = link.index(":")
            links_dict[link[:first_colon].strip()] = link[first_colon+1:].strip()
    return links_dict


def process_canned_text_df(df):
    df.update(pd.DataFrame({'trust': ['general'] * len(df.index)}))  # TODO: revert when trust model is working
    df = df[df['target'] == 'general']
    df = df.fillna({'text': ''})
    df_group_by = df.groupby(['intent_type', 'trust', 'arg_type', 'position'])
    connecting_text_library = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
    for connecting_text_type in df_group_by.groups.keys():
        df_type = df_group_by.get_group(connecting_text_type)
        arguments = [arg.rstrip() for arg in df_type['text'].values.tolist()]
        expressions = [e.strip() for e in df_type['emoji'].tolist()]
        t = connecting_text_type
        connecting_text_library[t[0]][t[1]][t[2]][t[3]] = [(a, e) for a, e in
                                                           zip(arguments, expressions)]
    return connecting_text_library


def get_language_code(fullname, name_prefix):
    filename = os.path.splitext(fullname)[0]
    language_code = filename[filename.index(name_prefix) + len(name_prefix) + 1:]
    return language_code


def import_response_db_path(name_prefix):
    logging.info("uploading response db")
    name_pattern = f'{name_prefix}_*.csv'
    resources_dir = os.path.join('resources', 'response_db')
    data = {get_language_code(fn, name_prefix): process_response_db_df(pd.read_csv(os.path.join(resources_dir, fn)))
            for fn in fnmatch.filter(os.listdir(resources_dir), name_pattern)}
    DBManager().upload_response_db(data)
    logging.info("response db uploaded")


def process_response_db_df(df):
    df = clean_response_db(df)
    df = df.fillna({'link_replacement': ''})
    df_hierarchy = dict(df.groupby(['user_kp', 'user_kp_parent']).groups.keys())
    kp_hierarchy = defaultdict(list)
    for key, value in df_hierarchy.items():
        if type(value) is float and math.isnan(value):
            value = 'root'
        for sub_value in value.split('|'):
            kp_hierarchy[key.strip()].append(sub_value.strip())
    kp_mapping = dict(df.groupby(['user_kp', 'system_kp']).groups.keys())
    pro_kp_groups = df.groupby('system_kp')
    kp_responses = defaultdict(lambda: defaultdict(list))
    for keypoint in pro_kp_groups.groups.keys():
        for text, arg_type, link_replacement in zip(pro_kp_groups.get_group(keypoint)['system_response'].tolist(),
                                                    pro_kp_groups.get_group(keypoint)['response_type'].tolist(),
                                                    pro_kp_groups.get_group(keypoint)['link_replacement'].tolist()):
            kp_responses[keypoint][arg_type.lower().strip()].append((text.strip(),
                                                                     construnct_link_dict(link_replacement)))
    return kp_hierarchy, kp_mapping, kp_responses


def import_configuration_data(json_data):
    logging.info("uploading configuration")
    for var in ['BOT_WA_APIKEY', 'BOT_WA_URL',
                'BOT_DASHBOARD_CODE',
                'BOT_KPA_HOST', 'BOT_KPA_APIKEY',
                'BOT_INTENT_CLASSIFIER_URL',
                'BOT_DIALOG_ACT_CLASSIFIER_URL']:
        if var not in os.environ:
            raise ValueError(f"Environment variable {var} is undefined")
    json_data['watson_translator']['apikey'] = os.environ['BOT_WA_APIKEY']
    json_data['watson_translator']['endpoint'] = os.environ['BOT_WA_URL']
    json_data['dialog_assessment']['ui_entrance_code'] = os.environ['BOT_DASHBOARD_CODE']
    json_data['keypoint_analysis']['host'] = os.environ['BOT_KPA_HOST']
    json_data['keypoint_analysis']['apikey'] = os.environ['BOT_KPA_APIKEY']
    json_data['kp_matching']['endpoint'] = os.environ['BOT_INTENT_CLASSIFIER_URL']
    json_data['intent_classifier']['endpoint'] = os.environ['BOT_DIALOG_ACT_CLASSIFIER_URL']
    DBManager().upload_configuration(Configuration(json_data))
    logging.info("configuration uploaded")


def import_configuration_path(path):
    path = os.path.join('resources', 'configuration', path)
    with open(path, "rt", encoding='utf-8') as fp:
        main_data = json.load(fp)
    import_configuration_data(main_data)


def is_file_exists(parser, arg):
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    else:
        return arg


def export_dialogs(path, start_date, end_date, label, appen_codes):
    dialogs = DBManager().read_dialogs(start_date=start_date, end_date=end_date, label=label, appen_codes=appen_codes)
    data = [{'dialog': d['data']['messages'],
             'dialog_id': d['_id'],
             'version': d['version'],
             'date': d['date'],
             'label': d['label'] if 'label' in d else '',
             'appen_code': d['data']['appen_code'] if 'appen_code' in d['data'] else '',
             'survey': d['data']['survey'] if 'survey' in d['data'] else {}}
            for d in dialogs if 'messages' in d['data'].keys()]
    with open(path, "w", encoding="utf8") as f:
        json.dump(data, f, default=str, indent=4)


def delete_dialogs(path=None):
    dialog_ids = None
    if path is not None:
        with open(path, "rt", encoding='utf-8') as fp:
            dialog_ids = json.load(fp)
    n_dialogs = DBManager().delete_dialogs(dialog_ids)
    logging.info("Deleted %d dialogs" % n_dialogs)


def delete_self_expiring_dialogs():
    n_dialogs = DBManager().delete_dialogs_by_label('self-expiring')
    logging.info("Deleted %d dialogs" % n_dialogs)


def import_conf_canned_db():
    import_canned_text_path('canned_text')
    import_response_db_path('response_db')
    import_kp_qform_path('kps_to_qform')
    import_kp_idx_path('kps_to_parent.csv')
    import_configuration_path('configuration.json')
    import_profanity_lexicon('profanity_lexicon.csv')
    import_profanity_texts('profanity_texts.csv')


def relabel_dialogs(path, label):
    with open(path, "rt", encoding='utf-8') as fp:
        dialog_ids = json.load(fp)

    n_dialogs = DBManager().relabel_dialogs(dialog_ids, label)
    logging.info("Re-labeled %d dialogs" % n_dialogs)


def main():
    logging.basicConfig(format="%(asctime)s %(levelname)s [%(threadName)s] %(funcName)s: %(message)s",
                        level=logging.INFO)
    logging.info("running db_utils")

    parser = ArgumentParser(description="Utilities for Data Management")
    parser.add_argument("-canned_text", dest="canned_text_path", required=False,
                        help="input canned text file", metavar="FILE",
                        default=None)
    parser.add_argument("-response_db", dest="response_db_file", required=False,
                        help="input keypoint mapping file", metavar="FILE",
                        default=None)
    parser.add_argument("-configuration", dest="configuration_file", required=False,
                        help="input configuration file", metavar="FILE",
                        default=None)
    parser.add_argument("-dialogs", dest="dialog_file", required=False,
                        help="output dialog file", metavar="FILE",
                        default=None)
    parser.add_argument("-dialogs_start_date", dest="start_date", required=False,
                        help="dialogs export start date, in a YYYY-MM-DD format",
                        type=str, default=None)
    parser.add_argument("-dialogs_end_date", dest="end_date", required=False,
                        help="dialogs export end date, in a YYYY-MM-DD format", type=str,
                        default=None)
    parser.add_argument("-dialogs_label", dest="label", required=False, help="dialogs export label", type=str,
                        default=None)
    parser.add_argument("-dialogs_appen_codes_path", dest="appen_codes_path", required=False,
                        help="dialogs export, path to appen codes to filter by. "
                             "path should contain a column named <appen_code>", type=str, default=None)
    parser.add_argument("-delete-all-dialogs", dest="delete", required=False, help="delete all dialogs",
                        action='store_true', default=None)
    parser.add_argument("-delete-dialogs", dest="delete_file", required=False,
                        help="delete specified dialogs", metavar="FILE", default=None)
    parser.add_argument("-replace-dialogs", dest="replace_file", required=False,
                        help="output dialog file", metavar="FILE", default=None)
    parser.add_argument("-conf-canned-db", dest="conf_canned_db", required=False,
                        help="imports configuration, canned text and response db",
                        action='store_true', default=None)
    parser.add_argument("-kp_idx_to_label", dest="kp_index_path", required=False,
                        help="kp-idx-mapping", metavar="FILE", default=None)
    parser.add_argument("-delete-self-expiring-dialogs", dest="delete_self_expiring", required=False,
                        help="delete all self expiring dialogs",
                        action='store_true', default=None)
    parser.add_argument("-relabel-dialogs", dest="relabel_file", required=False,
                        help="dialog ids file", metavar="FILE", default=None)
    parser.add_argument("-new-label", dest="label", required=False, help="dialogs new label", type=str,
                        default=None)
    parser.add_argument("-profanity_lexicon", dest="profanity_lexicon_path", required=False,
                        help="input profanity lexicon file", metavar="FILE",
                        default=None, type=lambda x: is_file_exists(parser, x))
    parser.add_argument("-profanity_texts", dest="profanity_texts_path", required=False,
                        help="input profanity texts file", metavar="FILE",
                        default=None, type=lambda x: is_file_exists(parser, x))

    args = parser.parse_args()

    if args.kp_index_path is not None:
        import_kp_idx_path(args.kp_index_qform_path)

    if args.canned_text_path is not None:
        import_canned_text_path(args.canned_text_path)

    if args.profanity_lexicon_path is not None:
        import_profanity_lexicon(args.profanity_lexicon_path)

    if args.profanity_texts_path is not None:
        import_profanity_texts(args.profanity_texts_path)

    if args.response_db_file is not None:
        import_response_db_path(args.response_db_file)

    if args.configuration_file is not None:
        import_configuration_path(args.configuration_file)

    if args.dialog_file is not None:
        appen_codes = list(set(pd.read_csv(args.appen_codes_path)['appen_code'].tolist())) if args.appen_codes_path is \
                                                                                              not None else None
        export_dialogs(path=args.dialog_file, start_date=args.start_date, end_date=args.end_date, label=args.label,
                       appen_codes=appen_codes)

    if args.delete:
        delete_dialogs()

    if args.delete_self_expiring:
        delete_self_expiring_dialogs()

    if args.delete_file:
        delete_dialogs(path=args.delete_file)

    if args.conf_canned_db:
        import_conf_canned_db()

    if args.relabel_file and args.label:
        relabel_dialogs(args.relabel_file, args.label)


if __name__ == '__main__':
    main()
