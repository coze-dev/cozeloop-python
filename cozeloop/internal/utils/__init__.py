# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import random

from cozeloop.internal.utils.convert import (
    to_json,
    truncate_string_by_byte
)

from cozeloop.internal.utils.get import (
    get_tag_value_size_limit,
    get_tag_key_size_limit
)

def random_hex(length):
    hex_characters = "0123456789abcdef"
    return "".join(random.choice(hex_characters) for _ in range(length))

