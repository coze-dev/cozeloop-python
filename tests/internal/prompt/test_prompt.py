# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import pytest
from unittest.mock import MagicMock, patch, call

from cozeloop.entities.prompt import (
    Prompt, Message, VariableDef, VariableType, TemplateType, Role, PromptVariable
)
from cozeloop.internal import consts
from cozeloop.internal.consts.error import RemoteServiceError
from cozeloop.internal.httpclient.client import Client
from cozeloop.internal.prompt.cache import PromptCache
from cozeloop.internal.prompt.openapi import OpenAPIClient, PromptQuery, Prompt as OpenAPIPrompt
from cozeloop.internal.trace.trace import TraceProvider
from cozeloop.internal.prompt.prompt import PromptProvider, CustomUndefined


@pytest.fixture
def mock_http_client():
    return MagicMock(spec=Client)


@pytest.fixture
def mock_trace_provider():
    provider = MagicMock(spec=TraceProvider)
    span = MagicMock()
    provider.start_span.return_value.__enter__.return_value = span
    return provider


@pytest.fixture
def mock_openapi_client():
    return MagicMock(spec=OpenAPIClient)


@pytest.fixture
def mock_prompt_cache():
    cache = MagicMock(spec=PromptCache)
    return cache


@pytest.fixture
def prompt_provider(mock_http_client, mock_trace_provider):
    with patch('cozeloop.internal.prompt.prompt.OpenAPIClient') as mock_openapi_client_class, \
         patch('cozeloop.internal.prompt.prompt.PromptCache') as mock_prompt_cache_class:
        
        mock_openapi_client = mock_openapi_client_class.return_value
        mock_prompt_cache = mock_prompt_cache_class.return_value
        
        provider = PromptProvider(
            workspace_id="test_workspace",
            http_client=mock_http_client,
            trace_provider=mock_trace_provider,
            prompt_cache_max_count=100,
            prompt_cache_refresh_interval=60,
            prompt_trace=False
        )
        
        # Replace the openapi_client and cache with mocks for easier testing
        provider.openapi_client = mock_openapi_client
        provider.cache = mock_prompt_cache
        
        yield provider


def test_init(mock_http_client, mock_trace_provider):
    # Test initialization of PromptProvider
    with patch('cozeloop.internal.prompt.prompt.OpenAPIClient') as mock_openapi_client_class, \
         patch('cozeloop.internal.prompt.prompt.PromptCache') as mock_prompt_cache_class:
        
        provider = PromptProvider(
            workspace_id="test_workspace",
            http_client=mock_http_client,
            trace_provider=mock_trace_provider,
            prompt_cache_max_count=200,
            prompt_cache_refresh_interval=120,
            prompt_trace=True
        )
        
        # Verify OpenAPIClient was initialized with the http_client
        mock_openapi_client_class.assert_called_once_with(mock_http_client)
        
        # Verify PromptCache was initialized with the correct parameters
        mock_prompt_cache_class.assert_called_once_with(
            "test_workspace", 
            provider.openapi_client,
            refresh_interval=120,
            max_size=200,
            auto_refresh=True
        )
        
        # Verify instance variables
        assert provider.workspace_id == "test_workspace"
        assert provider.prompt_trace is True
        assert provider.trace_provider == mock_trace_provider


def test_get_prompt_from_cache(prompt_provider):
    # Setup mock prompt
    mock_prompt = MagicMock(spec=Prompt)
    mock_prompt.copy.return_value = mock_prompt
    
    # Setup cache hit
    prompt_provider.cache.get.return_value = mock_prompt
    
    # Call method
    result = prompt_provider.get_prompt("test_prompt", "v1")
    
    # Verify result
    assert result == mock_prompt
    
    # Verify cache was checked
    prompt_provider.cache.get.assert_called_once_with("test_prompt", "v1")
    
    # Verify API was not called
    prompt_provider.openapi_client.mpull_prompt.assert_not_called()


def test_get_prompt_from_api(prompt_provider):
    # Setup cache miss
    prompt_provider.cache.get.return_value = None
    
    # Setup API response
    api_prompt = MagicMock(spec=OpenAPIPrompt)
    query = PromptQuery(prompt_key="test_prompt", version="v1")
    prompt_result = MagicMock()
    prompt_result.prompt = api_prompt
    prompt_result.query = query
    prompt_provider.openapi_client.mpull_prompt.return_value = [prompt_result]
    
    # Setup converted prompt
    entity_prompt = MagicMock(spec=Prompt)
    entity_prompt.copy.return_value = entity_prompt
    
    # Mock the converter function
    with patch('cozeloop.internal.prompt.prompt._convert_prompt') as mock_convert_prompt:
        mock_convert_prompt.return_value = entity_prompt
        
        # Call method
        result = prompt_provider.get_prompt("test_prompt", "v1")
        
        # Verify result
        assert result == entity_prompt
        
        # Verify cache was checked
        prompt_provider.cache.get.assert_called_once_with("test_prompt", "v1")
        
        # Verify API was called
        prompt_provider.openapi_client.mpull_prompt.assert_called_once_with(
            "test_workspace", 
            [PromptQuery(prompt_key="test_prompt", version="v1")]
        )
        
        # Verify prompt was converted
        mock_convert_prompt.assert_called_once_with(api_prompt)
        
        # Verify prompt was cached
        prompt_provider.cache.set.assert_called_once_with("test_prompt", "v1", entity_prompt)


def test_get_prompt_with_trace(prompt_provider, mock_trace_provider):
    # Enable tracing
    prompt_provider.prompt_trace = True
    
    # Setup cache miss
    prompt_provider.cache.get.return_value = None
    
    # Setup API response
    api_prompt = MagicMock(spec=OpenAPIPrompt)
    query = PromptQuery(prompt_key="test_prompt", version="v1")
    prompt_result = MagicMock()
    prompt_result.prompt = api_prompt
    prompt_result.query = query
    prompt_provider.openapi_client.mpull_prompt.return_value = [prompt_result]
    
    # Setup converted prompt
    entity_prompt = MagicMock(spec=Prompt)
    entity_prompt.version = "v1"
    entity_prompt.model_dump_json.return_value = '{"key": "value"}'
    entity_prompt.copy.return_value = entity_prompt
    
    # Mock the converter function
    with patch('cozeloop.internal.prompt.prompt._convert_prompt') as mock_convert_prompt:
        mock_convert_prompt.return_value = entity_prompt
        
        # Call method
        result = prompt_provider.get_prompt("test_prompt", "v1")
        
        # Verify result
        assert result == entity_prompt
        
        # Verify span was created
        mock_trace_provider.start_span.assert_called_once_with(
            consts.TRACE_PROMPT_HUB_SPAN_NAME,
            consts.TRACE_PROMPT_HUB_SPAN_TYPE
        )
        
        # Verify span was tagged with input
        span = mock_trace_provider.start_span.return_value.__enter__.return_value
        span.set_tags.assert_any_call({
            consts.PROMPT_KEY: "test_prompt",
            consts.INPUT: json.dumps({consts.PROMPT_KEY: "test_prompt", consts.PROMPT_VERSION: "v1"})
        })
        
        # Verify span was tagged with output
        span.set_tags.assert_any_call({
            consts.PROMPT_VERSION: "v1",
            consts.OUTPUT: '{"key": "value"}',
        })


def test_get_prompt_with_trace_api_error(prompt_provider, mock_trace_provider):
    # Enable tracing
    prompt_provider.prompt_trace = True
    
    # Setup cache miss
    prompt_provider.cache.get.return_value = None
    
    # Setup API error
    error = RemoteServiceError(500, 600400301, "Service unavailable", "ADSFVSFSD1")
    prompt_provider.openapi_client.mpull_prompt.side_effect = error
    
    # Call method and expect exception
    with pytest.raises(RemoteServiceError):
        prompt_provider.get_prompt("test_prompt", "v1")
    
    # Verify span was created
    mock_trace_provider.start_span.assert_called_once_with(
        consts.TRACE_PROMPT_HUB_SPAN_NAME,
        consts.TRACE_PROMPT_HUB_SPAN_TYPE
    )
    
    # Verify span was tagged with error
    span = mock_trace_provider.start_span.return_value.__enter__.return_value
    span.set_tags.assert_any_call({
        consts.STATUS_CODE: 600400301,
        consts.ERROR: "Service unavailable",
    })


def test_get_prompt_with_trace_general_error(prompt_provider, mock_trace_provider):
    # Enable tracing
    prompt_provider.prompt_trace = True
    
    # Setup cache miss
    prompt_provider.cache.get.return_value = None
    
    # Setup general error
    error = ValueError("Invalid parameter")
    prompt_provider.openapi_client.mpull_prompt.side_effect = error
    
    # Call method and expect exception
    with pytest.raises(ValueError):
        prompt_provider.get_prompt("test_prompt", "v1")
    
    # Verify span was created
    mock_trace_provider.start_span.assert_called_once_with(
        consts.TRACE_PROMPT_HUB_SPAN_NAME,
        consts.TRACE_PROMPT_HUB_SPAN_TYPE
    )
    
    # Verify span was tagged with error
    span = mock_trace_provider.start_span.return_value.__enter__.return_value
    span.set_tags.assert_any_call({
        consts.ERROR: "Invalid parameter"
    })


def test_prompt_format_normal(prompt_provider):
    # Setup test data
    message1 = Message(role=Role.SYSTEM, content="Hello {{name}}")
    message2 = Message(role=Role.USER, content="How are you, {{name}}?")
    
    var_def = VariableDef(key="name", desc="User name", type=VariableType.STRING)
    
    prompt_template = MagicMock()
    prompt_template.template_type = TemplateType.NORMAL
    prompt_template.messages = [message1, message2]
    prompt_template.variable_defs = [var_def]
    
    prompt = MagicMock(spec=Prompt)
    prompt.prompt_template = prompt_template
    
    variables = {"name": "Alice"}
    
    # Call method
    result = prompt_provider.prompt_format(prompt, variables)
    
    # Verify result
    assert len(result) == 2
    assert result[0].role == Role.SYSTEM
    assert result[0].content == "Hello Alice"
    assert result[1].role == Role.USER
    assert result[1].content == "How are you, Alice?"


def test_prompt_format_with_placeholder(prompt_provider):
    # Setup test data
    system_message = Message(role=Role.SYSTEM, content="You are a helpful assistant.")
    placeholder_message = Message(role=Role.PLACEHOLDER, content="history")
    user_message = Message(role=Role.USER, content="Hello!")
    
    var_def = VariableDef(key="history", desc="Chat history", type=VariableType.PLACEHOLDER)
    
    prompt_template = MagicMock()
    prompt_template.template_type = TemplateType.NORMAL
    prompt_template.messages = [system_message, placeholder_message, user_message]
    prompt_template.variable_defs = [var_def]
    
    prompt = MagicMock(spec=Prompt)
    prompt.prompt_template = prompt_template
    
    # Create history messages
    history_message1 = Message(role=Role.USER, content="What is the weather?")
    history_message2 = Message(role=Role.ASSISTANT, content="The weather is sunny.")
    
    variables = {"history": [history_message1, history_message2]}
    
    # Call method
    result = prompt_provider.prompt_format(prompt, variables)
    
    # Verify result
    assert len(result) == 4
    assert result[0].role == Role.SYSTEM
    assert result[0].content == "You are a helpful assistant."
    assert result[1].role == Role.USER
    assert result[1].content == "What is the weather?"
    assert result[2].role == Role.ASSISTANT
    assert result[2].content == "The weather is sunny."
    assert result[3].role == Role.USER
    assert result[3].content == "Hello!"


def test_prompt_format_with_single_message_placeholder(prompt_provider):
    # Setup test data
    system_message = Message(role=Role.SYSTEM, content="You are a helpful assistant.")
    placeholder_message = Message(role=Role.PLACEHOLDER, content="current_message")
    
    var_def = VariableDef(key="current_message", desc="Current message", type=VariableType.PLACEHOLDER)
    
    prompt_template = MagicMock()
    prompt_template.template_type = TemplateType.NORMAL
    prompt_template.messages = [system_message, placeholder_message]
    prompt_template.variable_defs = [var_def]
    
    prompt = MagicMock(spec=Prompt)
    prompt.prompt_template = prompt_template
    
    # Create a single message
    user_message = Message(role=Role.USER, content="Hello, assistant!")
    
    variables = {"current_message": user_message}
    
    # Call method
    result = prompt_provider.prompt_format(prompt, variables)
    
    # Verify result
    assert len(result) == 2
    assert result[0].role == Role.SYSTEM
    assert result[0].content == "You are a helpful assistant."
    assert result[1].role == Role.USER
    assert result[1].content == "Hello, assistant!"


def test_prompt_format_with_trace(prompt_provider, mock_trace_provider):
    # Enable tracing
    prompt_provider.prompt_trace = True
    
    # Setup test data
    message = Message(role=Role.USER, content="Hello {{name}}")
    var_def = VariableDef(key="name", desc="User name", type=VariableType.STRING)
    
    prompt_template = MagicMock()
    prompt_template.template_type = TemplateType.NORMAL
    prompt_template.messages = [message]
    prompt_template.variable_defs = [var_def]
    
    prompt = MagicMock(spec=Prompt)
    prompt.prompt_key = "test_prompt"
    prompt.version = "v1"
    prompt.prompt_template = prompt_template
    
    variables = {"name": "Alice"}
    
    # Mock span input/output conversion
    with patch('cozeloop.internal.prompt.prompt._to_span_prompt_input') as mock_to_input, \
         patch('cozeloop.internal.prompt.prompt._to_span_prompt_output') as mock_to_output:
        
        mock_input = MagicMock()
        mock_input.model_dump_json.return_value = '{"input": "data"}'
        mock_to_input.return_value = mock_input
        
        mock_output = MagicMock()
        mock_output.model_dump_json.return_value = '{"output": "data"}'
        mock_to_output.return_value = mock_output
        
        # Call method
        result = prompt_provider.prompt_format(prompt, variables)
        
        # Verify result
        assert len(result) == 1
        assert result[0].role == Role.USER
        assert result[0].content == "Hello Alice"
        
        # Verify span was created
        mock_trace_provider.start_span.assert_called_once_with(
            consts.TRACE_PROMPT_TEMPLATE_SPAN_NAME,
            consts.TRACE_PROMPT_TEMPLATE_SPAN_TYPE
        )
        
        # Verify span input
        mock_to_input.assert_called_once_with(prompt.prompt_template.messages, variables)
        
        # Verify span output
        mock_to_output.assert_called_once()
        assert mock_to_output.call_args[0][0] == result
        
        # Verify span tags
        span = mock_trace_provider.start_span.return_value.__enter__.return_value
        span.set_tags.assert_any_call({
            consts.PROMPT_KEY: "test_prompt",
            consts.PROMPT_VERSION: "v1",
            consts.INPUT: '{"input": "data"}'
        })
        
        span.set_tags.assert_any_call({
            consts.OUTPUT: '{"output": "data"}',
        })


def test_validate_variable_values_type_string(prompt_provider):
    # Test valid string variable
    var_defs = [VariableDef(key="name", desc="User name", type=VariableType.STRING)]
    variables = {"name": "Alice"}
    
    # Should not raise exception
    prompt_provider._validate_variable_values_type(var_defs, variables)


def test_validate_variable_values_type_string_error(prompt_provider):
    # Test invalid string variable (number instead of string)
    var_defs = [VariableDef(key="name", desc="User name", type=VariableType.STRING)]
    variables = {"name": 123}
    
    # Should raise exception
    with pytest.raises(ValueError) as excinfo:
        prompt_provider._validate_variable_values_type(var_defs, variables)
    
    assert "type of variable 'name' should be string" in str(excinfo.value)


def test_validate_variable_values_type_placeholder_message(prompt_provider):
    # Test valid placeholder variable with single message
    var_defs = [VariableDef(key="message", desc="User message", type=VariableType.PLACEHOLDER)]
    variables = {"message": Message(role=Role.USER, content="Hello")}
    
    # Should not raise exception
    prompt_provider._validate_variable_values_type(var_defs, variables)


def test_validate_variable_values_type_placeholder_messages(prompt_provider):
    # Test valid placeholder variable with list of messages
    var_defs = [VariableDef(key="history", desc="Chat history", type=VariableType.PLACEHOLDER)]
    variables = {"history": [
        Message(role=Role.USER, content="Hello"),
        Message(role=Role.ASSISTANT, content="Hi there")
    ]}
    
    # Should not raise exception
    prompt_provider._validate_variable_values_type(var_defs, variables)


def test_validate_variable_values_type_placeholder_error(prompt_provider):
    # Test invalid placeholder variable (string instead of Message)
    var_defs = [VariableDef(key="message", desc="User message", type=VariableType.PLACEHOLDER)]
    variables = {"message": "Hello"}
    
    # Should raise exception
    with pytest.raises(ValueError) as excinfo:
        prompt_provider._validate_variable_values_type(var_defs, variables)
    
    assert "type of variable 'message' should be Message like object" in str(excinfo.value)


def test_render_text_content_normal(prompt_provider):
    # Test normal template rendering
    template_str = "Hello {{name}}!"
    variable_def_map = {"name": VariableDef(key="name", desc="User name", type=VariableType.STRING)}
    variables = {"name": "Alice"}
    
    result = prompt_provider._render_text_content(
        TemplateType.NORMAL,
        template_str,
        variable_def_map,
        variables
    )
    
    assert result == "Hello Alice!"


def test_render_text_content_variable_not_in_defs(prompt_provider):
    # Test rendering when template contains variables not defined in variable_defs
    template_str = "Hello {{name}}! Today is {{day}}."

    # Only define 'name' in variable_def_map, 'day' is not defined
    variable_def_map = {"name": VariableDef(key="name", desc="User name", type=VariableType.STRING)}

    # Provide both variables in the variables map
    variables = {"name": "Alice", "day": "Monday"}

    result = prompt_provider._render_text_content(
        TemplateType.NORMAL,
        template_str,
        variable_def_map,
        variables
    )

    # Should render 'name' but keep 'day' as is since it's not in variable_def_map
    assert result == "Hello Alice! Today is {{day}}."


def test_render_text_content_defined_but_no_value(prompt_provider):
    # Test rendering when variable is defined in variable_defs but no value is provided
    template_str = "Hello {{name}}! How are you?"

    # Define 'name' in variable_def_map
    variable_def_map = {"name": VariableDef(key="name", desc="User name", type=VariableType.STRING)}

    # Don't provide any value for 'name' in variables
    variables = {}

    result = prompt_provider._render_text_content(
        TemplateType.NORMAL,
        template_str,
        variable_def_map,
        variables
    )

    # Should replace defined but missing variable with empty string
    assert result == "Hello ! How are you?"


def test_render_text_content_undefined_var(prompt_provider):
    # Test rendering with undefined variable
    template_str = "Hello {{unknown}}!"
    variable_def_map = {"name": VariableDef(key="name", desc="User name", type=VariableType.STRING)}
    variables = {"name": "Alice"}
    
    result = prompt_provider._render_text_content(
        TemplateType.NORMAL,
        template_str,
        variable_def_map,
        variables
    )
    
    # Should replace undefined variable with empty string
    assert result == "Hello {{unknown}}!"


def test_render_text_content_unsupported_type(prompt_provider):
    # Test unsupported template type
    template_str = "Hello {{name}}!"
    variable_def_map = {"name": VariableDef(key="name", desc="User name", type=VariableType.STRING)}
    variables = {"name": "Alice"}
    
    # Mock an unsupported template type
    unsupported_type = MagicMock()
    
    with pytest.raises(ValueError) as excinfo:
        prompt_provider._render_text_content(
            unsupported_type,
            template_str,
            variable_def_map,
            variables
        )
    
    assert "text render unsupported template type" in str(excinfo.value)


def test_custom_undefined():
    # Test CustomUndefined class
    undefined = CustomUndefined(name="test_var")
    assert str(undefined) == "{{test_var}}"
    
    # Test with hint
    undefined_hint = CustomUndefined(hint="Variable does not exist", name="test_var")
    assert str(undefined_hint) == "{{undefined value printed: Variable does not exist}}"


def test_prompt_format_empty_template(prompt_provider):
    # Test with empty template
    prompt_template = MagicMock()
    prompt_template.messages = []
    
    prompt = MagicMock(spec=Prompt)
    prompt.prompt_template = prompt_template
    
    variables = {}
    
    result = prompt_provider.prompt_format(prompt, variables)
    assert result == []


def test_prompt_format_none_template(prompt_provider):
    # Test with None template
    prompt = MagicMock(spec=Prompt)
    prompt.prompt_template = None
    
    variables = {}
    
    result = prompt_provider.prompt_format(prompt, variables)
    assert result == []


def test_format_normal_messages_null_message(prompt_provider):
    # Test with a None message in the list
    messages = [
        Message(role=Role.SYSTEM, content="Hello"),
        None,
        Message(role=Role.USER, content="World")
    ]
    
    template_type = TemplateType.NORMAL
    variable_defs = []
    variables = {}
    
    result = prompt_provider._format_normal_messages(template_type, messages, variable_defs, variables)
    
    # Should skip None message
    assert len(result) == 2
    assert result[0].role == Role.SYSTEM
    assert result[0].content == "Hello"
    assert result[1].role == Role.USER
    assert result[1].content == "World"
def test_validate_variable_values_type_boolean_valid(prompt_provider):
    """测试有效的 boolean 类型变量"""
    var_defs = [VariableDef(key="enabled", desc="Enable feature", type=VariableType.BOOLEAN)]
    variables = {"enabled": True}
    
    # 应该不抛出异常
    prompt_provider._validate_variable_values_type(var_defs, variables)


def test_validate_variable_values_type_boolean_invalid(prompt_provider):
    """测试无效的 boolean 类型变量"""
    var_defs = [VariableDef(key="enabled", desc="Enable feature", type=VariableType.BOOLEAN)]
    variables = {"enabled": "true"}  # 字符串而不是布尔值
    
    with pytest.raises(ValueError) as excinfo:
        prompt_provider._validate_variable_values_type(var_defs, variables)
    
    assert "type of variable 'enabled' should be bool" in str(excinfo.value)


def test_validate_variable_values_type_integer_valid(prompt_provider):
    """测试有效的 integer 类型变量"""
    var_defs = [VariableDef(key="count", desc="Item count", type=VariableType.INTEGER)]
    variables = {"count": 42}
    
    # 应该不抛出异常
    prompt_provider._validate_variable_values_type(var_defs, variables)


def test_validate_variable_values_type_integer_invalid(prompt_provider):
    """测试无效的 integer 类型变量"""
    var_defs = [VariableDef(key="count", desc="Item count", type=VariableType.INTEGER)]
    variables = {"count": "42"}  # 字符串而不是整数
    
    with pytest.raises(ValueError) as excinfo:
        prompt_provider._validate_variable_values_type(var_defs, variables)
    
    assert "type of variable 'count' should be int" in str(excinfo.value)


def test_validate_variable_values_type_float_valid(prompt_provider):
    """测试有效的 float 类型变量"""
    var_defs = [VariableDef(key="temperature", desc="Temperature value", type=VariableType.FLOAT)]
    variables = {"temperature": 3.14}
    
    # 应该不抛出异常
    prompt_provider._validate_variable_values_type(var_defs, variables)


def test_validate_variable_values_type_float_invalid(prompt_provider):
    """测试无效的 float 类型变量"""
    var_defs = [VariableDef(key="temperature", desc="Temperature value", type=VariableType.FLOAT)]
    variables = {"temperature": "3.14"}  # 字符串而不是浮点数
    
    with pytest.raises(ValueError) as excinfo:
        prompt_provider._validate_variable_values_type(var_defs, variables)
    
    assert "type of variable 'temperature' should be float" in str(excinfo.value)


def test_validate_variable_values_type_array_string_valid(prompt_provider):
    """测试有效的 array<string> 类型变量"""
    var_defs = [VariableDef(key="tags", desc="Tag list", type=VariableType.ARRAY_STRING)]
    variables = {"tags": ["tag1", "tag2", "tag3"]}
    
    # 应该不抛出异常
    prompt_provider._validate_variable_values_type(var_defs, variables)


def test_validate_variable_values_type_array_string_invalid_not_list(prompt_provider):
    """测试无效的 array<string> 类型变量 - 不是列表"""
    var_defs = [VariableDef(key="tags", desc="Tag list", type=VariableType.ARRAY_STRING)]
    variables = {"tags": "tag1,tag2,tag3"}  # 字符串而不是列表
    
    with pytest.raises(ValueError) as excinfo:
        prompt_provider._validate_variable_values_type(var_defs, variables)
    
    assert "type of variable 'tags' should be array<string>" in str(excinfo.value)


def test_validate_variable_values_type_array_string_invalid_wrong_element_type(prompt_provider):
    """测试无效的 array<string> 类型变量 - 元素类型错误"""
    var_defs = [VariableDef(key="tags", desc="Tag list", type=VariableType.ARRAY_STRING)]
    variables = {"tags": ["tag1", 123, "tag3"]}  # 包含非字符串元素
    
    with pytest.raises(ValueError) as excinfo:
        prompt_provider._validate_variable_values_type(var_defs, variables)
    
    assert "type of variable 'tags' should be array<string>" in str(excinfo.value)


def test_validate_variable_values_type_array_boolean_valid(prompt_provider):
    """测试有效的 array<boolean> 类型变量"""
    var_defs = [VariableDef(key="flags", desc="Boolean flags", type=VariableType.ARRAY_BOOLEAN)]
    variables = {"flags": [True, False, True]}
    
    # 应该不抛出异常
    prompt_provider._validate_variable_values_type(var_defs, variables)


def test_validate_variable_values_type_array_boolean_invalid(prompt_provider):
    """测试无效的 array<boolean> 类型变量"""
    var_defs = [VariableDef(key="flags", desc="Boolean flags", type=VariableType.ARRAY_BOOLEAN)]
    variables = {"flags": [True, "false", True]}  # 包含字符串而不是布尔值
    
    with pytest.raises(ValueError) as excinfo:
        prompt_provider._validate_variable_values_type(var_defs, variables)
    
    assert "type of variable 'flags' should be array<boolean>" in str(excinfo.value)


def test_validate_variable_values_type_array_integer_valid(prompt_provider):
    """测试有效的 array<integer> 类型变量"""
    var_defs = [VariableDef(key="numbers", desc="Number list", type=VariableType.ARRAY_INTEGER)]
    variables = {"numbers": [1, 2, 3, 4, 5]}
    
    # 应该不抛出异常
    prompt_provider._validate_variable_values_type(var_defs, variables)


def test_validate_variable_values_type_array_integer_invalid(prompt_provider):
    """测试无效的 array<integer> 类型变量"""
    var_defs = [VariableDef(key="numbers", desc="Number list", type=VariableType.ARRAY_INTEGER)]
    variables = {"numbers": [1, "2", 3]}  # 包含字符串而不是整数
    
    with pytest.raises(ValueError) as excinfo:
        prompt_provider._validate_variable_values_type(var_defs, variables)
    
    assert "type of variable 'numbers' should be array<integer>" in str(excinfo.value)


def test_validate_variable_values_type_array_float_valid(prompt_provider):
    """测试有效的 array<float> 类型变量"""
    var_defs = [VariableDef(key="scores", desc="Score list", type=VariableType.ARRAY_FLOAT)]
    variables = {"scores": [1.5, 2.7, 3.14]}
    
    # 应该不抛出异常
    prompt_provider._validate_variable_values_type(var_defs, variables)


def test_validate_variable_values_type_array_float_invalid(prompt_provider):
    """测试无效的 array<float> 类型变量"""
    var_defs = [VariableDef(key="scores", desc="Score list", type=VariableType.ARRAY_FLOAT)]
    variables = {"scores": [1.5, "2.7", 3.14]}  # 包含字符串而不是浮点数
    
    with pytest.raises(ValueError) as excinfo:
        prompt_provider._validate_variable_values_type(var_defs, variables)
    
    assert "type of variable 'scores' should be array<float>" in str(excinfo.value)


def test_validate_variable_values_type_mixed_valid(prompt_provider):
    """测试多种类型变量的混合验证"""
    var_defs = [
        VariableDef(key="name", desc="User name", type=VariableType.STRING),
        VariableDef(key="enabled", desc="Enable feature", type=VariableType.BOOLEAN),
        VariableDef(key="count", desc="Item count", type=VariableType.INTEGER),
        VariableDef(key="temperature", desc="Temperature", type=VariableType.FLOAT),
        VariableDef(key="tags", desc="Tag list", type=VariableType.ARRAY_STRING),
    ]
    variables = {
        "name": "Alice",
        "enabled": True,
        "count": 42,
        "temperature": 3.14,
        "tags": ["tag1", "tag2"]
    }
    
    # 应该不抛出异常
    prompt_provider._validate_variable_values_type(var_defs, variables)


# =============================================================================
# Jinja2模板渲染测试
# =============================================================================

def test_render_jinja2_template_basic(prompt_provider):
    """测试基本的 Jinja2 模板渲染"""
    template_str = "Hello {{ name }}!"
    variable_def_map = {"name": VariableDef(key="name", desc="User name", type=VariableType.STRING)}
    variables = {"name": "Alice"}
    
    result = prompt_provider._render_jinja2_template(template_str, variable_def_map, variables)
    assert result == "Hello Alice!"


def test_render_jinja2_template_variable_substitution(prompt_provider):
    """测试 Jinja2 模板变量替换"""
    template_str = "Welcome {{ name }}, you have {{ count }} messages."
    variable_def_map = {
        "name": VariableDef(key="name", desc="User name", type=VariableType.STRING),
        "count": VariableDef(key="count", desc="Message count", type=VariableType.INTEGER)
    }
    variables = {"name": "Bob", "count": 5}
    
    result = prompt_provider._render_jinja2_template(template_str, variable_def_map, variables)
    assert result == "Welcome Bob, you have 5 messages."


def test_render_jinja2_template_with_loops(prompt_provider):
    """测试 Jinja2 模板循环语句"""
    template_str = "Items: {% for item in items %}{{ item }}{% if not loop.last %}, {% endif %}{% endfor %}"
    variable_def_map = {"items": VariableDef(key="items", desc="Item list", type=VariableType.ARRAY_STRING)}
    variables = {"items": ["apple", "banana", "orange"]}
    
    result = prompt_provider._render_jinja2_template(template_str, variable_def_map, variables)
    assert result == "Items: apple, banana, orange"


def test_render_jinja2_template_with_conditionals(prompt_provider):
    """测试 Jinja2 模板条件语句"""
    template_str = "{% if enabled %}Feature is enabled{% else %}Feature is disabled{% endif %}"
    variable_def_map = {"enabled": VariableDef(key="enabled", desc="Feature enabled", type=VariableType.BOOLEAN)}
    variables = {"enabled": True}
    
    result = prompt_provider._render_jinja2_template(template_str, variable_def_map, variables)
    assert result == "Feature is enabled"


def test_render_jinja2_template_with_conditionals_false(prompt_provider):
    """测试 Jinja2 模板条件语句 - false 分支"""
    template_str = "{% if enabled %}Feature is enabled{% else %}Feature is disabled{% endif %}"
    variable_def_map = {"enabled": VariableDef(key="enabled", desc="Feature enabled", type=VariableType.BOOLEAN)}
    variables = {"enabled": False}
    
    result = prompt_provider._render_jinja2_template(template_str, variable_def_map, variables)
    assert result == "Feature is disabled"


def test_render_jinja2_template_undefined_variable(prompt_provider):
    """测试 Jinja2 模板未定义变量处理"""
    template_str = "Hello {{ name }}!"
    variable_def_map = {"name": VariableDef(key="name", desc="User name", type=VariableType.STRING)}
    variables = {}  # 没有提供 name 变量
    
    result = prompt_provider._render_jinja2_template(template_str, variable_def_map, variables)
    assert result == "Hello !"  # 未定义变量被替换为空字符串


def test_render_jinja2_template_complex(prompt_provider):
    """测试复杂的 Jinja2 模板"""
    template_str = """
{%- if user -%}
Hello {{ user }}!
{%- if items -%}
Your items:
{%- for item in items %}
- {{ item }}
{%- endfor -%}
{%- else -%}
You have no items.
{%- endif -%}
{%- else -%}
Hello stranger!
{%- endif -%}
""".strip()
    
    variable_def_map = {
        "user": VariableDef(key="user", desc="User name", type=VariableType.STRING),
        "items": VariableDef(key="items", desc="Item list", type=VariableType.ARRAY_STRING)
    }
    variables = {"user": "Alice", "items": ["book", "pen"]}
    
    result = prompt_provider._render_jinja2_template(template_str, variable_def_map, variables)
    expected = "Hello Alice!Your items:\n- book\n- pen"
    assert result == expected


def test_render_jinja2_template_sandbox_security(prompt_provider):
    """测试 Jinja2 模板沙箱环境安全性"""
    # 尝试访问不安全的内置函数
    template_str = "{{ ''.__class__.__mro__[1].__subclasses__() }}"
    variable_def_map = {}
    variables = {}
    
    # 沙箱环境应该阻止这种访问
    with pytest.raises(Exception):  # SandboxedEnvironment 会抛出异常
        prompt_provider._render_jinja2_template(template_str, variable_def_map, variables)


def test_render_text_content_jinja2(prompt_provider):
    """测试通过 _render_text_content 方法使用 Jinja2 模板"""
    template_str = "Hello {{ name }}! You have {{ count }} items."
    variable_def_map = {
        "name": VariableDef(key="name", desc="User name", type=VariableType.STRING),
        "count": VariableDef(key="count", desc="Item count", type=VariableType.INTEGER)
    }
    variables = {"name": "Charlie", "count": 3}
    
    result = prompt_provider._render_text_content(
        TemplateType.JINJA2,
        template_str,
        variable_def_map,
        variables
    )
    
    assert result == "Hello Charlie! You have 3 items."


# =============================================================================
# 集成测试
# =============================================================================

def test_prompt_format_jinja2_integration(prompt_provider):
    """测试使用 Jinja2 模板的完整 prompt 格式化"""
    # 创建 Jinja2 模板消息
    system_message = Message(role=Role.SYSTEM, content="You are a helpful assistant for {{ domain }}.")
    user_message = Message(role=Role.USER, content="{% if urgent %}URGENT: {% endif %}{{ question }}")
    
    var_defs = [
        VariableDef(key="domain", desc="Domain", type=VariableType.STRING),
        VariableDef(key="urgent", desc="Is urgent", type=VariableType.BOOLEAN),
        VariableDef(key="question", desc="User question", type=VariableType.STRING)
    ]
    
    prompt_template = MagicMock()
    prompt_template.template_type = TemplateType.JINJA2
    prompt_template.messages = [system_message, user_message]
    prompt_template.variable_defs = var_defs
    
    prompt = MagicMock(spec=Prompt)
    prompt.prompt_template = prompt_template
    
    variables = {
        "domain": "programming",
        "urgent": True,
        "question": "How to fix this bug?"
    }
    
    # 调用方法
    result = prompt_provider.prompt_format(prompt, variables)
    
    # 验证结果
    assert len(result) == 2
    assert result[0].role == Role.SYSTEM
    assert result[0].content == "You are a helpful assistant for programming."
    assert result[1].role == Role.USER
    assert result[1].content == "URGENT: How to fix this bug?"


def test_prompt_format_jinja2_with_arrays(prompt_provider):
    """测试使用数组变量的 Jinja2 模板格式化"""
    message = Message(
        role=Role.USER,
        content="Please process these items: {% for item in items %}{{ item }}{% if not loop.last %}, {% endif %}{% endfor %}"
    )
    
    var_defs = [
        VariableDef(key="items", desc="Item list", type=VariableType.ARRAY_STRING)
    ]
    
    prompt_template = MagicMock()
    prompt_template.template_type = TemplateType.JINJA2
    prompt_template.messages = [message]
    prompt_template.variable_defs = var_defs
    
    prompt = MagicMock(spec=Prompt)
    prompt.prompt_template = prompt_template
    
    variables = {"items": ["task1", "task2", "task3"]}
    
    # 调用方法
    result = prompt_provider.prompt_format(prompt, variables)
    
    # 验证结果
    assert len(result) == 1
    assert result[0].role == Role.USER
    assert result[0].content == "Please process these items: task1, task2, task3"


def test_prompt_format_mixed_template_types(prompt_provider):
    """测试混合使用 NORMAL 和 JINJA2 模板的场景（通过不同的 prompt）"""
    # 测试 NORMAL 模板
    normal_message = Message(role=Role.USER, content="Hello {{name}}!")
    normal_var_defs = [VariableDef(key="name", desc="User name", type=VariableType.STRING)]
    
    normal_template = MagicMock()
    normal_template.template_type = TemplateType.NORMAL
    normal_template.messages = [normal_message]
    normal_template.variable_defs = normal_var_defs
    
    normal_prompt = MagicMock(spec=Prompt)
    normal_prompt.prompt_template = normal_template
    
    normal_variables = {"name": "Alice"}
    normal_result = prompt_provider.prompt_format(normal_prompt, normal_variables)
    
    # 测试 JINJA2 模板
    jinja2_message = Message(role=Role.USER, content="Hello {{ name }}!")
    jinja2_var_defs = [VariableDef(key="name", desc="User name", type=VariableType.STRING)]
    
    jinja2_template = MagicMock()
    jinja2_template.template_type = TemplateType.JINJA2
    jinja2_template.messages = [jinja2_message]
    jinja2_template.variable_defs = jinja2_var_defs
    
    jinja2_prompt = MagicMock(spec=Prompt)
    jinja2_prompt.prompt_template = jinja2_template
    
    jinja2_variables = {"name": "Bob"}
    jinja2_result = prompt_provider.prompt_format(jinja2_prompt, jinja2_variables)
    
    # 验证两种模板都能正常工作
    assert len(normal_result) == 1
    assert normal_result[0].content == "Hello Alice!"
    
    assert len(jinja2_result) == 1
    assert jinja2_result[0].content == "Hello Bob!"


def test_prompt_format_jinja2_with_placeholder(prompt_provider):
    """测试 Jinja2 模板与 placeholder 消息的组合"""
    system_message = Message(role=Role.SYSTEM, content="You are helping with {{ task_type }}.")
    placeholder_message = Message(role=Role.PLACEHOLDER, content="history")
    user_message = Message(role=Role.USER, content="{% if urgent %}URGENT: {% endif %}{{ question }}")
    
    var_defs = [
        VariableDef(key="task_type", desc="Task type", type=VariableType.STRING),
        VariableDef(key="urgent", desc="Is urgent", type=VariableType.BOOLEAN),
        VariableDef(key="question", desc="User question", type=VariableType.STRING),
        VariableDef(key="history", desc="Chat history", type=VariableType.PLACEHOLDER)
    ]
    
    prompt_template = MagicMock()
    prompt_template.template_type = TemplateType.JINJA2
    prompt_template.messages = [system_message, placeholder_message, user_message]
    prompt_template.variable_defs = var_defs
    
    prompt = MagicMock(spec=Prompt)
    prompt.prompt_template = prompt_template
    
    # 创建历史消息
    history_messages = [
        Message(role=Role.USER, content="Previous question"),
        Message(role=Role.ASSISTANT, content="Previous answer")
    ]
    
    variables = {
        "task_type": "debugging",
        "urgent": False,
        "question": "What's the issue?",
        "history": history_messages
    }
    
    # 调用方法
    result = prompt_provider.prompt_format(prompt, variables)
    
    # 验证结果
    assert len(result) == 4
    assert result[0].role == Role.SYSTEM
    assert result[0].content == "You are helping with debugging."
    assert result[1].role == Role.USER
    assert result[1].content == "Previous question"
    assert result[2].role == Role.ASSISTANT
    assert result[2].content == "Previous answer"
    assert result[3].role == Role.USER
    assert result[3].content == "What's the issue?"


def test_prompt_format_jinja2_edge_cases(prompt_provider):
    """测试 Jinja2 模板的边界情况"""
    # 空模板
    empty_message = Message(role=Role.USER, content="")
    
    # 只有空格的模板
    whitespace_message = Message(role=Role.USER, content="   ")
    
    # 没有变量的模板
    no_vars_message = Message(role=Role.USER, content="Static text")
    
    var_defs = []
    
    prompt_template = MagicMock()
    prompt_template.template_type = TemplateType.JINJA2
    prompt_template.messages = [empty_message, whitespace_message, no_vars_message]
    prompt_template.variable_defs = var_defs
    
    prompt = MagicMock(spec=Prompt)
    prompt.prompt_template = prompt_template
    
    variables = {}
    
    # 调用方法
    result = prompt_provider.prompt_format(prompt, variables)
    
    # 验证结果
    assert len(result) == 3
    assert result[0].content == ""
    assert result[1].content == "   "
    assert result[2].content == "Static text"