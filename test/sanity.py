#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

import os
import json

import requests


headers = {
    'Authorization': f'Bearer {os.environ["VIRA_API_KEY"]}'
}

data = {

}

response = requests.post("http://0.0.0.0:8100/dialog/en", headers=headers, json=data)
session_id = response.json()['session_id']

data = {
    'session_id': session_id,
    'text': "Can children get the vaccine?"
}
response = requests.post("http://0.0.0.0:8100/dialog/en", headers=headers, json=data)
print(json.dumps(response.json(), indent=4))
