# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import List, Dict, Optional

from cozeloop.spec.tracespec import PromptInput, PromptOutput, ModelMessage, PromptArgument, ModelMessagePart, \
    ModelMessagePartType, ModelImageURL, PromptArgumentValueType
from cozeloop.entities.prompt import (
    Prompt as EntityPrompt,
    Message as EntityMessage,
    PromptTemplate as EntityPromptTemplate,
    Tool as EntityTool,
    ToolCallConfig as EntityToolCallConfig,
    LLMConfig as EntityModelConfig,
    Function as EntityFunction,
    VariableDef as EntityVariableDef,
    TemplateType as EntityTemplateType,
    ToolChoiceType as EntityToolChoiceType,
    Role as EntityRole,
    VariableType as EntityVariableType,
    ToolType as EntityToolType,
    PromptVariable,
    ContentType as EntityContentType,
    ContentPart as EntityContentPart,
    ToolCall as EntityToolCall,
    FunctionCall as EntityFunctionCall,
    TokenUsage as EntityTokenUsage,
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
    ContentPart as OpenAPIContentPart,
    ToolCall as OpenAPIToolCall,
    FunctionCall as OpenAPIFunctionCall,
    TokenUsage as OpenAPITokenUsage,
)


def _convert_role(openapi_role: OpenAPIRole) -> EntityRole:
    """Convert role type"""
    role_mapping = {
        OpenAPIRole.SYSTEM: EntityRole.SYSTEM,
        OpenAPIRole.USER: EntityRole.USER,
        OpenAPIRole.ASSISTANT: EntityRole.ASSISTANT,
        OpenAPIRole.TOOL: EntityRole.TOOL,
        OpenAPIRole.PLACEHOLDER: EntityRole.PLACEHOLDER
    }
    return role_mapping.get(openapi_role, EntityRole.USER)


def _convert_content_type(openapi_type: OpenAPIContentType) -> EntityContentType:
    """Convert content type"""
    content_type_mapping = {
        OpenAPIContentType.TEXT: EntityContentType.TEXT,
        OpenAPIContentType.IMAGE_URL: EntityContentType.IMAGE_URL,
        OpenAPIContentType.BASE64_DATA: EntityContentType.BASE64_DATA,
        OpenAPIContentType.MULTI_PART_VARIABLE: EntityContentType.MULTI_PART_VARIABLE,
    }
    return content_type_mapping.get(openapi_type, EntityContentType.TEXT)


def _convert_content_part(openapi_part: OpenAPIContentPart) -> EntityContentPart:
    """Convert content part, ensure text, image_url, base64_data fields are all converted"""
    return EntityContentPart(
        type=_convert_content_type(openapi_part.type),
        text=openapi_part.text,
        image_url=openapi_part.image_url,
        base64_data=openapi_part.base64_data
    )


def _convert_function_call(func_call: Optional[OpenAPIFunctionCall]) -> Optional[EntityFunctionCall]:
    """Convert function call, ensure name, arguments fields are all converted"""
    if func_call is None:
        return None
    return EntityFunctionCall(
        name=func_call.name,
        arguments=func_call.arguments
    )


def _convert_tool_call(tool_call: OpenAPIToolCall) -> EntityToolCall:
    """Convert tool call, ensure index, id, type, function_call fields are all converted"""
    return EntityToolCall(
        index=tool_call.index,
        id=tool_call.id,
        type=_convert_tool_type(tool_call.type),
        function_call=_convert_function_call(tool_call.function_call)
    )


def _convert_message(msg: OpenAPIMessage) -> EntityMessage:
    """Convert message, ensure role, content, reasoning_content, tool_call_id, tool_calls fields are all converted"""
    return EntityMessage(
        role=_convert_role(msg.role),
        reasoning_content=msg.reasoning_content,
        content=msg.content,
        parts=[_convert_content_part(part) for part in msg.parts] if msg.parts else None,
        tool_call_id=msg.tool_call_id,
        tool_calls=[_convert_tool_call(tool_call) for tool_call in msg.tool_calls] if msg.tool_calls else None
    )


def _convert_variable_type(openapi_type: OpenAPIVariableType) -> EntityVariableType:
    """Convert variable type"""
    type_mapping = {
        OpenAPIVariableType.STRING: EntityVariableType.STRING,
        OpenAPIVariableType.PLACEHOLDER: EntityVariableType.PLACEHOLDER,
        OpenAPIVariableType.BOOLEAN: EntityVariableType.BOOLEAN,
        OpenAPIVariableType.INTEGER: EntityVariableType.INTEGER,
        OpenAPIVariableType.FLOAT: EntityVariableType.FLOAT,
        OpenAPIVariableType.OBJECT: EntityVariableType.OBJECT,
        OpenAPIVariableType.ARRAY_STRING: EntityVariableType.ARRAY_STRING,
        OpenAPIVariableType.ARRAY_INTEGER: EntityVariableType.ARRAY_INTEGER,
        OpenAPIVariableType.ARRAY_FLOAT: EntityVariableType.ARRAY_FLOAT,
        OpenAPIVariableType.ARRAY_BOOLEAN: EntityVariableType.ARRAY_BOOLEAN,
        OpenAPIVariableType.ARRAY_OBJECT: EntityVariableType.ARRAY_OBJECT,
        OpenAPIVariableType.MULTI_PART: EntityVariableType.MULTI_PART,
    }
    return type_mapping.get(openapi_type, EntityVariableType.STRING)


def _convert_variable_def(var_def: OpenAPIVariableDef) -> EntityVariableDef:
    """Convert variable definition"""
    return EntityVariableDef(
        key=var_def.key,
        desc=var_def.desc,
        type=_convert_variable_type(var_def.type)
    )


def _convert_function(func: OpenAPIFunction) -> EntityFunction:
    """Convert function definition"""
    return EntityFunction(
        name=func.name,
        description=func.description,
        parameters=func.parameters
    )


def _convert_tool_type(openapi_tool_type: OpenAPIToolType) -> EntityToolType:
    """Convert tool type"""
    type_mapping = {
        OpenAPIToolType.FUNCTION: EntityToolType.FUNCTION,
    }
    return type_mapping.get(openapi_tool_type, EntityToolType.FUNCTION)


def _convert_tool(tool: OpenAPITool) -> EntityTool:
    """Convert tool definition"""
    return EntityTool(
        type=_convert_tool_type(tool.type),
        function=_convert_function(tool.function) if tool.function else None
    )


def _convert_tool_choice_type(openapi_tool_choice_type: OpenAPIChoiceType) -> EntityToolChoiceType:
    """Convert tool choice type"""
    choice_mapping = {
        OpenAPIChoiceType.AUTO: EntityToolChoiceType.AUTO,
        OpenAPIChoiceType.NONE: EntityToolChoiceType.NONE
    }
    return choice_mapping.get(openapi_tool_choice_type, EntityToolChoiceType.AUTO)


def _convert_tool_call_config(config: OpenAPIToolCallConfig) -> EntityToolCallConfig:
    """Convert tool call configuration"""
    return EntityToolCallConfig(
        tool_choice=_convert_tool_choice_type(config.tool_choice)
    )


def _convert_llm_config(config: OpenAPIModelConfig) -> EntityModelConfig:
    """Convert LLM configuration"""
    return EntityModelConfig(
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        top_k=config.top_k,
        top_p=config.top_p,
        frequency_penalty=config.frequency_penalty,
        presence_penalty=config.presence_penalty,
        json_mode=config.json_mode
    )


def _convert_template_type(openapi_template_type: OpenAPITemplateType) -> EntityTemplateType:
    """Convert template type"""
    template_mapping = {
        OpenAPITemplateType.NORMAL: EntityTemplateType.NORMAL,
        OpenAPITemplateType.JINJA2: EntityTemplateType.JINJA2
    }
    return template_mapping.get(openapi_template_type, EntityTemplateType.NORMAL)


def _convert_prompt_template(template: OpenAPIPromptTemplate) -> EntityPromptTemplate:
    """Convert prompt template"""
    return EntityPromptTemplate(
        template_type=_convert_template_type(template.template_type),
        messages=[_convert_message(msg) for msg in template.messages] if template.messages else None,
        variable_defs=[_convert_variable_def(var_def) for var_def in
                       template.variable_defs] if template.variable_defs else None
    )


def _convert_token_usage(usage: Optional[OpenAPITokenUsage]) -> Optional[EntityTokenUsage]:
    """Convert Token usage statistics, ensure input_tokens, output_tokens fields are all converted"""
    if usage is None:
        return None
    return EntityTokenUsage(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens
    )


def _convert_prompt(prompt: OpenAPIPrompt) -> EntityPrompt:
    """Convert OpenAPI Prompt object to entity Prompt object"""
    return EntityPrompt(
        workspace_id=prompt.workspace_id,
        prompt_key=prompt.prompt_key,
        version=prompt.version,
        prompt_template=_convert_prompt_template(prompt.prompt_template) if prompt.prompt_template else None,
        tools=[_convert_tool(tool) for tool in prompt.tools] if prompt.tools else None,
        tool_call_config=_convert_tool_call_config(prompt.tool_call_config) if prompt.tool_call_config else None,
        llm_config=_convert_llm_config(prompt.llm_config) if prompt.llm_config else None
    )


# Public conversion functions
def to_content_part(openapi_part: OpenAPIContentPart) -> EntityContentPart:
    """Public content part conversion function"""
    return _convert_content_part(openapi_part)


def to_prompt(openapi_prompt: OpenAPIPrompt) -> EntityPrompt:
    """Public prompt conversion function"""
    return _convert_prompt(openapi_prompt)


def to_message(openapi_message: OpenAPIMessage) -> EntityMessage:
    """Public message conversion function"""
    return _convert_message(openapi_message)


def to_token_usage(openapi_usage: Optional[OpenAPITokenUsage]) -> Optional[EntityTokenUsage]:
    """Public Token usage statistics conversion function"""
    return _convert_token_usage(openapi_usage)


def convert_execute_data_to_result(data) -> 'ExecuteResult':
    """Convert ExecuteData to ExecuteResult
    
    Unified conversion entry point, reusing existing conversion logic
    Used to replace duplicate implementations in prompt.py and reader.py
    
    Args:
        data: ExecuteData object containing execution result data
        
    Returns:
        ExecuteResult: Converted execution result object
    """
    from cozeloop.entities.prompt import ExecuteResult

    return ExecuteResult(
        message=to_message(data.message) if data.message else None,
        finish_reason=data.finish_reason,
        usage=to_token_usage(data.usage)
    )


def to_openapi_message(message: EntityMessage) -> OpenAPIMessage:
    """Convert EntityMessage to OpenAPIMessage"""
    return OpenAPIMessage(
        role=_to_openapi_role(message.role),
        reasoning_content=message.reasoning_content,
        content=message.content,
        parts=[_to_openapi_content_part(part) for part in message.parts] if message.parts else None,
        tool_call_id=message.tool_call_id,
        tool_calls=[_to_openapi_tool_call(tool_call) for tool_call in
                    message.tool_calls] if message.tool_calls else None
    )


def _to_openapi_role(role: EntityRole) -> OpenAPIRole:
    """Convert EntityRole to OpenAPIRole"""
    role_mapping = {
        EntityRole.SYSTEM: OpenAPIRole.SYSTEM,
        EntityRole.USER: OpenAPIRole.USER,
        EntityRole.ASSISTANT: OpenAPIRole.ASSISTANT,
        EntityRole.TOOL: OpenAPIRole.TOOL,
        EntityRole.PLACEHOLDER: OpenAPIRole.PLACEHOLDER
    }
    return role_mapping.get(role, OpenAPIRole.USER)


def _to_openapi_content_part(part: EntityContentPart) -> OpenAPIContentPart:
    """Convert EntityContentPart to OpenAPIContentPart"""
    return OpenAPIContentPart(
        type=_to_openapi_content_type(part.type),
        text=part.text,
        image_url=part.image_url,
        base64_data=part.base64_data
    )


def _to_openapi_content_type(content_type: EntityContentType) -> OpenAPIContentType:
    """Convert EntityContentType to OpenAPIContentType"""
    type_mapping = {
        EntityContentType.TEXT: OpenAPIContentType.TEXT,
        EntityContentType.IMAGE_URL: OpenAPIContentType.IMAGE_URL,
        EntityContentType.BASE64_DATA: OpenAPIContentType.BASE64_DATA,
        EntityContentType.MULTI_PART_VARIABLE: OpenAPIContentType.MULTI_PART_VARIABLE
    }
    return type_mapping.get(content_type, OpenAPIContentType.TEXT)


def _to_openapi_tool_call(tool_call: EntityToolCall) -> OpenAPIToolCall:
    """Convert EntityToolCall to OpenAPIToolCall"""
    return OpenAPIToolCall(
        index=tool_call.index,
        id=tool_call.id,
        type=_to_openapi_tool_type(tool_call.type),
        function_call=_to_openapi_function_call(tool_call.function_call)
    )


def _to_openapi_function_call(func_call: Optional[EntityFunctionCall]) -> Optional[OpenAPIFunctionCall]:
    """Convert EntityFunctionCall to OpenAPIFunctionCall"""
    if func_call is None:
        return None
    return OpenAPIFunctionCall(
        name=func_call.name,
        arguments=func_call.arguments
    )


def _to_openapi_tool_type(tool_type: EntityToolType) -> OpenAPIToolType:
    """Convert EntityToolType to OpenAPIToolType"""
    type_mapping = {
        EntityToolType.FUNCTION: OpenAPIToolType.FUNCTION,
    }
    return type_mapping.get(tool_type, OpenAPIToolType.FUNCTION)


# Span-related conversion functions
def _to_span_prompt_input(messages: List[EntityMessage], variables: Dict[str, PromptVariable]) -> PromptInput:
    """Convert to Span prompt input"""
    return PromptInput(
        templates=_to_span_messages(messages),
        arguments=_to_span_arguments(variables),
    )


def _to_span_prompt_output(messages: List[EntityMessage]) -> PromptOutput:
    """Convert to Span prompt output"""
    return PromptOutput(
        prompts=_to_span_messages(messages)
    )


def _to_span_messages(messages: List[EntityMessage]) -> List[ModelMessage]:
    """Convert message list to Span format"""
    return [
        ModelMessage(
            role=msg.role,
            content=msg.content,
            parts=[_to_span_content_part(part) for part in msg.parts] if msg.parts else None
        ) for msg in messages
    ]


def _to_span_arguments(arguments: Dict[str, PromptVariable]) -> List[PromptArgument]:
    """Convert argument dictionary to Span format"""
    return [
        to_span_argument(key, value) for key, value in arguments.items()
    ]


def to_span_argument(key: str, value: any) -> PromptArgument:
    """Convert single argument to Span format"""
    converted_value = str(value)
    value_type = PromptArgumentValueType.TEXT

    # Check if it's a multimodal variable
    if isinstance(value, list) and all(isinstance(part, EntityContentPart) for part in value):
        value_type = PromptArgumentValueType.MODEL_MESSAGE_PART
        converted_value = [_to_span_content_part(part) for part in value]

    # Check if it's a placeholder variable
    if isinstance(value, list) and all(isinstance(part, EntityMessage) for part in value):
        value_type = PromptArgumentValueType.MODEL_MESSAGE
        converted_value = _to_span_messages(value)

    return PromptArgument(
        key=key,
        value=converted_value,
        value_type=value_type,
        source="input"
    )


def _to_span_content_type(entity_type: EntityContentType) -> ModelMessagePartType:
    """Convert content type to Span format"""
    span_content_type_mapping = {
        EntityContentType.TEXT: ModelMessagePartType.TEXT,
        EntityContentType.IMAGE_URL: ModelMessagePartType.IMAGE,
        EntityContentType.BASE64_DATA: ModelMessagePartType.IMAGE,
        EntityContentType.MULTI_PART_VARIABLE: ModelMessagePartType.MULTI_PART_VARIABLE,
    }
    return span_content_type_mapping.get(entity_type, ModelMessagePartType.TEXT)


def _to_span_content_part(entity_part: EntityContentPart) -> ModelMessagePart:
    """Convert content part to Span format"""
    image_url = None
    if entity_part.image_url is not None:
        image_url = ModelImageURL(
            url=entity_part.image_url
        )

    return ModelMessagePart(
        type=_to_span_content_type(entity_part.type),
        text=entity_part.text,
        image_url=image_url,
    )