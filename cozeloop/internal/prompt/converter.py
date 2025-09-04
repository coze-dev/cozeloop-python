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
    """转换角色类型"""
    role_mapping = {
        OpenAPIRole.SYSTEM: EntityRole.SYSTEM,
        OpenAPIRole.USER: EntityRole.USER,
        OpenAPIRole.ASSISTANT: EntityRole.ASSISTANT,
        OpenAPIRole.TOOL: EntityRole.TOOL,
        OpenAPIRole.PLACEHOLDER: EntityRole.PLACEHOLDER
    }
    return role_mapping.get(openapi_role, EntityRole.USER)


def _convert_content_type(openapi_type: OpenAPIContentType) -> EntityContentType:
    """转换内容类型"""
    content_type_mapping = {
        OpenAPIContentType.TEXT: EntityContentType.TEXT,
        OpenAPIContentType.IMAGE_URL: EntityContentType.IMAGE_URL,
        OpenAPIContentType.BASE64_DATA: EntityContentType.BASE64_DATA,
        OpenAPIContentType.MULTI_PART_VARIABLE: EntityContentType.MULTI_PART_VARIABLE,
    }
    return content_type_mapping.get(openapi_type, EntityContentType.TEXT)


def _convert_content_part(openapi_part: OpenAPIContentPart) -> EntityContentPart:
    """转换内容部分，确保text、image_url、base64_data字段都被转换"""
    return EntityContentPart(
        type=_convert_content_type(openapi_part.type),
        text=openapi_part.text,
        image_url=openapi_part.image_url,
        base64_data=openapi_part.base64_data
    )


def _convert_function_call(func_call: Optional[OpenAPIFunctionCall]) -> Optional[EntityFunctionCall]:
    """转换函数调用，确保name、arguments字段都被转换"""
    if func_call is None:
        return None
    return EntityFunctionCall(
        name=func_call.name,
        arguments=func_call.arguments
    )


def _convert_tool_call(tool_call: OpenAPIToolCall) -> EntityToolCall:
    """转换工具调用，确保index、id、type、function_call字段都被转换"""
    return EntityToolCall(
        index=tool_call.index,
        id=tool_call.id,
        type=_convert_tool_type(tool_call.type),
        function_call=_convert_function_call(tool_call.function_call)
    )


def _convert_message(msg: OpenAPIMessage) -> EntityMessage:
    """转换消息，确保role、content、reasoning_content、tool_call_id、tool_calls字段都被转换"""
    return EntityMessage(
        role=_convert_role(msg.role),
        reasoning_content=msg.reasoning_content,
        content=msg.content,
        parts=[_convert_content_part(part) for part in msg.parts] if msg.parts else None,
        tool_call_id=msg.tool_call_id,
        tool_calls=[_convert_tool_call(tool_call) for tool_call in msg.tool_calls] if msg.tool_calls else None
    )


def _convert_variable_type(openapi_type: OpenAPIVariableType) -> EntityVariableType:
    """转换变量类型"""
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
    """转换变量定义"""
    return EntityVariableDef(
        key=var_def.key,
        desc=var_def.desc,
        type=_convert_variable_type(var_def.type)
    )


def _convert_function(func: OpenAPIFunction) -> EntityFunction:
    """转换函数定义"""
    return EntityFunction(
        name=func.name,
        description=func.description,
        parameters=func.parameters
    )


def _convert_tool_type(openapi_tool_type: OpenAPIToolType) -> EntityToolType:
    """转换工具类型"""
    type_mapping = {
        OpenAPIToolType.FUNCTION: EntityToolType.FUNCTION,
    }
    return type_mapping.get(openapi_tool_type, EntityToolType.FUNCTION)


def _convert_tool(tool: OpenAPITool) -> EntityTool:
    """转换工具定义"""
    return EntityTool(
        type=_convert_tool_type(tool.type),
        function=_convert_function(tool.function) if tool.function else None
    )


def _convert_tool_choice_type(openapi_tool_choice_type: OpenAPIChoiceType) -> EntityToolChoiceType:
    """转换工具选择类型"""
    choice_mapping = {
        OpenAPIChoiceType.AUTO: EntityToolChoiceType.AUTO,
        OpenAPIChoiceType.NONE: EntityToolChoiceType.NONE
    }
    return choice_mapping.get(openapi_tool_choice_type, EntityToolChoiceType.AUTO)


def _convert_tool_call_config(config: OpenAPIToolCallConfig) -> EntityToolCallConfig:
    """转换工具调用配置"""
    return EntityToolCallConfig(
        tool_choice=_convert_tool_choice_type(config.tool_choice)
    )


def _convert_llm_config(config: OpenAPIModelConfig) -> EntityModelConfig:
    """转换LLM配置"""
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
    """转换模板类型"""
    template_mapping = {
        OpenAPITemplateType.NORMAL: EntityTemplateType.NORMAL,
        OpenAPITemplateType.JINJA2: EntityTemplateType.JINJA2
    }
    return template_mapping.get(openapi_template_type, EntityTemplateType.NORMAL)


def _convert_prompt_template(template: OpenAPIPromptTemplate) -> EntityPromptTemplate:
    """转换提示模板"""
    return EntityPromptTemplate(
        template_type=_convert_template_type(template.template_type),
        messages=[_convert_message(msg) for msg in template.messages] if template.messages else None,
        variable_defs=[_convert_variable_def(var_def) for var_def in
                       template.variable_defs] if template.variable_defs else None
    )


def _convert_token_usage(usage: Optional[OpenAPITokenUsage]) -> Optional[EntityTokenUsage]:
    """转换Token使用统计，确保input_tokens、output_tokens字段都被转换"""
    if usage is None:
        return None
    return EntityTokenUsage(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens
    )


def _convert_prompt(prompt: OpenAPIPrompt) -> EntityPrompt:
    """转换OpenAPI Prompt对象到entity Prompt对象"""
    return EntityPrompt(
        workspace_id=prompt.workspace_id,
        prompt_key=prompt.prompt_key,
        version=prompt.version,
        prompt_template=_convert_prompt_template(prompt.prompt_template) if prompt.prompt_template else None,
        tools=[_convert_tool(tool) for tool in prompt.tools] if prompt.tools else None,
        tool_call_config=_convert_tool_call_config(prompt.tool_call_config) if prompt.tool_call_config else None,
        llm_config=_convert_llm_config(prompt.llm_config) if prompt.llm_config else None
    )


# 公开的转换函数
def to_content_part(openapi_part: OpenAPIContentPart) -> EntityContentPart:
    """公开的内容部分转换函数"""
    return _convert_content_part(openapi_part)


def to_prompt(openapi_prompt: OpenAPIPrompt) -> EntityPrompt:
    """公开的提示转换函数"""
    return _convert_prompt(openapi_prompt)


def to_message(openapi_message: OpenAPIMessage) -> EntityMessage:
    """公开的消息转换函数"""
    return _convert_message(openapi_message)


def to_token_usage(openapi_usage: Optional[OpenAPITokenUsage]) -> Optional[EntityTokenUsage]:
    """公开的Token使用统计转换函数"""
    return _convert_token_usage(openapi_usage)


def convert_execute_data_to_result(data) -> 'ExecuteResult':
    """将ExecuteData转换为ExecuteResult
    
    统一的转换入口，复用现有转换逻辑
    用于替代 prompt.py 和 reader.py 中的重复实现
    
    Args:
        data: ExecuteData对象，包含执行结果数据
        
    Returns:
        ExecuteResult: 转换后的执行结果对象
    """
    from cozeloop.entities.prompt import ExecuteResult

    return ExecuteResult(
        message=to_message(data.message) if data.message else None,
        finish_reason=data.finish_reason,
        usage=to_token_usage(data.usage)
    )


def to_openapi_message(message: EntityMessage) -> OpenAPIMessage:
    """将EntityMessage转换为OpenAPIMessage"""
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
    """将EntityRole转换为OpenAPIRole"""
    role_mapping = {
        EntityRole.SYSTEM: OpenAPIRole.SYSTEM,
        EntityRole.USER: OpenAPIRole.USER,
        EntityRole.ASSISTANT: OpenAPIRole.ASSISTANT,
        EntityRole.TOOL: OpenAPIRole.TOOL,
        EntityRole.PLACEHOLDER: OpenAPIRole.PLACEHOLDER
    }
    return role_mapping.get(role, OpenAPIRole.USER)


def _to_openapi_content_part(part: EntityContentPart) -> OpenAPIContentPart:
    """将EntityContentPart转换为OpenAPIContentPart"""
    return OpenAPIContentPart(
        type=_to_openapi_content_type(part.type),
        text=part.text,
        image_url=part.image_url,
        base64_data=part.base64_data
    )


def _to_openapi_content_type(content_type: EntityContentType) -> OpenAPIContentType:
    """将EntityContentType转换为OpenAPIContentType"""
    type_mapping = {
        EntityContentType.TEXT: OpenAPIContentType.TEXT,
        EntityContentType.IMAGE_URL: OpenAPIContentType.IMAGE_URL,
        EntityContentType.BASE64_DATA: OpenAPIContentType.BASE64_DATA,
        EntityContentType.MULTI_PART_VARIABLE: OpenAPIContentType.MULTI_PART_VARIABLE
    }
    return type_mapping.get(content_type, OpenAPIContentType.TEXT)


def _to_openapi_tool_call(tool_call: EntityToolCall) -> OpenAPIToolCall:
    """将EntityToolCall转换为OpenAPIToolCall"""
    return OpenAPIToolCall(
        index=tool_call.index,
        id=tool_call.id,
        type=_to_openapi_tool_type(tool_call.type),
        function_call=_to_openapi_function_call(tool_call.function_call)
    )


def _to_openapi_function_call(func_call: Optional[EntityFunctionCall]) -> Optional[OpenAPIFunctionCall]:
    """将EntityFunctionCall转换为OpenAPIFunctionCall"""
    if func_call is None:
        return None
    return OpenAPIFunctionCall(
        name=func_call.name,
        arguments=func_call.arguments
    )


def _to_openapi_tool_type(tool_type: EntityToolType) -> OpenAPIToolType:
    """将EntityToolType转换为OpenAPIToolType"""
    type_mapping = {
        EntityToolType.FUNCTION: OpenAPIToolType.FUNCTION,
    }
    return type_mapping.get(tool_type, OpenAPIToolType.FUNCTION)


# Span相关转换函数
def _to_span_prompt_input(messages: List[EntityMessage], variables: Dict[str, PromptVariable]) -> PromptInput:
    """转换到Span的提示输入"""
    return PromptInput(
        templates=_to_span_messages(messages),
        arguments=_to_span_arguments(variables),
    )


def _to_span_prompt_output(messages: List[EntityMessage]) -> PromptOutput:
    """转换到Span的提示输出"""
    return PromptOutput(
        prompts=_to_span_messages(messages)
    )


def _to_span_messages(messages: List[EntityMessage]) -> List[ModelMessage]:
    """转换消息列表到Span格式"""
    return [
        ModelMessage(
            role=msg.role,
            content=msg.content,
            parts=[_to_span_content_part(part) for part in msg.parts] if msg.parts else None
        ) for msg in messages
    ]


def _to_span_arguments(arguments: Dict[str, PromptVariable]) -> List[PromptArgument]:
    """转换参数字典到Span格式"""
    return [
        to_span_argument(key, value) for key, value in arguments.items()
    ]


def to_span_argument(key: str, value: any) -> PromptArgument:
    """转换单个参数到Span格式"""
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
    """转换内容类型到Span格式"""
    span_content_type_mapping = {
        EntityContentType.TEXT: ModelMessagePartType.TEXT,
        EntityContentType.IMAGE_URL: ModelMessagePartType.IMAGE,
        EntityContentType.BASE64_DATA: ModelMessagePartType.IMAGE,
        EntityContentType.MULTI_PART_VARIABLE: ModelMessagePartType.MULTI_PART_VARIABLE,
    }
    return span_content_type_mapping.get(entity_type, ModelMessagePartType.TEXT)


def _to_span_content_part(entity_part: EntityContentPart) -> ModelMessagePart:
    """转换内容部分到Span格式"""
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
