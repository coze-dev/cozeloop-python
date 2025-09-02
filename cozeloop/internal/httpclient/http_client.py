# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
from typing import Dict, Type, TypeVar

import httpx
import pydantic
from pydantic import ValidationError

from cozeloop.internal import consts
from cozeloop.internal.httpclient.base_model import BaseResponse

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseResponse)


class HTTPClient(httpx.Client):
    def __init__(self):
        super().__init__()


def _check_oauth_error(body: Dict, http_code: int, log_id: str) -> None:
    if http_code != 200 and "error_code" in body and "error_message" in body and "error" in body:
        auth_error = consts.AuthErrorFormat(**body)
        if auth_error.error_code:
            logger.error(f"OAuth error, {auth_error}")
            raise consts.AuthError(auth_error, http_code, log_id)


def parse_response(url: str, response: httpx.Response, response_model: Type[T]) -> T:
    log_id = response.headers.get(consts.LOG_ID_HEADER, None)
    http_code = response.status_code

    try:
        data = response.json()
        _check_oauth_error(data, http_code, log_id)
    except consts.AuthError as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to parse response. Path: {url}, http code: {http_code}, log id: {log_id}, error: {e}.")
        raise consts.RemoteServiceError(http_code, -1, "", log_id) from e

    code = data.get("code")
    msg = data.get("msg")
    if code and code != 0:
        e = consts.RemoteServiceError(http_code=http_code, error_code=code, error_message=msg, log_id=log_id)
        logger.error(
            f"Call remote service failed. Path: {url}, {e}, log id: {log_id}.")
        raise e

    try:
        res = None
        if data is not None:
            if pydantic.VERSION.startswith('1'):
                res = response_model.parse_obj(data)
            else:
                res = response_model.model_validate(data)
        else:
            res = response_model()
    except ValidationError as e:
        logger.error(f"Failed to parse response. Path: {url}, http code: {http_code}, log id: {log_id}, error: {e}.")
        raise consts.InternalError from e
    logger.debug(f"Call remote service success. Path: {url}, response: {res}, log id: {log_id}")
    return res
