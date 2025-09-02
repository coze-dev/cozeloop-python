# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel

# ModelInput is the input for model span, for tag key: input
class ModelInput(BaseModel):
    messages: Optional[List['ModelMessage']] = None
    tools: Optional[List['ModelTool']] = None
    model_tool_choice: Optional['ModelToolChoice'] = None


# ModelOutput is the output for model span, for tag key: output
class ModelOutput(BaseModel):
    choices: List['ModelChoice'] = []


# ModelCallOption is the option for model span, for tag key: call_options
class ModelCallOption(BaseModel):
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    stop: Optional[List[str]] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    top_k: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    reasoning_effort: Optional[str] = None


class ModelMessage(BaseModel):
    role: str = ""                            # from enum VRole in span_value
    content: Optional[str] = None             # single content
    reasoning_content: Optional[str] = None   # only for output
    parts: Optional[List['ModelMessagePart']] = None # multi-modality content
    name: Optional[str] = None
    tool_calls: Optional[List['ModelToolCall']] = None
    tool_call_id: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


class ModelMessagePartType(str, Enum):
    TEXT = "text"
    IMAGE = "image_url"
    FILE = "file_url"
    MULTI_PART_VARIABLE = "multi_part_variable" # Internal use only, unless you fully comprehend its functionality and risks


class ModelMessagePart(BaseModel):
    type: ModelMessagePartType
    text: Optional[str] = None
    image_url: Optional['ModelImageURL'] = None
    file_url: Optional['ModelFileURL'] = None


class ModelImageURL(BaseModel):
    name: Optional[str] = None
    # Required. You can enter a valid image URL or MDN Base64 data of an image().
    # MDN: https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Schemes/data#syntax
    url: str = ""
    detail: Optional[str] = None


class ModelFileURL(BaseModel):
    name: Optional[str] = None
    # Required. You can enter a valid file URL or MDN Base64 data of file.
    # MDN: https://developer.mozilla.org/en-US/docs/Web/URI/Reference/Schemes/data#syntax
    url: str = ""
    detail: Optional[str] = None
    suffix: Optional[str] = None


class ModelToolCall(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None
    function: Optional['ModelToolCallFunction'] = None


class ModelToolCallFunction(BaseModel):
    name: str = ""
    arguments: Optional[str] = None


class ModelTool(BaseModel):
    type: str = "function"
    function: Optional['ModelToolFunction'] = None


class ModelToolFunction(BaseModel):
    name: str = ""
    description: str = ""
    parameters: Optional[dict] = None


class ModelChoice(BaseModel):
    finish_reason: str = ""
    index: int = 0
    message: Optional['ModelMessage'] = None


class ModelToolChoice(BaseModel):
    type: str = ""                                       # from enum VToolChoice in span_value
    function: Optional['ModelToolCallFunction'] = None   # field name only.
