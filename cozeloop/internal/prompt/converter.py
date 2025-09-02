# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import List, Dict

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
)


def _convert_role(openapi_role: OpenAPIRole) -> EntityRole:
    role_mapping = {
        OpenAPIRole.SYSTEM: EntityRole.SYSTEM,
        OpenAPIRole.USER: EntityRole.USER,
        OpenAPIRole.ASSISTANT: EntityRole.ASSISTANT,
        OpenAPIRole.TOOL: EntityRole.TOOL,
        OpenAPIRole.PLACEHOLDER: EntityRole.PLACEHOLDER
    }
    return role_mapping.get(openapi_role, EntityRole.USER)  # Default to USER type


def _convert_content_type(openapi_type: OpenAPIContentType) -> EntityContentType:
    content_type_mapping = {
        OpenAPIContentType.TEXT: EntityContentType.TEXT,
        OpenAPIContentType.MULTI_PART_VARIABLE: EntityContentType.MULTI_PART_VARIABLE,
    }
    return content_type_mapping.get(openapi_type, EntityContentType.TEXT)


def to_content_part(openapi_part: OpenAPIContentPart) -> EntityContentPart:
    return EntityContentPart(
        type=_convert_content_type(openapi_part.type),
        text=openapi_part.text
    )


def _convert_message(msg: OpenAPIMessage) -> EntityMessage:
    return EntityMessage(
        role=_convert_role(msg.role),
        content=msg.content,
        parts=[to_content_part(part) for part in msg.parts] if msg.parts else None
    )


def _convert_variable_type(openapi_type: OpenAPIVariableType) -> EntityVariableType:
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
    return type_mapping.get(openapi_type, EntityVariableType.STRING)  # Default to STRING type


def _convert_variable_def(var_def: OpenAPIVariableDef) -> EntityVariableDef:
    return EntityVariableDef(
        key=var_def.key,
        desc=var_def.desc,
        type=_convert_variable_type(var_def.type)
    )


def _convert_function(func: OpenAPIFunction) -> EntityFunction:
    return EntityFunction(
        name=func.name,
        description=func.description,
        parameters=func.parameters
    )


def _convert_tool_type(openapi_tool_type: OpenAPIToolType) -> EntityToolType:
    type_mapping = {
        OpenAPIToolType.FUNCTION: EntityToolType.FUNCTION,
    }
    return type_mapping.get(openapi_tool_type, EntityToolType.FUNCTION)  # Default to FUNCTION type


def _convert_tool(tool: OpenAPITool) -> EntityTool:
    return EntityTool(
        type=_convert_tool_type(tool.type),
        function=_convert_function(tool.function) if tool.function else None
    )


def _convert_tool_choice_type(openapi_tool_choice_type: OpenAPIChoiceType) -> EntityToolChoiceType:
    choice_mapping = {
        OpenAPIChoiceType.AUTO: EntityToolChoiceType.AUTO,
        OpenAPIChoiceType.NONE: EntityToolChoiceType.NONE
    }
    return choice_mapping.get(openapi_tool_choice_type, EntityToolChoiceType.AUTO)  # Default to AUTO type


def _convert_tool_call_config(config: OpenAPIToolCallConfig) -> EntityToolCallConfig:
    return EntityToolCallConfig(
        tool_choice=_convert_tool_choice_type(config.tool_choice)
    )


def _convert_llm_config(config: OpenAPIModelConfig) -> EntityModelConfig:
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
    template_mapping = {
        OpenAPITemplateType.NORMAL: EntityTemplateType.NORMAL,
        OpenAPITemplateType.JINJA2: EntityTemplateType.JINJA2
    }
    return template_mapping.get(openapi_template_type, EntityTemplateType.NORMAL)  # Default to NORMAL type


def _convert_prompt_template(template: OpenAPIPromptTemplate) -> EntityPromptTemplate:
    return EntityPromptTemplate(
        template_type=_convert_template_type(template.template_type),
        messages=[_convert_message(msg) for msg in template.messages] if template.messages else None,
        variable_defs=[_convert_variable_def(var_def) for var_def in
                       template.variable_defs] if template.variable_defs else None
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


def _to_span_prompt_input(messages: List[EntityMessage], variables: Dict[str, PromptVariable]) -> PromptInput:
    return PromptInput(
        templates=_to_span_messages(messages),
        arguments=_to_span_arguments(variables),
    )


def _to_span_prompt_output(messages: List[EntityMessage]) -> PromptOutput:
    return PromptOutput(
        prompts=_to_span_messages(messages)
    )


def _to_span_messages(messages: List[EntityMessage]) -> List[ModelMessage]:
    return [
        ModelMessage(
            role=msg.role,
            content=msg.content,
            parts=[_to_span_content_part(part) for part in msg.parts] if msg.parts else None
        ) for msg in messages
    ]


def _to_span_arguments(arguments: Dict[str, PromptVariable]) -> List[PromptArgument]:
    return [
        to_span_argument(key, value) for key, value in arguments.items()
    ]


def to_span_argument(key: str, value: any) -> PromptArgument:
    converted_value = str(value)
    value_type = PromptArgumentValueType.TEXT
    # 判断是否是多模态变量
    if isinstance(value, list) and all(isinstance(part, EntityContentPart) for part in value):
        value_type = PromptArgumentValueType.MODEL_MESSAGE_PART
        converted_value = [_to_span_content_part(part) for part in value]

    # 判断是否是placeholder变量
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
    span_content_type_mapping = {
        EntityContentType.TEXT: ModelMessagePartType.TEXT,
        EntityContentType.IMAGE_URL: ModelMessagePartType.IMAGE,
        EntityContentType.MULTI_PART_VARIABLE: ModelMessagePartType.MULTI_PART_VARIABLE,
    }
    return span_content_type_mapping.get(entity_type, ModelMessagePartType.TEXT)


def _to_span_content_part(entity_part: EntityContentPart) -> ModelMessagePart:
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
