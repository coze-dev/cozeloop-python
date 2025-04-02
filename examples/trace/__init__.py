# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import requests
import base64

def get_image_bytes(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.content


def get_url_base64(url: str) -> str:
    response = requests.get(url)
    response.raise_for_status()
    return base64.b64encode(response.content).decode('utf-8')
