#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
