# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import pytest
from unittest.mock import MagicMock, patch

from cozeloop.internal.httpclient import Client
from cozeloop.internal.prompt.openapi import (
    OpenAPIClient,
    PromptQuery,
    Prompt,
    MPullPromptRequest,
    MPullPromptResponse,
    PromptResult,
    PromptResultData,
    MAX_PROMPT_QUERY_BATCH_SIZE,
    Role,
    TemplateType,
    ToolType,
    VariableType,
    ToolChoiceType,
    Message,
    VariableDef,
    Function,
    Tool,
    ToolCallConfig,
    LLMConfig,
    PromptTemplate
)


@pytest.fixture
def mock_http_client():
    return MagicMock(spec=Client)


@pytest.fixture
def openapi_client(mock_http_client):
    return OpenAPIClient(http_client=mock_http_client)


def test_client_init(mock_http_client):
    # Test client initialization
    client = OpenAPIClient(http_client=mock_http_client)
    assert client.http_client == mock_http_client


def test_mpull_prompt_single_batch(openapi_client, mock_http_client):
    # Setup mock data
    workspace_id = "test_workspace"
    queries = [
        PromptQuery(prompt_key="prompt1", version="v1"),
        PromptQuery(prompt_key="prompt2", version="v2")
    ]
    
    # Setup mock response
    prompt1 = Prompt(workspace_id=workspace_id, prompt_key="prompt1", version="v1")
    prompt2 = Prompt(workspace_id=workspace_id, prompt_key="prompt2", version="v2")
    
    result1 = PromptResult(query=queries[0], prompt=prompt1)
    result2 = PromptResult(query=queries[1], prompt=prompt2)
    
    response_data = PromptResultData(items=[result1, result2])
    response = MPullPromptResponse(code=0, msg="", data=response_data)
    
    mock_http_client.post.return_value = response.dict()
    
    # Call the method
    results = openapi_client.mpull_prompt(workspace_id, queries)
    
    # Verify the results
    assert len(results) == 2
    assert results[0].query.prompt_key == "prompt1"
    assert results[0].prompt.prompt_key == "prompt1"
    assert results[1].query.prompt_key == "prompt2"
    assert results[1].prompt.prompt_key == "prompt2"
    
    # Verify the request
    mock_http_client.post.assert_called_once()
    args, kwargs = mock_http_client.post.call_args
    
    # Verify correct path and response type
    assert args[0] == "/v1/loop/prompts/mget"
    assert args[1] == MPullPromptResponse
    
    # Verify request data
    request_obj = args[2]
    assert isinstance(request_obj, MPullPromptRequest)
    assert request_obj.workspace_id == workspace_id
    assert len(request_obj.queries) == 2
    assert request_obj.queries[0].prompt_key == "prompt1"
    assert request_obj.queries[1].prompt_key == "prompt2"


def test_mpull_prompt_multiple_batches(openapi_client, mock_http_client):
    # Create more queries than MAX_PROMPT_QUERY_BATCH_SIZE
    workspace_id = "test_workspace"
    
    # Create MAX_PROMPT_QUERY_BATCH_SIZE + 5 queries
    queries = []
    for i in range(MAX_PROMPT_QUERY_BATCH_SIZE + 5):
        queries.append(PromptQuery(prompt_key=f"prompt{i}", version=f"v{i}"))
    
    # Setup first batch response
    first_batch_results = []
    for i in range(MAX_PROMPT_QUERY_BATCH_SIZE):
        prompt = Prompt(workspace_id=workspace_id, prompt_key=f"prompt{i}", version=f"v{i}")
        result = PromptResult(query=queries[i], prompt=prompt)
        first_batch_results.append(result)
    
    first_response_data = PromptResultData(items=first_batch_results)
    first_response = MPullPromptResponse(code=0, msg="", data=first_response_data)
    
    # Setup second batch response
    second_batch_results = []
    for i in range(MAX_PROMPT_QUERY_BATCH_SIZE, MAX_PROMPT_QUERY_BATCH_SIZE + 5):
        prompt = Prompt(workspace_id=workspace_id, prompt_key=f"prompt{i}", version=f"v{i}")
        result = PromptResult(query=queries[i], prompt=prompt)
        second_batch_results.append(result)
    
    second_response_data = PromptResultData(items=second_batch_results)
    second_response = MPullPromptResponse(code=0, msg="", data=second_response_data)
    
    # Configure mock to return different responses for each call
    mock_http_client.post.side_effect = [first_response.dict(), second_response.dict()]
    
    # Call the method
    results = openapi_client.mpull_prompt(workspace_id, queries)
    
    # Verify results
    assert len(results) == MAX_PROMPT_QUERY_BATCH_SIZE + 5
    
    # Verify the http client was called twice
    assert mock_http_client.post.call_count == 2
    
    # Verify first batch call
    first_call_args = mock_http_client.post.call_args_list[0][0]
    first_request = first_call_args[2]
    assert len(first_request.queries) == MAX_PROMPT_QUERY_BATCH_SIZE
    
    # Verify second batch call
    second_call_args = mock_http_client.post.call_args_list[1][0]
    second_request = second_call_args[2]
    assert len(second_request.queries) == 5


def test_mpull_prompt_empty_response(openapi_client, mock_http_client):
    # Setup test data
    workspace_id = "test_workspace"
    queries = [PromptQuery(prompt_key="prompt1", version="v1")]
    
    # Setup empty response
    response = MPullPromptResponse(code=0, msg="", data=None)
    mock_http_client.post.return_value = response.dict()
    
    # Call the method
    results = openapi_client.mpull_prompt(workspace_id, queries)
    
    # Verify empty list is returned
    assert results is None
    

def test_mpull_prompt_empty_items(openapi_client, mock_http_client):
    # Setup test data
    workspace_id = "test_workspace"
    queries = [PromptQuery(prompt_key="prompt1", version="v1")]
    
    # Setup response with empty items
    response_data = PromptResultData(items=None)
    response = MPullPromptResponse(code=0, msg="", data=response_data)
    mock_http_client.post.return_value = response.dict()
    
    # Call the method
    results = openapi_client.mpull_prompt(workspace_id, queries)
    
    # Verify None is returned
    assert results is None


def test_mpull_prompt_query_sorting(openapi_client, mock_http_client):
    # Setup test data with unsorted queries
    workspace_id = "test_workspace"
    queries = [
        PromptQuery(prompt_key="promptB", version="v1"),
        PromptQuery(prompt_key="promptA", version="v2"),
        PromptQuery(prompt_key="promptA", version="v1"),
    ]
    
    # Expected sort order: promptA-v1, promptA-v2, promptB-v1
    
    # Setup mock response
    response_data = PromptResultData(items=[])
    response = MPullPromptResponse(code=0, msg="", data=response_data)
    mock_http_client.post.return_value = response.dict()
    
    # Call method
    openapi_client.mpull_prompt(workspace_id, queries)
    
    # Verify queries were sorted before sending
    args, _ = mock_http_client.post.call_args
    request_obj = args[2]
    
    assert request_obj.queries[0].prompt_key == "promptA"
    assert request_obj.queries[0].version == "v1"
    assert request_obj.queries[1].prompt_key == "promptA"
    assert request_obj.queries[1].version == "v2"
    assert request_obj.queries[2].prompt_key == "promptB"
    assert request_obj.queries[2].version == "v1"


def test_enum_values():
    # Test Role enum values
    assert Role.SYSTEM == "system"
    assert Role.USER == "user"
    assert Role.ASSISTANT == "assistant"
    assert Role.TOOL == "tool"
    assert Role.PLACEHOLDER == "placeholder"
    
    # Test TemplateType enum values
    assert TemplateType.NORMAL == "normal"
    
    # Test ToolType enum values
    assert ToolType.FUNCTION == "function"
    
    # Test VariableType enum values
    assert VariableType.STRING == "string"
    assert VariableType.PLACEHOLDER == "placeholder"
    
    # Test ToolChoiceType enum values
    assert ToolChoiceType.AUTO == "auto"
    assert ToolChoiceType.NONE == "none"


def test_message_model():
    # Test Message model with required fields
    message = Message(role=Role.USER)
    assert message.role == Role.USER
    assert message.content is None
    
    # Test Message model with all fields
    message = Message(role=Role.SYSTEM, content="System message")
    assert message.role == Role.SYSTEM
    assert message.content == "System message"


def test_variable_def_model():
    # Test VariableDef model with required fields
    var_def = VariableDef(key="test_key", desc="Test description", type=VariableType.STRING)
    assert var_def.key == "test_key"
    assert var_def.desc == "Test description"
    assert var_def.type == VariableType.STRING


def test_function_model():
    # Test Function model with required fields
    func = Function(name="test_function")
    assert func.name == "test_function"
    assert func.description is None
    assert func.parameters is None
    
    # Test Function model with all fields
    func = Function(
        name="test_function",
        description="Test description",
        parameters='{"type": "object", "properties": {}}'
    )
    assert func.name == "test_function"
    assert func.description == "Test description"
    assert func.parameters == '{"type": "object", "properties": {}}'


def test_tool_model():
    # Test Tool model with required fields
    tool = Tool(type=ToolType.FUNCTION)
    assert tool.type == ToolType.FUNCTION
    assert tool.function is None
    
    # Test Tool model with all fields
    func = Function(name="test_function")
    tool = Tool(type=ToolType.FUNCTION, function=func)
    assert tool.type == ToolType.FUNCTION
    assert tool.function == func
    assert tool.function.name == "test_function"


def test_tool_call_config_model():
    # Test ToolCallConfig model
    config = ToolCallConfig(tool_choice=ToolChoiceType.AUTO)
    assert config.tool_choice == ToolChoiceType.AUTO


def test_llm_config_model():
    # Test LLMConfig model with default values
    config = LLMConfig()
    assert config.temperature is None
    assert config.max_tokens is None
    assert config.top_k is None
    assert config.top_p is None
    assert config.frequency_penalty is None
    assert config.presence_penalty is None
    assert config.json_mode is None
    
    # Test LLMConfig model with all fields
    config = LLMConfig(
        temperature=0.7,
        max_tokens=1024,
        top_k=50,
        top_p=0.95,
        frequency_penalty=0.1,
        presence_penalty=0.2,
        json_mode=True
    )
    assert config.temperature == 0.7
    assert config.max_tokens == 1024
    assert config.top_k == 50
    assert config.top_p == 0.95
    assert config.frequency_penalty == 0.1
    assert config.presence_penalty == 0.2
    assert config.json_mode is True


def test_prompt_template_model():
    # Test PromptTemplate model with required fields
    template = PromptTemplate(template_type=TemplateType.NORMAL)
    assert template.template_type == TemplateType.NORMAL
    assert template.messages is None
    assert template.variable_defs is None
    
    # Test PromptTemplate model with all fields
    messages = [Message(role=Role.USER, content="Test message")]
    var_defs = [VariableDef(key="test_var", desc="Test var", type=VariableType.STRING)]
    
    template = PromptTemplate(
        template_type=TemplateType.NORMAL,
        messages=messages,
        variable_defs=var_defs
    )
    assert template.template_type == TemplateType.NORMAL
    assert template.messages == messages
    assert template.variable_defs == var_defs


def test_prompt_model():
    # Test Prompt model with required fields
    prompt = Prompt(workspace_id="test_workspace", prompt_key="test_prompt", version="v1")
    assert prompt.workspace_id == "test_workspace"
    assert prompt.prompt_key == "test_prompt"
    assert prompt.version == "v1"
    assert prompt.prompt_template is None
    assert prompt.tools is None
    assert prompt.tool_call_config is None
    assert prompt.llm_config is None
    
    # Test Prompt model with all fields
    template = PromptTemplate(template_type=TemplateType.NORMAL)
    tools = [Tool(type=ToolType.FUNCTION)]
    tool_call_config = ToolCallConfig(tool_choice=ToolChoiceType.AUTO)
    llm_config = LLMConfig(temperature=0.7)
    
    prompt = Prompt(
        workspace_id="test_workspace",
        prompt_key="test_prompt",
        version="v1",
        prompt_template=template,
        tools=tools,
        tool_call_config=tool_call_config,
        llm_config=llm_config
    )
    assert prompt.workspace_id == "test_workspace"
    assert prompt.prompt_key == "test_prompt"
    assert prompt.version == "v1"
    assert prompt.prompt_template == template
    assert prompt.tools == tools
    assert prompt.tool_call_config == tool_call_config
    assert prompt.llm_config == llm_config


def test_prompt_query_model():
    # Test PromptQuery model with required fields
    query = PromptQuery(prompt_key="test_prompt")
    assert query.prompt_key == "test_prompt"
    assert query.version is None
    
    # Test PromptQuery model with all fields
    query = PromptQuery(prompt_key="test_prompt", version="v1")
    assert query.prompt_key == "test_prompt"
    assert query.version == "v1"


def test_mpull_prompt_request_model():
    # Test MPullPromptRequest model
    queries = [PromptQuery(prompt_key="test_prompt", version="v1")]
    request = MPullPromptRequest(workspace_id="test_workspace", queries=queries)
    assert request.workspace_id == "test_workspace"
    assert request.queries == queries


def test_prompt_result_model():
    # Test PromptResult model with required fields
    query = PromptQuery(prompt_key="test_prompt", version="v1")
    result = PromptResult(query=query)
    assert result.query == query
    assert result.prompt is None
    
    # Test PromptResult model with all fields
    prompt = Prompt(workspace_id="test_workspace", prompt_key="test_prompt", version="v1")
    result = PromptResult(query=query, prompt=prompt)
    assert result.query == query
    assert result.prompt == prompt


def test_prompt_result_data_model():
    # Test PromptResultData model with default values
    data = PromptResultData()
    assert data.items is None
    
    # Test PromptResultData model with items
    query = PromptQuery(prompt_key="test_prompt", version="v1")
    result = PromptResult(query=query)
    data = PromptResultData(items=[result])
    assert data.items == [result]


def test_mpull_prompt_response_model():
    # Test MPullPromptResponse model with default values
    response = MPullPromptResponse(code=0, msg="")
    assert response.data is None
    
    # Test MPullPromptResponse model with data
    data = PromptResultData()
    response = MPullPromptResponse(code=0, msg="", data=data)
    assert response.data == data
