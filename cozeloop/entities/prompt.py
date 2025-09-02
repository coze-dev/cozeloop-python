# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field, ConfigDict


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
    MULTI_PART_VARIABLE = "multi_part_variable"


class ContentPart(BaseModel):
    type: ContentType
    text: Optional[str] = None
    image_url: Optional[str] = None


class Message(BaseModel):
    role: Role
    content: Optional[str] = None
    parts: Optional[List[ContentPart]] = None


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


MessageLikeObject = Union[Message, List[Message]]
PromptVariable = Union[str, MessageLikeObject]
