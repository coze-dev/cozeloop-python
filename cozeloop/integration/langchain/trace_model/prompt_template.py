# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
from typing import Optional, List, Any, Union, Tuple
from pydantic import BaseModel
from langchain_core.messages import BaseMessage, SystemMessage

from cozeloop.integration.langchain.trace_model import Message


def _convert_message(value: Any) -> Any:
    if isinstance(value, dict):
        format_value = {}
        for key, val in value.items():
            format_value[key] = _convert_message(val)
        return format_value
    if isinstance(value, list):
        format_value = []
        for each in value:
            format_value.append(_convert_message(each))
        return format_value
    if isinstance(value, BaseMessage):
        return Message(role=value.type, content=value.content)
    return value


class Argument(BaseModel):
    key: Optional[str]
    value: Optional[Any]
    source: Optional[str] = 'input'

    def __post_init__(self):
        self.value = _convert_message(self.value)


class PromptTraceInput(BaseModel):
    arguments: Optional[List[Argument]]
    templates: Optional[List[Message]] = None

    def to_json(self):
        return json.dumps(
            self,
            default=lambda o: dict((key, value) for key, value in o.__dict__.items() if value is not None),
            sort_keys=False,
            ensure_ascii=False)


class PromptTraceOutput(BaseModel):
    prompts: Optional[List[Message]]

    def to_json(self):
        return json.dumps(
            self,
            default=lambda o: dict((key, value) for key, value in o.__dict__.items() if value is not None),
            sort_keys=False,
            ensure_ascii=False)
