# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
from typing import Optional, Dict, Union, IO, Type, Tuple

import httpx
import pydantic
from pydantic import BaseModel

from cozeloop.internal import consts
from cozeloop.internal.httpclient.auth import Auth
from cozeloop.internal.httpclient.http_client import T, parse_response, HTTPClient
from cozeloop.internal.httpclient.user_agent import user_agent_header

logger = logging.getLogger(__name__)

FileContent = Union[IO[bytes], bytes]
FileType = Tuple[str, FileContent]


class Client:
    def __init__(
            self,
            api_base_url: str,
            http_client: HTTPClient,
            auth: Auth,
            timeout: int = consts.DEFAULT_TIMEOUT,
            upload_timeout: int = consts.DEFAULT_UPLOAD_TIMEOUT,
    ):
        self.api_base_url = api_base_url
        self.http_client = http_client
        self.auth = auth
        self.timeout = timeout
        self.upload_timeout = upload_timeout

    def _build_url(self, path: str) -> str:
        return f"{self.api_base_url}{path}"

    def _set_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        res = user_agent_header()
        if headers:
            res.update(headers)
        res[consts.AUTHORIZE_HEADER] = f"Bearer {self.auth.token}"

        tt_env = os.getenv("x_tt_env")
        if tt_env:
            res["x-tt-env"] = tt_env
        ppe_env = os.getenv("x_use_ppe")
        if ppe_env:
            res["x-use-ppe"] = "1"

        return res

    def request(
            self,
            path: str,
            method: str,
            response_model: Type[T],
            *,
            params: Optional[Dict[str, str]] = None,
            form: Optional[Dict[str, str]] = None,
            json: Optional[Union[BaseModel, Dict]] = None,
            files: Optional[Dict[str, FileType]] = None,
            headers: Optional[Dict[str, str]] = None,
            timeout: Optional[int] = None,
    ) -> T:
        url = self._build_url(path)
        _headers = self._set_headers(headers)

        _timeout = timeout if timeout is not None else self.timeout

        if isinstance(json, BaseModel):
            if pydantic.VERSION.startswith('1'):
                json = json.dict(by_alias=True)
            else:
                json = json.model_dump(by_alias=True)

        try:
            response = self.http_client.request(
                method,
                url,
                params=params,
                data=form,
                json=json,
                files=files,
                headers=_headers,
                timeout=_timeout
            )
        except httpx.HTTPError as e:
            logger.error(f"Http client request failed, path: {path}, err: {e}.")
            raise consts.NetworkError from e

        return parse_response(url, response, response_model)

    def get(
            self,
            path: str,
            response_model: Type[T],
            params: Optional[Dict[str, str]] = None,
    ) -> T:
        return self.request(path, "GET", response_model, params=params,
                            headers={"Content-Type": "application/json"})

    def post(
            self,
            path: str,
            response_model: Type[T],
            json: Union[BaseModel, Dict] = None,
    ) -> T:
        return self.request(path, "POST", response_model, json=json,
                            headers={"Content-Type": "application/json"})

    def upload_file(
            self,
            path: str,
            response_model: Type[T],
            file: FileContent,
            file_name: str,
            form: Dict[str, str],
    ) -> T:
        _file = {"file": (file_name, file)}
        return self.request(path, "POST", response_model, form=form, files=_file, timeout=self.upload_timeout)
