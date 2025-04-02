# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import cozeloop


def test_new_client():
    client1 = cozeloop.new_client(workspace_id="123", api_token="token")
    client2 = cozeloop.new_client(workspace_id="123", api_token="token")
    client3 = cozeloop.new_client(workspace_id="456", api_token="token")

    assert client1 == client2
    assert client1 != client3
