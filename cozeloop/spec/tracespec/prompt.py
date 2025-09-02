# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
from enum import Enum
from typing import List, Optional, Any

from pydantic import BaseModel

from cozeloop.spec.tracespec import ModelMessage


class PromptInput(BaseModel):
    templates: Optional[List['ModelMessage']] = None
    arguments: Optional[List['PromptArgument']] = None


class PromptArgumentValueType(str, Enum):
    TEXT = "text"
    MODEL_MESSAGE = "model_message"
    MODEL_MESSAGE_PART = "model_message_part"


class PromptArgument(BaseModel):
    key: str = ""
    value: Optional[Any] = None
    source: Optional[str] = None
    value_type: PromptArgumentValueType


class PromptOutput(BaseModel):
    prompts: Optional[List['ModelMessage']] = None
