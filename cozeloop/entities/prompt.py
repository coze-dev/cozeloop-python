# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from enum import Enum
from typing import List, Optional, Union
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel


class TemplateType(str, Enum):
    NORMAL = "normal"
    JINJA2 = "jinja2"


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    PLACEHOLDER = "placeholder"


class ToolType(str, Enum):
    FUNCTION = "function"


class VariableType(str, Enum):
    STRING = "string"
    PLACEHOLDER = "placeholder"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float"
    OBJECT = "object"
    ARRAY_STRING = "array<string>"
    ARRAY_BOOLEAN = "array<boolean>"
    ARRAY_INTEGER = "array<integer>"
    ARRAY_FLOAT = "array<float>"
    ARRAY_OBJECT = "array<object>"
    MULTI_PART = "multi_part"


class ToolChoiceType(str, Enum):
    AUTO = "auto"
    NONE = "none"


class ContentType(str, Enum):
    TEXT = "text"
    IMAGE_URL = "image_url"
    BASE64_DATA = "base64_data"
    MULTI_PART_VARIABLE = "multi_part_variable"


class ContentPart(BaseModel):
    type: ContentType
    text: Optional[str] = None
    image_url: Optional[str] = None
    base64_data: Optional[str] = None


class FunctionCall(BaseModel):
    name: str
    arguments: Optional[str] = None


class ToolCall(BaseModel):
    index: int
    id: str
    type: ToolType
    function_call: Optional[FunctionCall] = None


class Message(BaseModel):
    role: Role
    reasoning_content: Optional[str] = None
    content: Optional[str] = None
    parts: Optional[List[ContentPart]] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class VariableDef(BaseModel):
    key: str
    desc: str
    type: VariableType


class Function(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Optional[str] = None


class Tool(BaseModel):
    type: ToolType
    function: Optional[Function] = None


class ToolCallConfig(BaseModel):
    tool_choice: ToolChoiceType


class LLMConfig(BaseModel):
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    json_mode: Optional[bool] = None


class PromptTemplate(BaseModel):
    template_type: TemplateType
    messages: Optional[List[Message]] = None
    variable_defs: Optional[List[VariableDef]] = None


class Prompt(BaseModel):
    workspace_id: str = ""
    prompt_key: str
    version: str
    prompt_template: Optional[PromptTemplate] = None
    tools: Optional[List[Tool]] = None
    tool_call_config: Optional[ToolCallConfig] = None
    llm_config: Optional[LLMConfig] = None


class ExecuteParam(BaseModel):
    """Execute parameters"""
    prompt_key: str
    version: str = ""
    label: str = ""
    variable_vals: Optional[Dict[str, Any]] = None
    messages: Optional[List[Message]] = None


class TokenUsage(BaseModel):
    """Token usage statistics"""
    input_tokens: int = 0
    output_tokens: int = 0


class ExecuteResult(BaseModel):
    """Execute result"""
    message: Optional[Message] = None
    finish_reason: Optional[str] = None
    usage: Optional[TokenUsage] = None


MessageLikeObject = Union[Message, List[Message]]
PromptVariable = Union[str, MessageLikeObject]