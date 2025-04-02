# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import time

import pytest
from unittest.mock import MagicMock
from cozeloop.internal.httpclient.auth_client import JWTOAuthApp
from cozeloop.internal import consts
import httpx

@pytest.fixture
def mock_http_client():
    return MagicMock(spec=httpx)

@pytest.fixture
def jwt_oauth_app(mock_http_client):
    return JWTOAuthApp(
        client_id="test_client_id",
        public_key_id="test_public_key",
        private_key='''-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCz+ZYCeTPBV/G5
EwZGamN13draYthjIgnjtQJxsmHa7R2SvcylPi7w6Ihn31DJkLuQNhW71/1lP50Z
NiIB6loKxtc31Q/CCgUwdYI9NztANaBMAvq9qZW/CIC8IFvprnoa0VtoYNgNGuqI
NaAFV8cE8RJpiZ15Yd7e0rK7BtFN2DkcjxayjsOh1Xm3bvGVpjeBGW+YthW9yo+P
kPKFmu2gbhknJgmU4+IVIcvPz+rDIoYz0X6BKPABRJ9wc0Z8MW99cnb10D9Q5781
lX2b4YjShIjLdj3cUKfQWZoX7wOtni8/yvYqpiZoxCulITTXyNBwbzkQR7q0RttZ
5ukgnSPHAgMBAAECggEAEzRtlCioI9g6lxaMnjROwLkX2CNMFpKp83578EiqCy6E
8AUI3WkxS8vEd9vAnIGxQhuYs3QXj2z7r+uy3U7LT53AQYOe1tndi+To15duidTZ
x21Z9vstsODmES0ddxDYlBwFtlxUhwbO7WdWLWZxz6PZ5HZ8M1kE60oYgGn4fmcy
fdr7dpEtKKLoFGOhWhKPHKkvVsjTGgEQDS/JJQ01CToe30Qwm20CtdeqUSj5aSHt
4WCoDM0zS8qvyI66y6Hj/zC+Uy2Pe7dccUbxy/X/MYIZ4R5NUNC0hs01zmxctIz1
+ThWDTt2+gyIJV8jdsOYBIYl0/2S9TGaumns9Hn6AQKBgQDcI/FYTWKQrGgq0heh
dM4FVKoE9++CJVBCeztz6MMZXRby0rbuwCgft4hb195UzdHxeZJznAkf745Kb8px
HBNcTlqtXtLFdu/jPEsJtr+cc5QK/gGsqMBWB9bwNDWC505RDpjbljEnGv2pCWNr
l8ocCb4rklvsLodxpHlQ9hCAQQKBgQDRSrTtokHhSOMOfpwqrcHx32ebcAKXM5W0
eIsls7JqEINRU/ryCo8FeGfkGi8veyvpxvDyGIXFGYvu39EsQ/qOVjXMRvLWAPWo
NqpYprbR4tI0LeTiQXLvvshjePM5+BWYj3UxdmJkxRTEbhU4Xaf3zRwmWs0MEO28
JTlkfOEiBwKBgFgcTsIQHy5Ww064TlsCPF+n1nEsp4GI28nwNwiallQ1jTTdn/iJ
ksW3GO3hxgxdYPVsunBpeMF+iY5DllyVZy5f8i1IMcZ1Z2ilPkeCDMla/Vs09Yic
9na4po/35Z8iY5dP52CkicHkLLkWl+N9mpiEUchwyTgMG4whz6jXBB3BAoGAGVI5
i5qa79+6oNFOoZc+JL5LsbGejp6OGTSQWTJhfpWa3acUcF44qYfEwgMs/EihqnoI
QrIW1R7fIDpx+zIKSVhC0AExdhTNo9lhSLJ64e/YULnQvFMAzeK+KdLDUpsiOb/5
hM923gw+E/nhlV03ajKlmjpYHoKZ0K6MQA0fy9cCgYEAoO+BW8WITLRJgyfRZW0r
t99wYg/6jw3YiErzQjLntki9WflEsxvM6sRhNsHcUMvV01IeeFXW3TkRao9QZSc7
tt0xwhEZBT693So7I5FTP3Wbf64fw4vE0JCA3YqEwVRdatO6Xcm327xY2u0exLnz
6gQ2JKv+sdilxSPmRVm+hl8=
-----END PRIVATE KEY-----''',
        base_url="http://test.com",
        http_client=mock_http_client
    )

def test_get_access_token_success(jwt_oauth_app, mock_http_client):
    expires_in = int(time.time()) + 3600
    http_response = httpx.Response(200, json={"access_token": "test_token", "expires_in": expires_in})
    mock_http_client.request.return_value = http_response

    token = jwt_oauth_app.get_access_token()

    assert token.access_token == "test_token"
    assert token.expires_in == expires_in

def test_get_access_token_http_error(jwt_oauth_app, mock_http_client):
    mock_http_client.request.side_effect = httpx.HTTPError("Network error")

    with pytest.raises(consts.NetworkError):
        jwt_oauth_app.get_access_token()
