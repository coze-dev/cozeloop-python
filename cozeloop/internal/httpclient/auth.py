# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

from cozeloop.internal import consts
from cozeloop.internal.httpclient.http_client import HTTPClient
from cozeloop.internal.httpclient.auth_client import JWTOAuthApp


logger = logging.getLogger(__name__)


class Auth(ABC):
    @property
    @abstractmethod
    def token(self) -> str:
        pass


class TokenAuth(Auth):
    """
    The fixed access token auth flow.
    """

    def __init__(self, token: str):
        if not token:
            raise consts.InvalidParamError("Token is required.")
        self._token = token

    @property
    def token(self) -> str:
        return self._token


class JWTAuth(Auth):
    """
    The JWT auth flow.
    """

    def __init__(
            self,
            client_id: Optional[str] = None,
            private_key: Optional[str] = None,
            public_key_id: Optional[str] = None,
            ttl: int = consts.DEFAULT_OAUTH_REFRESH_TTL,
            base_url: str = consts.CN_BASE_URL,
            http_client: HTTPClient = None,
    ):
        if ttl < consts.OAUTH_REFRESH_ADVANCE_TIME:
            self._tll = consts.DEFAULT_OAUTH_REFRESH_TTL
        else:
            self._ttl = ttl
        self._token = None

        assert isinstance(client_id, str)
        assert isinstance(private_key, str)
        assert isinstance(public_key_id, str)
        assert isinstance(ttl, int)
        assert isinstance(base_url, str)
        self._oauth_cli = JWTOAuthApp(
            client_id, private_key, public_key_id, base_url=base_url, http_client=http_client
        )

    @property
    def token(self) -> str:
        token = self._generate_token()
        return token.access_token

    def need_refresh(self) -> bool:
        """
        Determines if the access token needs to be refreshed.

        :returns: True if the token needs to be refreshed, otherwise False.
        """
        before_second = consts.OAUTH_REFRESH_ADVANCE_TIME
        # Determine if the token needs to be refreshed
        current_time = int(time.time())
        return self._token is None or (current_time + before_second) > self._token.expires_in

    def _generate_token(self):
        if not self.need_refresh():
            return self._token
        logger.debug("Jwt token need refresh.")
        # todo add singleflight
        self._token = self._oauth_cli.get_access_token(self._ttl)
        return self._token
