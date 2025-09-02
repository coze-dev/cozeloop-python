# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import time
from typing import Optional, List, Type, Dict
from urllib.parse import urlparse, quote_plus

import httpx
import pydantic
from authlib.jose import jwt
from pydantic import BaseModel

from cozeloop.internal import consts
from cozeloop.internal.utils import random_hex
from .http_client import HTTPClient, T, parse_response

logger = logging.getLogger(__name__)


class OAuthToken(BaseModel):
    # The requested access token. The app can use this token to authenticate to the Coze resource.
    access_token: str
    # How long the access token is valid, in seconds (UNIX timestamp)
    expires_in: int
    # An OAuth 2.0 refresh token. The app can use this token to acquire other access tokens after the current access token expires. Refresh tokens are long-lived.
    refresh_token: str = ""
    # fixed: Bearer
    token_type: str = ""


class ScopeAccountPermission(BaseModel):
    permission_list: List[str]


class ScopeAttributeConstraintConnectorBotChatAttribute(BaseModel):
    bot_id_list: List[str]


class ScopeAttributeConstraint(BaseModel):
    connector_bot_chat_attribute: ScopeAttributeConstraintConnectorBotChatAttribute


class Scope(BaseModel):
    account_permission: Optional[ScopeAccountPermission] = None
    attribute_constraint: Optional[ScopeAttributeConstraint] = None

    @staticmethod
    def build_bot_chat(bot_id_list: List[str], permission_list: Optional[List[str]] = None) -> "Scope":
        if not permission_list:
            permission_list = ["Connector.botChat"]
        return Scope(
            account_permission=ScopeAccountPermission(permission_list=permission_list),
            attribute_constraint=ScopeAttributeConstraint(
                connector_bot_chat_attribute=ScopeAttributeConstraintConnectorBotChatAttribute(bot_id_list=bot_id_list)
            )
            if bot_id_list
            else None,
        )


class OAuthApp(object):
    def __init__(self, client_id: str, base_url: str, www_base_url: str, http_client: HTTPClient):
        self._client_id = client_id
        self._base_url = base_url
        self._api_endpoint = urlparse(base_url).netloc
        self._www_base_url = www_base_url
        self._http_client = http_client

    def _get_oauth_url(
            self,
            redirect_uri: str,
            code_challenge: Optional[str] = None,
            code_challenge_method: Optional[str] = None,
            state: str = "",
            workspace_id: Optional[str] = None,
    ):
        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        if code_challenge:
            params["code_challenge"] = code_challenge
        if code_challenge_method:
            params["code_challenge_method"] = code_challenge_method

        uri = f"{self._get_www_base_url}/api/permission/oauth2/authorize"
        if workspace_id:
            uri = f"{self._get_www_base_url}/api/permission/oauth2/workspace_id/{workspace_id}/authorize"
        return uri + "?" + "&".join([f"{k}={quote_plus(v)}" for k, v in params.items()])

    def _refresh_access_token(self, refresh_token: str, secret: str = "") -> OAuthToken:
        url = f"{self._base_url}/api/permission/oauth2/token"
        headers = {"Authorization": f"Bearer {secret}"} if secret else {}
        body = {
            "grant_type": "refresh_token",
            "client_id": self._client_id,
            "refresh_token": refresh_token,
        }
        return self._do_request(url, "POST", OAuthToken, headers=headers, json=body)

    def _gen_jwt(self, public_key_id: str, private_key: str, ttl: int, session_name: Optional[str] = None):
        now = int(time.time())
        header = {"alg": "RS256", "typ": "JWT", "kid": public_key_id}
        payload = {
            "iss": self._client_id,
            "aud": self._api_endpoint,
            "iat": now,
            "exp": now + ttl,
            "jti": random_hex(16),
        }
        if session_name:
            payload["session_name"] = session_name
        s = jwt.encode(header, payload, private_key)
        return s.decode("utf-8")

    async def _arefresh_access_token(self, refresh_token: str, secret: str = "") -> OAuthToken:
        url = f"{self._base_url}/api/permission/oauth2/token"
        headers = {"Authorization": f"Bearer {secret}"} if secret else {}
        body = {
            "grant_type": "refresh_token",
            "client_id": self._client_id,
            "refresh_token": refresh_token,
        }
        return await self._do_request(url, "POST", OAuthToken, headers=headers, json=body)

    @property
    def _get_www_base_url(self) -> str:
        if self._www_base_url:
            return self._www_base_url
        if self._base_url in [consts.CN_BASE_URL]:
            return self._base_url.replace("api", "www")
        return self._base_url

    def _do_request(
            self,
            url: str,
            method: str,
            response_model: Type[T],
            *,
            json: Optional[Dict] = None,
            headers: Optional[Dict[str, str]] = None,
            timeout: Optional[int] = consts.DEFAULT_TIMEOUT,
    ) -> T:
        _timeout = timeout if timeout is not None else timeout

        try:
            response = self._http_client.request(
                method,
                url,
                json=json,
                headers=headers,
                timeout=_timeout
            )
        except httpx.HTTPError as e:
            logger.error(f"Auth client call failed, url: {url}, err: {e}.")
            raise consts.NetworkError from e

        return parse_response(url, response, response_model)


class JWTOAuthApp(OAuthApp):
    """
    JWT OAuth App.
    """

    def __init__(self, client_id: str, private_key: str, public_key_id: str, base_url: str, http_client: HTTPClient):
        """
        :param client_id:
        :param private_key:
        :param public_key_id:
        :param base_url:
        """
        self._client_id = client_id
        self._base_url = base_url
        self._api_endpoint = urlparse(base_url).netloc
        self._token = ""
        self._private_key = self.parse_private_key(private_key)
        self._public_key_id = public_key_id
        super().__init__(client_id, base_url, www_base_url="", http_client=http_client)

    def parse_private_key(self, private_key: str) -> str:
        return private_key.replace("\\n", "\n")


    def get_access_token(
            self, ttl: int = 900, scope: Optional[Scope] = None, session_name: Optional[str] = None
    ) -> OAuthToken:
        """
        Get the token by jwt with jwt auth flow.

        :param ttl: The validity period of the AccessToken you apply for is in seconds.
        The default value is 900 seconds and the maximum value you can set is 86399 seconds,
        which is 24 hours.
        :param scope:
        :param session_name: Isolate different sub-resources under the same jwt account
        """
        jwt_token = self._gen_jwt(self._public_key_id, self._private_key, 3600, session_name)
        url = f"{self._base_url}/api/permission/oauth2/token"
        headers = {"Authorization": f"Bearer {jwt_token}"}
        scope_str = None
        if scope:
            if pydantic.VERSION.startswith('1'):
                scope_str = scope.dict()
            else:
                scope_str = scope.model_dump()
        body = {
            "duration_seconds": ttl,
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "scope": scope_str,
        }
        return self._do_request(url, "POST", OAuthToken, headers=headers, json=body)
