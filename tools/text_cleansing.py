#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

import re

stop_words = {
    "a", "about", "all", "also", "am", "an", "and", "any", "are", "as",
    "at", "be", "being", "been", "between", "both", "by", "can", "could",
    "did", "do", "does", "doing", "during", "each", "for", "from", "few", "further",
    "had", "has", "have", "having", "he", "he'd", "he'll", "he's", "her", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "in",
    "into", "is", "it", "its", "itself", "let", "let's", "me", "more", "most", "my",
    "must", "myself", "of", "off", "on", "once", "one", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "she", "she'd", "she'll",
    "she's", "should", "so", "some", "such", "than", "that", "that's", "the", "their",
    "theirs", "them", "themselves", "then", "there", "there's", "these", "they", "they'd",
    "they'll", "they're", "they've", "this", "those", "to", "too", "until", "us", "very",
    "was", "we", "we'd", "we'll", "we're", "we've", "were", "while", "whom", "will", "with",
    "would", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",
    "ll", "re", "ve", "s", "d", "t"}


def clean_words(text):
    text_words = re.sub(r"[^A-Za-z0-9\-]", " ", text).lower().split()
    return [word for word in text_words if word not in stop_words]


def clean_text(text, ignore_words=None, mask=None):
    words = clean_words(text)
    if ignore_words is not None:
        words = [word for word in words if word not in ignore_words]
    if mask is not None:
        mask_words = clean_words(mask)
        mask_words_set = set(mask_words)
        words = [word for word in words if word not in mask_words_set] + mask_words
    return " ".join(words)
