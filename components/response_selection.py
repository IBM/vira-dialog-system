#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

import threading

from tools.db_manager import DBManager

RANDOM_MODEL = "random"
RANDOM_INIT_SCORE = 10


class RandomScorer:

    def __init__(self, random_state):
        self.random_state = random_state

    def score(self, chat_history, candidates):
        self.random_state.shuffle(candidates)
        return {'text_candidates': candidates, 'cand_scores': [RANDOM_INIT_SCORE - i/RANDOM_INIT_SCORE
                                                               if RANDOM_INIT_SCORE - i/RANDOM_INIT_SCORE > 0
                                                               else 0 for i in range(len(candidates))]}


class ResponseSelection:

    def __init__(self, random_state):
        configuration = DBManager().read_configuration()
        self.scorer = RandomScorer(random_state)
        self.lock = threading.Lock()
        self.random_state = random_state
        self.last_usage_factors = configuration.get_last_usage_factors()

    def diminish_score_by_recency_usage(self, arg, score, system_argument_history):
        response_base_used = [i for i, arg_history in enumerate(system_argument_history)
                              if arg_history.base_response == arg.base_response]
        response_base_last_used_index = response_base_used[-1] if len(response_base_used) > 0 else -1
        canned_text_last_used_indices = []
        for ct in arg.canned_text:
            if len(ct) > 0:
                canned_text_used = [i for i, arg_history in enumerate(system_argument_history)
                                    if ct in arg_history.canned_text]
                canned_text_last_used_indices.append(canned_text_used[-1] if len(canned_text_used) > 0 else -1)
        if response_base_last_used_index > -1:
            score *= pow(self.last_usage_factors['response_db'],
                         5 / (len(system_argument_history) - response_base_last_used_index))
        for canned_text_last_used_index in canned_text_last_used_indices:
            if canned_text_last_used_index > -1:
                score *= pow(self.last_usage_factors['canned_text'],
                             5 / (len(system_argument_history) - canned_text_last_used_index))
        return score

    def apply(self, candidates, chat_history, system_argument_history):
        orig_scores = None
        sorted_scores = None
        sorted_candidates = None
        if len(candidates) == 0:
            return [], sorted_candidates, sorted_scores, orig_scores
        if len(chat_history) == 0:
            return self.random_state.choice(candidates, 1)[0], sorted_candidates, sorted_scores, orig_scores
        self.lock.acquire()
        try:
            model_response = self.scorer.score(chat_history=chat_history, candidates=[c.text for c in candidates])
        finally:
            self.lock.release()
        # calculating new scores, using factors to reduce scores according to last usage
        # determining if new scores need to be sorted in descending or ascending order
        descending_sort = len(candidates) < 2 or (model_response['cand_scores'][0] > model_response['cand_scores'][1])
        # first, sort list of Arguments according to the order determined by the model
        sorted_candidates = [[c for c in candidates if c.text == text][0] for text in model_response['text_candidates']]
        sorted_candidates_to_orig_scores = dict(zip(sorted_candidates, model_response['cand_scores']))
        # then calculate new scores for each Argument
        cands_to_new_scores = {arg: self.diminish_score_by_recency_usage(arg, score, system_argument_history) for arg,
                               score in zip(sorted_candidates, model_response['cand_scores'])}
        sorted_candidates = sorted(cands_to_new_scores.items(), key=lambda x: x[1],
                                   reverse=descending_sort)
        sorted_scores = [sc[1] for sc in sorted_candidates]
        orig_scores = [sorted_candidates_to_orig_scores[c[0]] for c in sorted_candidates]
        selected_candidate = sorted_candidates[0][0]
        return selected_candidate, [sc[0].text for sc in sorted_candidates], sorted_scores, orig_scores
