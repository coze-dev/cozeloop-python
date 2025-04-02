# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import base64
from urllib.parse import urlparse

from typing import Tuple


def is_valid_url(url_str: str) -> bool:
    try:
        result = urlparse(url_str)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

def parse_valid_mdn_base64(mdn_base64: str) -> Tuple[str, bool]:
    ss = mdn_base64.split(",")
    if len(ss) != 2:
        return "", False

    base64_data = ss[1]
    if len(base64_data) == 0:
        return "", False

    try:
        base64.b64decode(base64_data, validate=True)
    except Exception:
        return "", False

    return base64_data, True

def is_valid_hex_str(s: str) -> bool:
    hex_digits = "0123456789abcdefABCDEF"
    return all(c in hex_digits for c in s)