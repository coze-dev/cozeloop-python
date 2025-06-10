# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import List, Optional, Any

from pydantic import BaseModel

from cozeloop.spec.tracespec import ModelMessage


class PromptInput(BaseModel):
    templates: Optional[List['ModelMessage']] = None
    arguments: Optional[List['PromptArgument']] = None


class PromptArgument(BaseModel):
    key: str = ""
    value: Optional[Any] = None


class PromptOutput(BaseModel):
    prompts: Optional[List['ModelMessage']] = None
