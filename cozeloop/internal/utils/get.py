# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import time
import random

from ..consts import MAX_BYTES_OF_ONE_TAG_KEY_DEFAULT, MAX_BYTES_OF_ONE_TAG_VALUE_DEFAULT, TAG_VALUE_SIZE_LIMIT
from ..idgen import get_multiple_delta_id_generator


def gen_16char_id() -> str:
    rand = get_multiple_delta_id_generator().gen_id()
    return f"{rand & 0xFFFFFFFFFFFFFFFF:016x}"

def gen_32char_id() -> str:
    high = (int(time.time()) + get_multiple_delta_id_generator().gen_id()) & 0xFFFFFFFFFFFFFFFF
    low = get_multiple_delta_id_generator().gen_id() & 0xFFFFFFFFFFFFFFFF
    return f"{high:016x}{low:016x}"

def get_tag_value_size_limit(tag_key: str) -> int:
    return TAG_VALUE_SIZE_LIMIT.get(tag_key, MAX_BYTES_OF_ONE_TAG_VALUE_DEFAULT)

def get_tag_key_size_limit() -> int:
    return MAX_BYTES_OF_ONE_TAG_KEY_DEFAULT