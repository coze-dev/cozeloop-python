# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import logging
import time
from typing import List, Optional, Union, Dict, Any
from pydantic.dataclasses import dataclass
from langchain_core.messages import BaseMessage, ToolMessage, AIMessageChunk, AIMessage
from langchain_core.outputs import Generation, ChatGeneration

logger = logging.getLogger(__name__)


@dataclass
class ToolFunction:
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[dict] = None
    arguments: Optional[Union[dict, str]] = None


@dataclass
class Tool:
    type: Optional[str] = None
    function: Optional[ToolFunction] = None


@dataclass
class ToolCall:
    id: Optional[str] = None
    type: Optional[str] = None
    function: Optional[ToolFunction] = None


@dataclass
class ImageUrl:
    url: Optional[str] = None


@dataclass
class Parts:
    type: Optional[str] = None
    text: Optional[str] = None
    image_url: Optional[ImageUrl] = None


@dataclass
class Message:
    role: Optional[str] = None
    content: Optional[Union[str, List[Union[dict, Parts]], dict]] = None
    parts: Optional[List[Parts]] = None
    tool_calls: List[ToolCall] = None
    metadata: Optional[dict] = None
    reasoning_content: Optional[str] = None

    def __post_init__(self):
        if self.role is not None and (self.role == 'AIMessageChunk' or self.role == 'ai'):
            self.role = 'assistant'
        parts: Optional[List[Parts]] = []
        if isinstance(self.content, List) and all(isinstance(x, dict) for x in self.content):
            is_parts = False
            for each in self.content:
                text = each.get('text', None)
                url = each.get('url', each.get('image_url', {}).get('url', None))
                if text is None and url is None:
                    continue
                is_parts = True
                parts.append(Parts(type=each.get('type', ''), text=text, image_url=ImageUrl(url=url) if url is not None else None))
            if is_parts:
                self.content = None
            else:
                self.content = self.content.__str__()
        elif isinstance(self.content, dict):
            text = self.content.get('text', None)
            url = self.content.get('url', self.content.get('image_url', {}).get('url', None))
            if text is not None or url is not None:
                parts.append(Parts(type=self.content.get('type', ''), text=text, image_url=ImageUrl(url=url) if url is not None else None))
                self.content = None
            else:
                self.content = self.content.__str__()
        elif isinstance(self.content, List) and all(type(x, Parts) for x in self.content):
            parts = self.content
            self.content = None
        if len(parts) > 0:
            self.parts = parts


@dataclass
class Choice:
    index: Optional[int] = None
    message: Optional[Message] = None
    finish_reason: Optional[str] = None


@dataclass
class Choices:
    id: Optional[str] = None
    choices: Optional[List[Choice]] = None


@dataclass
class ModelTraceInputData:
    messages: Optional[List[Message]] = None
    tools: Optional[List[Tool]] = None
    previous_response_id: Optional[str] = None


@dataclass
class ModelMeta:
    message: Optional[List] = None
    model_name: Optional[str] = None
    receive_first_token: Optional[bool] = False
    entry_timestamp: Optional[int] = None

    def __post_init__(self):
        self.entry_timestamp = int(round(time.time() * 1000))


class ModelTraceInput:
    def __init__(self, messages: List[Union[BaseMessage, List[BaseMessage]]], invocation_params: dict):
        self._invocation_params = invocation_params
        self._messages: List[Union[BaseMessage, Message]] = []
        process_messages: List[BaseMessage] = []
        for inner_messages in messages:
            if isinstance(inner_messages, BaseMessage):
                process_messages.append(inner_messages)
            elif isinstance(inner_messages, List):
                for message in inner_messages:
                    process_messages.append(message)

        tool_call_id_name_map = {}
        for message in process_messages:
            if isinstance(message, (AIMessageChunk, AIMessage)):
                if message.additional_kwargs:
                    for tool_call in message.additional_kwargs.get('tool_calls', []):
                        if tool_call and tool_call.get('id', ''):
                            tool_call_id_name_map[tool_call.get('id', '')] = tool_call.get('function', {}).get('name', '')
                for tool_call in message.tool_calls:
                    if tool_call and tool_call.get('id', ''):
                        tool_call_id_name_map[tool_call.get('id', '')] = tool_call.get('name', '')

        for message in process_messages:
            if isinstance(message, (AIMessageChunk, AIMessage)):
                tool_calls = []
                if message.additional_kwargs:
                    tool_calls = convert_tool_calls_by_additional_kwargs(message.additional_kwargs.get('tool_calls', []))
                if len(tool_calls) == 0:
                    tool_calls = convert_tool_calls_by_raw(message.tool_calls)
                self._messages.append(Message(role=message.type, content=message.content, tool_calls=tool_calls))
            elif isinstance(message, ToolMessage):
                name = ''
                if tool_call_id_name_map.get(message.tool_call_id, None) is not None:
                    name = tool_call_id_name_map[message.tool_call_id]
                if message.additional_kwargs is not None and message.additional_kwargs.get('name', ''):
                    name = message.additional_kwargs.get('name', '')
                tool_call = ToolCall(id=message.tool_call_id, type=message.type, function=ToolFunction(name=name))
                self._messages.append(Message(role=message.type, content=message.content, tool_calls=[tool_call]))
            else:
                self._messages.append(Message(role=message.type, content=message.content))

    def to_json(self):
        if self._invocation_params is None:
            return '{}'
        tools: List[Tool] = []
        for tool in self._invocation_params.get('tools', []):
            if tool.get('function', {}) is None:
                continue
            function = ToolFunction(name=tool.get('function', {}).get('name', ''),
                                    description=tool.get('function', {}).get('description', ''),
                                    parameters=tool.get('function', {}).get('parameters', {}))
            tools.append(Tool(type=tool.get('type', ''), function=function))
        if len(tools) == 0 and 'functions' in self._invocation_params:
            for bind_function in self._invocation_params.get('functions', []):
                name = ''
                if bind_function.get('function', {}):
                    name = bind_function.get('function', {}).get('name', '')
                function = ToolFunction(name=name,
                                        description=bind_function.get('description', ''),
                                        parameters=bind_function.get('parameters', {}))
                tools.append(Tool(type=bind_function.get('type', ''), function=function))

        pre_resp_id = self._invocation_params.get('previous_response_id', None)
        return json.dumps(
            ModelTraceInputData(messages=self._messages, tools=tools, previous_response_id=pre_resp_id),
            default=lambda o: dict((key, value) for key, value in o.__dict__.items() if value),
            sort_keys=False,
            ensure_ascii=False)


class ModelTraceOutput:
    def __init__(self, generations: List[Union[ChatGeneration, Generation]]):
        super().__init__()
        self.generations = generations[0] if len(generations) > 0 else {}

    def to_json(self):
        choices: List[Choice] = []
        response_id = None
        for i, generation in enumerate(self.generations):
            choice: Choice = None
            if isinstance(generation, ChatGeneration):
                message = convert_output_message(generation.message)
                if message and message.metadata:
                    response_id = message.metadata.get('id', None)
                choice = Choice(index=i, message=message)
                if generation.generation_info:
                    choice.finish_reason = generation.generation_info.get('finish_reason', '')
            elif isinstance(generation, Generation):
                choice = Choice(index=i, message=Message(content=generation.text))
            choices.append(choice)
        res = ''
        try:
            res = json.dumps(
                Choices(id=response_id, choices=choices),
                default=lambda o: dict((key, value) for key, value in o.__dict__.items() if value or key == 'index'),
                sort_keys=False,
                ensure_ascii=False)
        except Exception as e:
            logging.error(f"ModelTraceOutput.to_json failed, exception: {e}, choices: {choices}")
            raise e
        finally:
            return res


def convert_tool_calls_by_raw(tool_calls: list) -> List[ToolCall]:
    format_tool_calls: List[ToolCall] = []
    for tool_call in tool_calls:
        if tool_call is None:
            continue
        function = ToolFunction(name=tool_call.get('name', ''), arguments=tool_call.get('args', {}))
        format_tool_calls.append(ToolCall(id=tool_call.get('id', ''), type=tool_call.get('type', ''), function=function))
    return format_tool_calls


def convert_tool_calls_by_additional_kwargs(tool_calls: list) -> List[ToolCall]:
    format_tool_calls: List[ToolCall] = []
    for tool_call in tool_calls:
        if tool_call is None or tool_call.get('function', {}) is None:
            continue
        raw_args = tool_call.get('function', {}).get('arguments', '{}')
        final_args = None
        try:
            final_args = json.loads(raw_args)
        except Exception as e:
            final_args = raw_args
            logger.error(f"convert_tool_calls_by_additional_kwargs failed, error: {e}, tool_call.function.arguments: {raw_args}")
        function = ToolFunction(name=tool_call.get('function', {}).get('name', ''), arguments=final_args)
        format_tool_calls.append(ToolCall(id=tool_call.get('id', ''), type=tool_call.get('type', ''), function=function))
    return format_tool_calls


def convert_output_message(message: BaseMessage) -> Message:
    if message is None:
        return None
    tool_calls = convert_tool_calls_by_additional_kwargs(message.additional_kwargs.get('tool_calls', []))
    if len(tool_calls) == 0 and isinstance(message, (AIMessage, AIMessageChunk)):
        tool_calls = convert_tool_calls_by_raw(message.tool_calls)
    if len(tool_calls) == 0 and 'function_call' in message.additional_kwargs:
        function_call = message.additional_kwargs.get('function_call', {})
        try:
            arg = json.loads(function_call.get('arguments', {}))
        except Exception as e:
            logging.error(f"ModelTraceOutput.to_json arguments loads failed, exception: {e}")
            arg = {}
        function = ToolFunction(name=function_call.get('name', ''), arguments=arg)
        tool_calls.append(ToolCall(function=function, type='function_call(deprecated)'))
    metadata = {}
    if message.response_metadata is not None:
        if message.response_metadata.get('id', ''):
            response_id = message.response_metadata.get('id', '')
            metadata['id'] = response_id
    message = Message(
        role=message.type,
        content=message.content,
        tool_calls=tool_calls,
        metadata=metadata,
        reasoning_content=message.additional_kwargs.get('reasoning_content', ''),
    )

    return message