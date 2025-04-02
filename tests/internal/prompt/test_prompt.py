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
