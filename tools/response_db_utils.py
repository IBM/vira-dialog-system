#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

import os

import pandas as pd

from components.kp_matching import KpMatching

# mapping between kps
# keys are how they are phrased in our training data,
# values are how they are phrased in the response db
response_db_user_kp_mapping = {
    'what is covid?' : 'What is COVID?',
    'I think the vaccine was not tested on my community' : 'I don\'t think the vaccine was tested on my community',
    'COVID-19 vaccines are  contaminated with aluminium, mercury, and formaldehyde' : 'COVID-19 vaccines are  contaminated with aluminum, mercury, and formaldehyde',
    'How can I get the vaccine?': 'Where can I find the vaccine?',
    'I am worried about blood clots as a result of the vaccine': 'I am scared about blood clots',
    'What are the side effect of the vaccine?': 'What are the side effects of the vaccine?',
    'Who developed the vaccine?': 'Who developed the vaccines?',
    'Which vaccines are available?': 'How many vaccines are there?',
    'Does the vaccine prevent transmission?': 'Does the vaccine prevent me from giving the virus to others?',
    'Is it safe to go to the gym indoors if I\'m vaccinated?': 'Is it safe to go to the gym indoors if I\'m fully vaccinated?',
    'How much will I have to pay for the vaccine':'How much is the vaccine and do I need health insurance to get it?',
    'What about reports of abnormal periods due to the vaccine?': 'Is the vaccine safe for people who menstruate?',
    'Is the vaccine FDA approved?': 'What is the difference between FDA authorization and approval?',
    'How effective is the vaccine against the Omicron variant?': 'Do vaccines work against the Omicron variant of COVID-19?',
    'I am still experiencing COVID symptoms even after testing negative, should I still take the vaccine?': "I'm still experiencing COVID symptoms even after testing negative - should I still take the vaccine?",
    "How do I find the COVID-19 Community levels of my county?": "How do I find the COVID-19  Community levels of my county?",
    "Does the COVID-19 vaccine cause tinnitus?": "Is tinnitus a rare side effect of Covid vaccine?"
}


def get_normalized_kp(kp):
    if kp in response_db_user_kp_mapping.keys():
        return response_db_user_kp_mapping[kp]
    return kp


def clean_chars(df):
    return df.replace('’', "'", regex=True).replace("“", "\"", regex=True). \
        replace("”", "\"", regex=True).replace("<", "[", regex=True).replace(">", "]", regex=True).replace("–", "-",
                                                                                                           regex=True)


# replaces bad characters, strips kps, and renames some of them to make compatible with training file
def clean_response_db(df):
    df = clean_chars(df)
    df['user_kp'] = df['user_kp'].str.strip()
    if 'response_type' in df.columns:
        df['response_type'] = df['response_type'].str.strip()
    if 'system_kp' in df.columns:
        df['system_kp'] = df['system_kp'].str.strip()
    df['orig_user_kp'] = df['user_kp']
    response_db_user_kp_inv_mapping = {v: k for k, v in response_db_user_kp_mapping.items()}
    df = df.replace({"user_kp": response_db_user_kp_inv_mapping})
    return df


def verify_response_db(response_db_path, train_path, old_response_db_path, unused_path):

    response_db_df = pd.read_csv(response_db_path)
    train_df = pd.read_csv(train_path)
    response_db_df = clean_response_db(response_db_df)
    train_df = clean_response_db(train_df)
    old_response_db_df = pd.read_csv(old_response_db_path)
    old_response_db_df = clean_response_db(old_response_db_df)
    unused_df = pd.read_csv(unused_path)

    response_db_user_kps = set(response_db_df['user_kp'])
    train_user_kps = set(train_df['user_kp'])
    unused_user_kps = set(unused_df['unused'].tolist())

    # calculate the diff between the known kps to us vs. the kps in the response db
    response_db_not_in_training = response_db_user_kps.difference(train_user_kps)
    training_not_in_response_db = train_user_kps.difference(response_db_user_kps)
    reponses_db_not_in_training_or_unused = response_db_not_in_training.difference(unused_user_kps)
    print(f"{len(response_db_user_kps)} kps in the response db")
    print(f"{len(train_user_kps)} kps in the training data")
    print(f"\n{len(response_db_not_in_training)} kps in response db, not in our training data: \n{list(response_db_not_in_training)}")
    print(f'{len(training_not_in_response_db)} kps in our training data, not in the response db: \n{list(training_not_in_response_db)}')
    print(f"\n{len(reponses_db_not_in_training_or_unused)} kps in response db, not in our training data, including unused kps: \n{response_db_not_in_training}")


    # calculate responses by type
    if 'response_type' in response_db_df.columns:
        group_by_response_type = response_db_df.groupby(['response_type'])
        for response_type in group_by_response_type.groups.keys():
            print(f"\n {response_type}: {len(group_by_response_type.get_group(response_type)['system_response'])} responses")

    responses_diff = None
    # check if there are kps with a single response, or kps with more than one system response
    if 'system_kp' in response_db_df.columns:
        group_by_user_kps = response_db_df.groupby(['user_kp'])
        kps_with_more_than_one_system_kp = set()
        kps_with_only_one_response = set()
        for kp in group_by_user_kps.groups.keys():
            system_kps = len(set(group_by_user_kps.get_group(kp)['system_kp'].tolist()))
            if system_kps > 1:
                kps_with_more_than_one_system_kp.add(kp)
            system_responses = len(set(group_by_user_kps.get_group(kp)['system_response'].tolist()))
            if system_responses == 1:
                kps_with_only_one_response.add(kp)
        print(f'\nkps in the response db with more than one system kp: \n{kps_with_more_than_one_system_kp}')
        print(f'\nkps in the response db with a single system response: \n{kps_with_only_one_response}')

        group_by_system_kps = response_db_df.groupby(['system_kp'])
        system_kps_with_more_than_one_user_kp = {}
        for kp in group_by_system_kps.groups.keys():
            user_kps = set(group_by_system_kps.get_group(kp)['user_kp'].tolist())
            if len(user_kps) > 1:
                system_kps_with_more_than_one_user_kp[kp] = user_kps
        print(f'\nsystem kps in the response db for more than one user kp:')
        [print(f'{kp} : {", ".join(system_kps_with_more_than_one_user_kp[kp])}') for kp in
         system_kps_with_more_than_one_user_kp.keys()]

        new_responses_for_kp = {}
        deleted_responses_for_kp = {}

        old_response_user_kps = set(old_response_db_df['user_kp'])
        old_response_db_user_kps_also_in_new_response_db = old_response_user_kps.intersection(response_db_user_kps)
        old_group_by_user_kps = old_response_db_df.groupby(['user_kp'])
        for kp in old_response_db_user_kps_also_in_new_response_db:
            new_system_responses = set(group_by_user_kps.get_group(kp)['system_response'].tolist())
            old_system_responses = set(old_group_by_user_kps.get_group(kp)['system_response'].tolist())
            new_responses_not_in_old = new_system_responses.difference(old_system_responses)
            old_responses_deleted = old_system_responses.difference(new_system_responses)
            if len(new_responses_not_in_old) > 0:
                print(f'\n {len(new_responses_not_in_old)} new responses for kp {kp}')
                [print(f'\n{response}') for response in new_responses_not_in_old]
            if len(old_responses_deleted) > 0:
                print(f'\n {len(old_responses_deleted)} old responses removed for kp {kp}')
                [print(f'{response}') for response in old_responses_deleted]
            if len(new_responses_not_in_old) > 0 or len(old_responses_deleted) > 0:
                new_responses_for_kp[kp] = new_responses_not_in_old
                deleted_responses_for_kp[kp] = old_responses_deleted
        responses_diff = pd.DataFrame({'kp': [
            kp for kp in new_responses_for_kp.keys()],
            'num_new_responses': [len(new_responses_for_kp[kp]) for kp in new_responses_for_kp.keys()],
            'new_responses': ['\n\n'.join(new_responses_for_kp[kp]) for kp in new_responses_for_kp.keys()],
            'num_deleted_responses': [len(deleted_responses_for_kp[kp]) for kp in new_responses_for_kp.keys()],
            'deleted_responses': ['\n\n'.join(deleted_responses_for_kp[kp]) for kp in new_responses_for_kp.keys()]})

    # check matches of new kps to existing kps, according to the deployed kp model
    kp_matching_result = check_matches_to_existing_kps(list(response_db_user_kps))
    glove_similarity_result = check_glove_similarity_to_existing_kps(
        list(response_db_user_kps),
        list(set(response_db_user_kps).union(set(train_user_kps)).union(set(unused_user_kps))))
    combined_result = []
    for kp in response_db_user_kps:
        kp_result_dict = {"kp": kp, 'all_matches': set(), 'new': kp in response_db_not_in_training}
        for i, match_and_score_kp_matching_model in enumerate(kp_matching_result[kp]):
            add_match_and_score_to_result_dict(kp_result_dict, index=i, score_type='kp_matching',
                                               match_and_score=match_and_score_kp_matching_model)
        for i, match_and_score_glove_similarity in enumerate(glove_similarity_result[kp]):
            add_match_and_score_to_result_dict(kp_result_dict, index=i, score_type='glove_similarity',
                                               match_and_score=match_and_score_glove_similarity)
        combined_result.append(kp_result_dict)
    matching_results = pd.DataFrame(combined_result).sort_values(by=['kp_matching_score_1'], ascending=False)
    return matching_results, responses_diff


def add_match_and_score_to_result_dict(kp_result_dict, index, score_type, match_and_score):
    kp_result_dict[score_type+'_rank_' + str(index+1)] = match_and_score[0]
    kp_result_dict[score_type+'_score_' + str(index+1)] = match_and_score[1]
    kp_result_dict['all_matches'].add(match_and_score[0])


def get_response_db_kp(kp):
    if kp in response_db_user_kp_mapping:
        return response_db_user_kp_mapping[kp]
    return kp


def check_glove_similarity_to_existing_kps(new_kps_list, baseline_kps_list):
    import spacy
    nlp = spacy.load("en_core_web_lg")
    new_docs = [d for d in nlp.pipe(new_kps_list)]
    baseline_docs = [d for d in nlp.pipe(baseline_kps_list)]
    new_kps_top_glove_matches = {}
    for new_doc in new_docs:
        kp = new_doc.text
        kp_matches_and_scores = {}
        for baseline_doc in baseline_docs:
            # the kp shouldn't be in the matches to itself
            if kp == baseline_doc.text:
                continue
            kp_matches_and_scores.update({baseline_doc.text: baseline_doc.similarity(new_doc)})
        # for each kp, we save the 3 best matches
        new_kps_top_glove_matches[kp] = sorted(kp_matches_and_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    return new_kps_top_glove_matches


def check_matches_to_existing_kps(new_kps_list):
    confident_matches, all_matches_scores = KpMatching().match_to_existing_kps(list(new_kps_list))
    print(f'\npotential matches within the response db\n')
    result = {}
    for kp, kp_confident_matches, kp_matches_and_scores in zip(list(new_kps_list), confident_matches,
                                                               all_matches_scores):
        # the kp shouldn't be in the matches to itself
        kp_matches_and_scores = {get_response_db_kp(kp): score for kp, score in kp_matches_and_scores.items()}
        if kp in kp_confident_matches:
            kp_confident_matches.remove(kp)
        if kp in kp_matches_and_scores:
            kp_matches_and_scores.pop(kp)
        if len(kp_confident_matches) > 0:
            print(f'\"{kp}\" was confidently matched to {kp_confident_matches}')
        # for each kp, we save the 3 best matches
        result[kp] = sorted(kp_matches_and_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    return result


if __name__ == "__main__":
    bot_dir = 'bot/covid_jhu_en/resources'
    result_df, responses_diff_df = verify_response_db(
        response_db_path=os.path.join(bot_dir, 'response_db_en.csv'),
        train_path=os.path.join(bot_dir, 'kps_to_parent.csv'),
        old_response_db_path=os.path.join(bot_dir, 'response_db_es.csv'),
        unused_path=os.path.join(bot_dir, 'unused_kps.csv'))
    result_df.to_csv('assessment/results/new_kps_potential_duplicates.csv')
    if responses_diff_df is not None:
        responses_diff_df.to_csv('assessment/results/responses_diff.csv', index=False)
