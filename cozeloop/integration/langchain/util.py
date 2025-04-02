# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import tiktoken
from typing import List, Dict, Union, Any, Optional
from langchain.schema import LLMResult
from langchain_core.outputs import Generation, ChatGeneration


def calc_token_usage(inputs: Union[List[Dict], LLMResult], model: str = 'gpt-3.5-turbo-0613'):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print('Warning: model not found. Using cl100k_base encoding.')
        encoding = tiktoken.get_encoding('cl100k_base')
    if model == 'gpt-3.5-turbo-0301':
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif model.startswith(('gpt-3.5', 'gpt-35', 'gpt-4')):
        tokens_per_message = 3
        tokens_per_name = 1
    else:
        tokens_per_message = 3
        tokens_per_name = 1
    num_tokens = 0
    if isinstance(inputs, List):
        for message in inputs:
            num_tokens += tokens_per_message
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == 'name':
                    num_tokens += tokens_per_name
    elif isinstance(inputs, LLMResult):
        for inner_generations in inputs.generations:
            for generation in inner_generations:
                if isinstance(generation, ChatGeneration):
                    num_tokens += len(encoding.encode(generation.message.type)) + len(encoding.encode(generation.message.content))
                elif isinstance(generation, Generation):
                    num_tokens += len(encoding.encode('ai')) + len(encoding.encode(generation.text))
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens



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