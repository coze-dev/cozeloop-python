# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from enum import Enum
from typing import List, Optional

import pydantic
from pydantic import BaseModel, ConfigDict

from cozeloop.internal.httpclient import Client, BaseResponse

MPULL_PROMPT_PATH = "/v1/loop/prompts/mget"
EXECUTE_PROMPT_PATH = "/v1/loop/prompts/execute"
EXECUTE_STREAMING_PROMPT_PATH = "/v1/loop/prompts/execute_streaming"
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
    IMAGE_URL = "image_url"
    BASE64_DATA = "base64_data"
    MULTI_PART_VARIABLE = "multi_part_variable"


class ContentPart(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    type: ContentType
    text: Optional[str] = None
    image_url: Optional[str] = None
    base64_data: Optional[str] = None


class FunctionCall(BaseModel):
    name: str
    arguments: Optional[str] = None


class ToolCall(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    index: int
    id: str
    type: ToolType
    function_call: Optional[FunctionCall] = None


class Message(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    role: Role
    reasoning_content: Optional[str] = None
    content: Optional[str] = None
    parts: Optional[List[ContentPart]] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None


class VariableDef(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    key: str
    desc: str
    type: VariableType


class Function(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Optional[str] = None


class Tool(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    type: ToolType
    function: Optional[Function] = None
class ToolCallConfig(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    tool_choice: ToolChoiceType
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
    model_config = ConfigDict(use_enum_values=True)
    
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


# Execute相关数据结构
class VariableVal(BaseModel):
    key: str
    value: Optional[str] = None
    placeholder_messages: Optional[List[Message]] = None
    multi_part_values: Optional[List[ContentPart]] = None


class ExecuteRequest(BaseModel):
    workspace_id: str
    prompt_identifier: Optional[PromptQuery] = None
    variable_vals: Optional[List[VariableVal]] = None
    messages: Optional[List[Message]] = None


# HTTP接口专用的Token使用统计（字段名对齐HTTP接口）
class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class ExecuteData(BaseModel):
    message: Optional[Message] = None
    finish_reason: Optional[str] = None
    usage: Optional[TokenUsage] = None


class ExecuteResponse(BaseResponse):
    data: Optional[ExecuteData] = None


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

    def execute(self, request: ExecuteRequest, timeout: Optional[int] = None) -> ExecuteData:
        """Execute Prompt request"""
        response = self.http_client.request(
            EXECUTE_PROMPT_PATH, 
            "POST", 
            ExecuteResponse, 
            json=request,
            timeout=timeout
        )
        if response.data is None:
            raise ValueError("Execute response data is None")
        return response.data

    def execute_streaming(self, request: ExecuteRequest, timeout: Optional[int] = None):
        """Execute Prompt request in streaming mode"""
        return self.http_client.post_stream(EXECUTE_STREAMING_PROMPT_PATH, request, timeout=timeout)

    async def aexecute(self, request: ExecuteRequest, timeout: Optional[int] = None) -> ExecuteData:
        """Asynchronously execute Prompt request"""
        response = await self.http_client.arequest(
            EXECUTE_PROMPT_PATH, 
            "POST", 
            ExecuteResponse, 
            json=request,
            timeout=timeout
        )
        if response.data is None:
            raise ValueError("Execute response data is None")
        return response.data

    async def aexecute_streaming(self, request: ExecuteRequest, timeout: Optional[int] = None):
        """Asynchronously execute Prompt request in streaming mode"""
        return await self.http_client.apost_stream(EXECUTE_STREAMING_PROMPT_PATH, request, timeout=timeout)