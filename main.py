#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

import json
import logging.config
import os
from typing import Optional, Union, Any

from fastapi import FastAPI, Depends, Request, HTTPException, status as fastapi_status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from starlette.responses import JSONResponse

from components.dialog_manager import DialogManager
from tools.db_manager import DBManager
from tools.service_utils import check_input_text, check_session_id, verify_bool_feedback, verify_int_feedback, \
    verify_message_id
import uvicorn

logging_config_file = os.path.join('resources', 'logging.conf')
logging.config.fileConfig(logging_config_file)

log = logging.getLogger('main')

app = FastAPI(openapi_url=None)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

VIRA_API_KEY = os.environ['VIRA_API_KEY']


# bot_name = "bot"

# BotManager().set_name(bot_name)
language_codes = DBManager().read_configuration().get_language_codes()

dialog_manager = DialogManager()


class MessageRequest(BaseModel):
    session_id: Optional[str]
    text: Optional[str]
    feedback: Union[bool, int, None] = None
    answer: Optional[bool]
    message_id: Optional[int]
    survey: Optional[Any]


# entry point for sanity check
@app.get("/")
def read_root():
    return {"Hello": "VIRA Backend"}


# entry point for k8s health-check
@app.get("/health")
def read_root():
    return "OK"


async def verify_token(token: str = Depends(oauth2_scheme)):
    if token != VIRA_API_KEY:
        raise HTTPException(
            status_code=fastapi_status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


@app.exception_handler(ValueError)
async def value_error_exception_handler(_request: Request, exc: ValueError):
    log.exception(f"ValueError raised")
    return JSONResponse(
        status_code=400,
        content={"message": str(exc)},
    )


@app.exception_handler(HTTPException)
async def unicorn_exception_handler(_request: Request, exc: HTTPException):
    log.exception(f"HTTP Exception raised")
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={"message": exc.detail},
    )


@app.exception_handler(Exception)
async def unicorn_exception_handler(_request: Request, exc: Exception):
    log.exception(f"Unexpected exception caught: {type(exc).__name__}")
    return JSONResponse(
        status_code=500,
        content={"message": f"Internal Server Error"},
    )


@app.post("/dialog/{language_code}")
def handle_user_input(language_code: Optional[str], request: MessageRequest,
                      _token: str = Depends(verify_token)):
    log.info('New message')

    if not request.session_id:
        log.info('Processing new session')

        dialog_label = None

        # # extract the campaign id
        # if 'Campaign-Id' in headers:
        #     campaign_id = headers['Campaign-Id']
        #     check_input_text(campaign_id, 64)
        # else:
        campaign_id = None

        # # extract the opening survey
        # if 'Opening-Survey' in headers:
        #     opening_survey_flow = headers['Opening-Survey'].lower()
        #     check_input_text(opening_survey_flow, 16)
        # else:
        opening_survey_flow = None

        # # extract the platform
        # if 'platform' in headers:
        #     platform = headers['platform'].lower()
        #     check_input_text(platform, 64)
        # else:
        platform = None

        # generate response
        response = dialog_manager.process_new_session(dialog_label, campaign_id, opening_survey_flow,
                                                      platform, language_code)
    else:
        log.info('Continuing existing session')
        log.info(f'Received request:\n{json.dumps(request.dict(), indent=4)}')

        # extract the session id
        session_id = request.session_id
        check_session_id(session_id)

        if request.text:
            text = request.text.strip()
            check_input_text(text, 255)

            # 'feedback' indicates whether the user input is a new input text or a selection of
            # a kp that is sent as a new text - i.e. a feedback.
            feedback = request.feedback if request.feedback is not None else False
            verify_bool_feedback(feedback)

            # 'answer' indicates whether the user input is an answer to an opening survey question
            answer = request.answer if request.answer is not None else False
            verify_bool_feedback(answer)

            # disable cache down the road if requested to
            # disable_cache = 'Pragma' in headers and headers['Pragma'] == 'no-cache'
            disable_cache = False

            # generate response
            response = dialog_manager.process_user_text(session_id, text, feedback, answer, disable_cache)

        elif all(x is not None for x in [request.message_id, request.feedback]):
            # the message to which the feedback is given
            message_id = request.message_id
            verify_message_id(message_id)

            # feedback indicates whether it's a thumbs up (true) or thumbs down (false)
            feedback = request.feedback
            verify_int_feedback(feedback)

            # generate response
            response = dialog_manager.process_user_feedback(session_id, message_id, feedback)

        elif request.survey is not None:

            # generate response
            response = dialog_manager.process_user_survey(session_id, request.survey)

        else:
            raise ValueError('Unsupported request')

    log.info('Response:\n' + str(response))

    return response


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8100, log_config=logging_config_file)
