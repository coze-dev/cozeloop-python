# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import Dict, Optional
from unittest.mock import MagicMock

import httpx
import pytest
from pydantic import BaseModel

from cozeloop.internal import consts
from cozeloop.internal.httpclient import Client, BaseResponse
from cozeloop.internal.httpclient.user_agent import user_agent_header


class MockResponse(BaseResponse):
    code: int
    msg: str


@pytest.fixture
def mock_client():
    mock_http_client = MagicMock(spec=httpx.Client)
    mock_auth = MagicMock()
    mock_auth.token = "test_token"
    return Client(
        api_base_url="http://test.com",
        http_client=mock_http_client,
        auth=mock_auth,
        timeout=10,
        upload_timeout=20
    )


def expect_header(content_type: str = "") -> Dict[str, str]:
    headers = user_agent_header()
    if content_type:
        headers["Content-Type"] = content_type
    headers["Authorization"] = "Bearer test_token"
    return headers


def test_request_dict_success(mock_client):
    class TestResponse(BaseResponse):
        i: int

    http_response = httpx.Response(200, json={"code": 0, "msg": "Success", "i": 1})
    mock_client.http_client.request.return_value = http_response

    response = mock_client.request(
        path="/test",
        method="GET",
        response_model=TestResponse,
        json={"i": 1}
    )

    assert response.code == 0
    assert response.msg == "Success"
    assert response.i == 1
    mock_client.http_client.request.assert_called_once_with(
        "GET",
        "http://test.com/test",
        headers=expect_header(),
        json={"i": 1},
        timeout=10,
        params=None,
        data=None,
        files=None
    )


def test_request_base_model_success(mock_client):
    class TestResponse(BaseResponse):
        i: int

    class TestRequest(BaseModel):
        i: int

    http_response = httpx.Response(200, json={"code": 0, "msg": "Success", "i": 1})
    mock_client.http_client.request.return_value = http_response

    response = mock_client.request(
        path="/test",
        method="GET",
        response_model=TestResponse,
        json=TestRequest(i=1)
    )

    assert response.code == 0
    assert response.msg == "Success"
    assert response.i == 1
    mock_client.http_client.request.assert_called_once_with(
        "GET",
        "http://test.com/test",
        headers=expect_header(),
        json={"i": 1},
        timeout=10,
        params=None,
        data=None,
        files=None
    )


def test_request_no_json_error(mock_client):
    http_response = httpx.Response(404, content="return html.")
    mock_client.http_client.request.return_value = http_response

    with pytest.raises(consts.RemoteServiceError) as e:
        mock_client.request(
            path="/test",
            method="GET",
            response_model=MockResponse
        )
    mock_client.http_client.request.assert_called_once()
    assert e.value.http_code == 404


def test_request_auth_error(mock_client):
    http_response = httpx.Response(401, json={"error": "e", "error_code": "c", "error_message": "m"})
    mock_client.http_client.request.return_value = http_response

    with pytest.raises(consts.AuthError) as e:
        mock_client.request(
            path="/test",
            method="GET",
            response_model=MockResponse
        )
    mock_client.http_client.request.assert_called_once()
    assert e.value.http_code == 401
    assert e.value.code == "c"


def test_request_server_error(mock_client):
    http_response = httpx.Response(500, json={"code": 100, "msg": "error"})
    mock_client.http_client.request.return_value = http_response

    with pytest.raises(consts.RemoteServiceError) as e:
        mock_client.request(
            path="/test",
            method="GET",
            response_model=MockResponse
        )
    mock_client.http_client.request.assert_called_once()
    assert e.value.http_code == 500
    assert e.value.error_code == 100
    assert e.value.error_message == "error"


def test_request_response_data_validate_error(mock_client):
    class TestResponse(BaseResponse):
        code: int
        msg: str
        data: str
    http_response = httpx.Response(200, json={"code": 0, "msg": "", "data": 1})
    mock_client.http_client.request.return_value = http_response

    with pytest.raises(consts.InternalError) as e:
        mock_client.request(
            path="/test",
            method="GET",
            response_model=TestResponse
        )
    mock_client.http_client.request.assert_called_once()


def test_request_http_error(mock_client):
    mock_client.http_client.request.side_effect = httpx.HTTPError("Test HTTPError"),

    with pytest.raises(consts.NetworkError):
        mock_client.request(
            path="/test",
            method="GET",
            response_model=MockResponse
        )

    mock_client.http_client.request.assert_called_once()


def test_get_success(mock_client):
    http_response = httpx.Response(200, json={"code": 0, "msg": "Success"})
    mock_client.http_client.request.return_value = http_response

    response = mock_client.get(
        path="/test",
        response_model=MockResponse,
        params={"s": "a"}
    )

    assert response.code == 0
    assert response.msg == "Success"
    mock_client.http_client.request.assert_called_once_with(
        "GET",
        "http://test.com/test",
        params={"s": "a"},
        data=None,
        json=None,
        files=None,
        headers=expect_header("application/json"),
        timeout=10,
    )


def test_post_success(mock_client):
    http_response = httpx.Response(200, json={"code": 0, "msg": "Success"})
    mock_client.http_client.request.return_value = http_response

    response = mock_client.post(
        path="/test",
        response_model=BaseResponse,
        json={"s": "a"}
    )

    assert response.code == 0
    assert response.msg == "Success"
    mock_client.http_client.request.assert_called_once_with(
        "POST",
        "http://test.com/test",
        data=None,
        params=None,
        json={"s": "a"},
        files=None,
        headers=expect_header("application/json"),
        timeout=10,
    )


def test_upload_file_success(mock_client):
    http_response = httpx.Response(200, json={"code": 0, "msg": "Success"})
    mock_client.http_client.request.return_value = http_response

    response = mock_client.upload_file(
        path="/test",
        response_model=BaseResponse,
        file=b"abcde",
        file_name="test_file",
        form={"s": "a"}
    )

    assert response.code == 0
    assert response.msg == "Success"
    mock_client.http_client.request.assert_called_once_with(
        "POST",
        "http://test.com/test",
        params=None,
        data={"s": "a"},
        json=None,
        files={"file": ("test_file", b"abcde")},
        headers=expect_header(),
        timeout=20,
    )
