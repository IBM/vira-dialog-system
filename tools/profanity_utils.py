#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

from time import time
import pandas as pd
from components.profanity_classifier import ProfanityClassifier
from tools.db_manager import DBManager
from assessment.operators import is_user, is_not_intro, has_profanity, get_profanity
from tqdm import tqdm


def main():
    print('Reading dialogs...', end=" ")
    t0 = time()
    dialogs = DBManager().read_dialogs(label='jhu-production')
    print("done in %.3f secs" % (time()-t0))
    profanity_classifier = ProfanityClassifier()
    profanity_missed_cases = []
    profanity_diff_old_cases = []
    profanity_diff_new_cases = []
    print('Collecting profanity cases...', end=" ")
    t0 = time()
    for dialog in tqdm(dialogs):
        dialog_id = str(dialog['_id'])
        for message_id, message in enumerate(dialog['data']['messages']):
            if is_user(message) and is_not_intro(message):
                text = message['text']
                is_profanity = profanity_classifier.apply(text)
                cases = None
                if has_profanity(message):
                    if is_profanity is not get_profanity(message):
                        cases = profanity_diff_new_cases if is_profanity else profanity_diff_old_cases
                elif is_profanity:
                    cases = profanity_missed_cases
                if cases is not None:
                    cases.append({
                        'dialog_id': dialog_id,
                        'message_id': message_id,
                        'date': message['date'],
                        'text': text
                    })
    print("Done in %.3f secs" % (time()-t0))
    pd.DataFrame(profanity_missed_cases).to_csv("profanity_missing_retrospective_.csv")
    pd.DataFrame(profanity_diff_old_cases).to_csv("profanity_diff_old.csv")
    pd.DataFrame(profanity_diff_new_cases).to_csv("profanity_diff_new.csv")

    print('Add profanity to %d messages? [y/n]' % len(profanity_missed_cases))
    choice = input().lower()

    if choice == 'y':
        # update the missing cases
        print('Adding profanity...', end=" ")
        t0 = time()
        for case in tqdm(profanity_missed_cases):
            dialog_data = DBManager().get_dialog_data(case['dialog_id'])
            dialog_data.set_profanity_retro(case['message_id'])
            DBManager().commit(dialog_data)
        print("Done in %.3f secs" % (time()-t0))


if __name__ == '__main__':
    main()
