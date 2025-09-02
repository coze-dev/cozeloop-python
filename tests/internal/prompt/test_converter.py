# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock

from cozeloop.entities.prompt import (
    Message as EntityMessage,
    ContentType as EntityContentType
)
from cozeloop.entities.prompt import (
    Role as EntityRole,
    VariableType as EntityVariableType,
    ToolType as EntityToolType,
    TemplateType as EntityTemplateType,
    ToolChoiceType as EntityToolChoiceType
)
from cozeloop.internal.prompt.converter import (
    _convert_role,
    _convert_message,
    _convert_variable_type,
    _convert_variable_def,
    _convert_function,
    _convert_tool_type,
    _convert_tool,
    _convert_tool_choice_type,
    _convert_tool_call_config,
    _convert_llm_config,
    _convert_template_type,
    _convert_prompt_template,
    _convert_prompt,
    _to_span_prompt_input,
    _to_span_prompt_output,
    _to_span_messages,
    _to_span_arguments,
    _convert_content_type,
    to_content_part
)
from cozeloop.internal.prompt.openapi import (
    Prompt as OpenAPIPrompt,
    Message as OpenAPIMessage,
    PromptTemplate as OpenAPIPromptTemplate,
    Tool as OpenAPITool,
    ToolCallConfig as OpenAPIToolCallConfig,
    LLMConfig as OpenAPIModelConfig,
    Function as OpenAPIFunction,
    VariableDef as OpenAPIVariableDef,
    VariableType as OpenAPIVariableType,
    ToolType as OpenAPIToolType,
    Role as OpenAPIRole,
    ToolChoiceType as OpenAPIChoiceType,
    TemplateType as OpenAPITemplateType,
    ContentType as OpenAPIContentType,
    ContentPart as OpenAPIContentPart
)


def test_convert_role():
    # Test conversion of each role type
    assert _convert_role(OpenAPIRole.SYSTEM) == EntityRole.SYSTEM
    assert _convert_role(OpenAPIRole.USER) == EntityRole.USER
    assert _convert_role(OpenAPIRole.ASSISTANT) == EntityRole.ASSISTANT
    assert _convert_role(OpenAPIRole.TOOL) == EntityRole.TOOL
    assert _convert_role(OpenAPIRole.PLACEHOLDER) == EntityRole.PLACEHOLDER
    
    # Test default case with invalid role
    mock_invalid_role = MagicMock()
    assert _convert_role(mock_invalid_role) == EntityRole.USER


def test_convert_message():
    # Create a mock OpenAPI message
    openapi_message = OpenAPIMessage(
        role=OpenAPIRole.USER,
        content="Hello, world!"
    )
    
    # Convert message and verify
    entity_message = _convert_message(openapi_message)
    assert entity_message.role == EntityRole.USER
    assert entity_message.content == "Hello, world!"


def test_convert_variable_type():
    # Test conversion of each variable type
    assert _convert_variable_type(OpenAPIVariableType.STRING) == EntityVariableType.STRING
    assert _convert_variable_type(OpenAPIVariableType.PLACEHOLDER) == EntityVariableType.PLACEHOLDER
    
    # Test default case with invalid type
    mock_invalid_type = MagicMock()
    assert _convert_variable_type(mock_invalid_type) == EntityVariableType.STRING


def test_convert_variable_def():
    # Create a mock OpenAPI variable definition
    openapi_var_def = OpenAPIVariableDef(
        key="test_var",
        desc="Test variable",
        type=OpenAPIVariableType.STRING
    )
    
    # Convert variable definition and verify
    entity_var_def = _convert_variable_def(openapi_var_def)
    assert entity_var_def.key == "test_var"
    assert entity_var_def.desc == "Test variable"
    assert entity_var_def.type == EntityVariableType.STRING


def test_convert_function():
    # Create a mock OpenAPI function
    openapi_function = OpenAPIFunction(
        name="test_function",
        description="Test function description",
        parameters='{"type": "object", "properties": {}}'
    )
    
    # Convert function and verify
    entity_function = _convert_function(openapi_function)
    assert entity_function.name == "test_function"
    assert entity_function.description == "Test function description"
    assert entity_function.parameters == '{"type": "object", "properties": {}}'


def test_convert_tool_type():
    # Test conversion of each tool type
    assert _convert_tool_type(OpenAPIToolType.FUNCTION) == EntityToolType.FUNCTION
    
    # Test default case with invalid type
    mock_invalid_type = MagicMock()
    assert _convert_tool_type(mock_invalid_type) == EntityToolType.FUNCTION


def test_convert_tool():
    # Create a mock OpenAPI function for the tool
    openapi_function = OpenAPIFunction(
        name="test_function",
        description="Test function description",
        parameters='{"type": "object", "properties": {}}'
    )
    
    # Create a mock OpenAPI tool with the function
    openapi_tool = OpenAPITool(
        type=OpenAPIToolType.FUNCTION,
        function=openapi_function
    )
    
    # Convert tool and verify
    entity_tool = _convert_tool(openapi_tool)
    assert entity_tool.type == EntityToolType.FUNCTION
    assert entity_tool.function is not None
    assert entity_tool.function.name == "test_function"
    
    # Test with empty function
    openapi_tool_no_function = OpenAPITool(
        type=OpenAPIToolType.FUNCTION,
        function=None
    )
    entity_tool_no_function = _convert_tool(openapi_tool_no_function)
    assert entity_tool_no_function.function is None


def test_convert_tool_choice_type():
    # Test conversion of each tool choice type
    assert _convert_tool_choice_type(OpenAPIChoiceType.AUTO) == EntityToolChoiceType.AUTO
    assert _convert_tool_choice_type(OpenAPIChoiceType.NONE) == EntityToolChoiceType.NONE
    
    # Test default case with invalid type
    mock_invalid_type = MagicMock()
    assert _convert_tool_choice_type(mock_invalid_type) == EntityToolChoiceType.AUTO


def test_convert_tool_call_config():
    # Create a mock OpenAPI tool call config
    openapi_config = OpenAPIToolCallConfig(
        tool_choice=OpenAPIChoiceType.AUTO
    )
    
    # Convert tool call config and verify
    entity_config = _convert_tool_call_config(openapi_config)
    assert entity_config.tool_choice == EntityToolChoiceType.AUTO


def test_convert_llm_config():
    # Create a mock OpenAPI LLM config
    openapi_config = OpenAPIModelConfig(
        temperature=0.7,
        max_tokens=2048,
        top_k=50,
        top_p=0.95,
        frequency_penalty=0.1,
        presence_penalty=0.2,
        json_mode=True
    )
    
    # Convert LLM config and verify
    entity_config = _convert_llm_config(openapi_config)
    assert entity_config.temperature == 0.7
    assert entity_config.max_tokens == 2048
    assert entity_config.top_k == 50
    assert entity_config.top_p == 0.95
    assert entity_config.frequency_penalty == 0.1
    assert entity_config.presence_penalty == 0.2
    assert entity_config.json_mode is True


def test_convert_template_type():
    # Test conversion of template type
    assert _convert_template_type(OpenAPITemplateType.NORMAL) == EntityTemplateType.NORMAL
    
    # Test default case with invalid type
    mock_invalid_type = MagicMock()
    assert _convert_template_type(mock_invalid_type) == EntityTemplateType.NORMAL


def test_convert_prompt_template():
    # Create mock OpenAPI messages
    openapi_message1 = OpenAPIMessage(role=OpenAPIRole.SYSTEM, content="You are a helpful assistant.")
    openapi_message2 = OpenAPIMessage(role=OpenAPIRole.USER, content="Hello!")
    
    # Create mock OpenAPI variable definitions
    openapi_var_def = OpenAPIVariableDef(
        key="user_name",
        desc="User's name",
        type=OpenAPIVariableType.STRING
    )
    
    # Create a mock OpenAPI prompt template
    openapi_template = OpenAPIPromptTemplate(
        template_type=OpenAPITemplateType.NORMAL,
        messages=[openapi_message1, openapi_message2],
        variable_defs=[openapi_var_def]
    )
    
    # Convert prompt template and verify
    entity_template = _convert_prompt_template(openapi_template)
    assert entity_template.template_type == EntityTemplateType.NORMAL
    assert len(entity_template.messages) == 2
    assert entity_template.messages[0].role == EntityRole.SYSTEM
    assert entity_template.messages[0].content == "You are a helpful assistant."
    assert entity_template.messages[1].role == EntityRole.USER
    assert entity_template.messages[1].content == "Hello!"
    assert len(entity_template.variable_defs) == 1
    assert entity_template.variable_defs[0].key == "user_name"
    
    # Test with empty messages and variable_defs
    openapi_template_empty = OpenAPIPromptTemplate(
        template_type=OpenAPITemplateType.NORMAL,
        messages=None,
        variable_defs=None
    )
    entity_template_empty = _convert_prompt_template(openapi_template_empty)
    assert entity_template_empty.messages is None
    assert entity_template_empty.variable_defs is None


def test_convert_prompt():
    # Create a simple OpenAPI prompt for testing
    openapi_message = OpenAPIMessage(role=OpenAPIRole.USER, content="Hello!")
    openapi_template = OpenAPIPromptTemplate(
        template_type=OpenAPITemplateType.NORMAL,
        messages=[openapi_message],
        variable_defs=[]
    )
    
    openapi_function = OpenAPIFunction(
        name="test_function",
        description="Test function",
        parameters='{}'
    )
    
    openapi_tool = OpenAPITool(
        type=OpenAPIToolType.FUNCTION,
        function=openapi_function
    )
    
    openapi_tool_call_config = OpenAPIToolCallConfig(
        tool_choice=OpenAPIChoiceType.AUTO
    )
    
    openapi_llm_config = OpenAPIModelConfig(
        temperature=0.7,
        max_tokens=1024,
        top_k=None,
        top_p=None,
        frequency_penalty=None,
        presence_penalty=None,
        json_mode=False
    )
    
    openapi_prompt = OpenAPIPrompt(
        workspace_id="test_workspace",
        prompt_key="test_prompt",
        version="v1",
        prompt_template=openapi_template,
        tools=[openapi_tool],
        tool_call_config=openapi_tool_call_config,
        llm_config=openapi_llm_config
    )
    
    # Convert prompt and verify
    entity_prompt = _convert_prompt(openapi_prompt)
    
    assert entity_prompt.workspace_id == "test_workspace"
    assert entity_prompt.prompt_key == "test_prompt"
    assert entity_prompt.version == "v1"
    assert entity_prompt.prompt_template is not None
    assert entity_prompt.prompt_template.messages[0].content == "Hello!"
    assert len(entity_prompt.tools) == 1
    assert entity_prompt.tools[0].type == EntityToolType.FUNCTION
    assert entity_prompt.tool_call_config is not None
    assert entity_prompt.llm_config is not None
    assert entity_prompt.llm_config.temperature == 0.7
    
    # Test with empty fields
    openapi_prompt_empty = OpenAPIPrompt(
        workspace_id="test_workspace",
        prompt_key="test_prompt",
        version="v1",
        prompt_template=None,
        tools=None,
        tool_call_config=None,
        llm_config=None
    )
    
    entity_prompt_empty = _convert_prompt(openapi_prompt_empty)
    assert entity_prompt_empty.prompt_template is None
    assert entity_prompt_empty.tools is None
    assert entity_prompt_empty.tool_call_config is None
    assert entity_prompt_empty.llm_config is None


def test_to_span_messages():
    # Create entity messages for testing
    entity_message1 = EntityMessage(role=EntityRole.SYSTEM, content="System message")
    entity_message2 = EntityMessage(role=EntityRole.USER, content="User message")
    
    # Convert to span messages
    span_messages = _to_span_messages([entity_message1, entity_message2])
    
    # Verify conversion
    assert len(span_messages) == 2
    assert span_messages[0].role == EntityRole.SYSTEM
    assert span_messages[0].content == "System message"
    assert span_messages[1].role == EntityRole.USER
    assert span_messages[1].content == "User message"


def test_to_span_arguments():
    # Create arguments dictionary
    arguments = {
        "name": "John Doe",
        "age": 30
    }
    
    # Convert to span arguments
    span_arguments = _to_span_arguments(arguments)
    
    # Verify conversion
    assert len(span_arguments) == 2
    
    # Sort by key for deterministic comparison
    span_arguments.sort(key=lambda x: x.key)
    
    assert span_arguments[0].key == "age"
    assert span_arguments[0].value == 30
    assert span_arguments[1].key == "name"
    assert span_arguments[1].value == "John Doe"


def test_to_span_prompt_input():
    # Create entity messages for testing
    entity_message1 = EntityMessage(role=EntityRole.SYSTEM, content="System message")
    entity_message2 = EntityMessage(role=EntityRole.USER, content="User message")
    
    # Create variables dictionary
    variables = {
        "name": "John Doe",
        "age": 30
    }
    
    # Convert to span prompt input
    span_input = _to_span_prompt_input([entity_message1, entity_message2], variables)
    
    # Verify conversion
    assert len(span_input.templates) == 2
    assert span_input.templates[0].role == EntityRole.SYSTEM
    assert span_input.templates[0].content == "System message"
    assert span_input.templates[1].role == EntityRole.USER
    assert span_input.templates[1].content == "User message"
    
    assert len(span_input.arguments) == 2
    
    # Sort arguments by key for deterministic comparison
    span_input.arguments.sort(key=lambda x: x.key)
    
    assert span_input.arguments[0].key == "age"
    assert span_input.arguments[0].value == 30
    assert span_input.arguments[1].key == "name"
    assert span_input.arguments[1].value == "John Doe"


def test_to_span_prompt_output():
    # Create entity messages for testing
    entity_message1 = EntityMessage(role=EntityRole.ASSISTANT, content="Assistant response")
    
    # Convert to span prompt output
    span_output = _to_span_prompt_output([entity_message1])
    
    # Verify conversion
    assert len(span_output.prompts) == 1
    assert span_output.prompts[0].role == EntityRole.ASSISTANT
    assert span_output.prompts[0].content == "Assistant response"

def test_convert_content_type():
    # Test conversion of content types
    assert _convert_content_type(OpenAPIContentType.TEXT) == EntityContentType.TEXT
    assert _convert_content_type(OpenAPIContentType.MULTI_PART_VARIABLE) == EntityContentType.MULTI_PART_VARIABLE

    # Test default case with invalid type
    mock_invalid_type = MagicMock()
    assert _convert_content_type(mock_invalid_type) == EntityContentType.TEXT

def test_to_content_part():
    # Test text content part conversion
    openapi_text_part = OpenAPIContentPart(
        type=OpenAPIContentType.TEXT,
        text="Hello world"
    )

    entity_part = to_content_part(openapi_text_part)
    assert entity_part.type == EntityContentType.TEXT
    assert entity_part.text == "Hello world"
    assert entity_part.image_url is None

    # Test multi-part variable content part conversion
    openapi_multipart_part = OpenAPIContentPart(
        type=OpenAPIContentType.MULTI_PART_VARIABLE,
        text="image_variable"
    )

    entity_multipart_part = to_content_part(openapi_multipart_part)
    assert entity_multipart_part.type == EntityContentType.MULTI_PART_VARIABLE
    assert entity_multipart_part.text == "image_variable"
    assert entity_multipart_part.image_url is None

def test_convert_message_with_parts():
    # Create OpenAPI content parts
    text_part = OpenAPIContentPart(type=OpenAPIContentType.TEXT, text="Hello")
    multipart_part = OpenAPIContentPart(type=OpenAPIContentType.MULTI_PART_VARIABLE, text="image_var")

    # Create OpenAPI message with parts
    openapi_message = OpenAPIMessage(
        role=OpenAPIRole.USER,
        content="User message",
        parts=[text_part, multipart_part]
    )

    # Convert message
    entity_message = _convert_message(openapi_message)

    # Verify conversion
    assert entity_message.role == EntityRole.USER
    assert entity_message.content == "User message"
    assert entity_message.parts is not None
    assert len(entity_message.parts) == 2

    # Verify first part (text)
    assert entity_message.parts[0].type == EntityContentType.TEXT
    assert entity_message.parts[0].text == "Hello"
    assert entity_message.parts[0].image_url is None

    # Verify second part (multi-part variable)
    assert entity_message.parts[1].type == EntityContentType.MULTI_PART_VARIABLE
    assert entity_message.parts[1].text == "image_var"
    assert entity_message.parts[1].image_url is None

def test_convert_message_without_parts():
    # Create OpenAPI message without parts
    openapi_message = OpenAPIMessage(
        role=OpenAPIRole.ASSISTANT,
        content="Assistant response"
    )

    # Convert message
    entity_message = _convert_message(openapi_message)

    # Verify conversion
    assert entity_message.role == EntityRole.ASSISTANT
    assert entity_message.content == "Assistant response"
    assert entity_message.parts is None

def test_convert_variable_type_multi_part():
    # Test MULTI_PART variable type conversion
    assert _convert_variable_type(OpenAPIVariableType.MULTI_PART) == EntityVariableType.MULTI_PART

    # Test all existing variable types still work
    assert _convert_variable_type(OpenAPIVariableType.STRING) == EntityVariableType.STRING
    assert _convert_variable_type(OpenAPIVariableType.PLACEHOLDER) == EntityVariableType.PLACEHOLDER
    assert _convert_variable_type(OpenAPIVariableType.BOOLEAN) == EntityVariableType.BOOLEAN
    assert _convert_variable_type(OpenAPIVariableType.INTEGER) == EntityVariableType.INTEGER
    assert _convert_variable_type(OpenAPIVariableType.FLOAT) == EntityVariableType.FLOAT
    assert _convert_variable_type(OpenAPIVariableType.OBJECT) == EntityVariableType.OBJECT
    assert _convert_variable_type(OpenAPIVariableType.ARRAY_STRING) == EntityVariableType.ARRAY_STRING
    assert _convert_variable_type(OpenAPIVariableType.ARRAY_BOOLEAN) == EntityVariableType.ARRAY_BOOLEAN
    assert _convert_variable_type(OpenAPIVariableType.ARRAY_INTEGER) == EntityVariableType.ARRAY_INTEGER
    assert _convert_variable_type(OpenAPIVariableType.ARRAY_FLOAT) == EntityVariableType.ARRAY_FLOAT
    assert _convert_variable_type(OpenAPIVariableType.ARRAY_OBJECT) == EntityVariableType.ARRAY_OBJECT