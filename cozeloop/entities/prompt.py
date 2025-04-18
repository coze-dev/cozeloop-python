# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from enum import Enum
from typing import List, Optional, Union

from pydantic import BaseModel, Field, ConfigDict


class TemplateType(str, Enum):
    NORMAL = "normal"


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


class ToolChoiceType(str, Enum):
    AUTO = "auto"
    NONE = "none"


class Message(BaseModel):
    role: Role
    content: Optional[str] = None


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
