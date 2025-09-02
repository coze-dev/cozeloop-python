# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from enum import Enum
from typing import List, Optional

import pydantic
from pydantic import BaseModel

from cozeloop.internal.httpclient import Client, BaseResponse

MPULL_PROMPT_PATH = "/v1/loop/prompts/mget"
MAX_PROMPT_QUERY_BATCH_SIZE = 25


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
    MULTI_PART_VARIABLE = "multi_part_variable"


class ContentPart(BaseModel):
    type: ContentType
    text: Optional[str] = None


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
    workspace_id: str
    prompt_key: str
    version: str
    prompt_template: Optional[PromptTemplate] = None
    tools: Optional[List[Tool]] = None
    tool_call_config: Optional[ToolCallConfig] = None
    llm_config: Optional[LLMConfig] = None


class PromptQuery(BaseModel):
    prompt_key: str
    version: Optional[str] = None
    label: Optional[str] = None


class MPullPromptRequest(BaseModel):
    workspace_id: str
    queries: List[PromptQuery]


class PromptResult(BaseModel):
    query: PromptQuery
    prompt: Optional[Prompt] = None


class PromptResultData(BaseModel):
    items: Optional[List[PromptResult]] = None


class MPullPromptResponse(BaseResponse):
    data: Optional[PromptResultData] = None


class OpenAPIClient:
    def __init__(self, http_client: Client):
        self.http_client = http_client

    def mpull_prompt(self, workspace_id: str, queries: List[PromptQuery]) -> List[PromptResult]:
        sorted_queries = sorted(queries, key=lambda x: (x.prompt_key, x.version))

        all_prompts = []
        # If query count is less than or equal to the maximum batch size, execute directly
        if len(sorted_queries) <= MAX_PROMPT_QUERY_BATCH_SIZE:
            batch_results = self._do_mpull_prompt(workspace_id, sorted_queries)
            if batch_results is not None:
                all_prompts.extend(batch_results)
            return all_prompts

        # Process large number of queries in batches
        for i in range(0, len(sorted_queries), MAX_PROMPT_QUERY_BATCH_SIZE):
            batch_queries = sorted_queries[i:i + MAX_PROMPT_QUERY_BATCH_SIZE]
            batch_results = self._do_mpull_prompt(workspace_id, batch_queries)
            if batch_results is not None:
                all_prompts.extend(batch_results)

        return all_prompts

    def _do_mpull_prompt(self, workspace_id: str, queries: List[PromptQuery]) -> Optional[List[PromptResult]]:
        if not queries:
            return None
        request = MPullPromptRequest(workspace_id=workspace_id, queries=queries)
        response = self.http_client.post(MPULL_PROMPT_PATH, MPullPromptResponse, request)
        real_resp = None
        if pydantic.VERSION.startswith('1'):
            real_resp = MPullPromptResponse.parse_obj(response)
        else:
            real_resp = MPullPromptResponse.model_validate(response)
        if real_resp.data is not None:
            return real_resp.data.items
