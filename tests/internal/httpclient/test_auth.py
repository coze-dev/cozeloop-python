# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from time import time

import pytest
from unittest.mock import MagicMock
from cozeloop.internal.httpclient.auth import TokenAuth, JWTAuth
from cozeloop.internal.httpclient.auth_client import OAuthToken


def test_token_auth_token():
    token = "valid_token"
    auth = TokenAuth(token)
    assert auth._token == token


@pytest.fixture
def mock_jwt_auth():
    mock_jwt_oauth_app = MagicMock()
    jwt_auth = JWTAuth(
        client_id='test_client_id',
        private_key='test_private_key',
        public_key_id='test_public_key_id',
    )
    jwt_auth._oauth_cli = mock_jwt_oauth_app
    return jwt_auth

def test_jwt_auth_token(mock_jwt_auth):
    mock_jwt_auth._oauth_cli.get_access_token.return_value = OAuthToken(
        access_token="valid_token",
        expires_in= int(time()) + 3600,
        token_type="Bearer"
    )

    token = mock_jwt_auth.token

    assert token == "valid_token"
    assert mock_jwt_auth._oauth_cli.get_access_token.call_count == 1

    token = mock_jwt_auth.token
    assert token == "valid_token"
    assert mock_jwt_auth._oauth_cli.get_access_token.call_count == 1

    mock_jwt_auth._token.expires_in = int(time())
    token = mock_jwt_auth.token
    assert token == "valid_token"
    assert mock_jwt_auth._oauth_cli.get_access_token.call_count == 2

