# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import List

_startswith = 'fornax_prompt_tag'


def get_prompt_tag(tags: List[str]) -> List[str]:
    """
    When using it, you need to check if the returned list is empty. If it is not empty,
    index 0 represents prompt_key, and index 1 represents version.
    """
    for tag in tags:
        if tag.startswith(_startswith):
            return split_prompt_tag(tag)
    return []


def split_prompt_tag(prompt_dict_key: str) -> List[str]:
    return prompt_dict_key.split(':')[1:3]