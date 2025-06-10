# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import time
from typing import List, Optional, Union, Dict, Any
from pydantic.dataclasses import dataclass
from langchain_core.messages import BaseMessage, ToolMessage, AIMessageChunk
from langchain_core.outputs import Generation, ChatGeneration


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
            is_part = False
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
    choices: Optional[List[Choice]] = None


@dataclass
class ModelTraceInputData:
    messages: Optional[List[Message]] = None
    tools: Optional[List[Tool]] = None


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
        for message in process_messages:
            if isinstance(message, AIMessageChunk):
                self._messages.append(Message(role=message.type, content=message.content, tool_calls=convert_tool_calls(message.additional_kwargs.get('tool_calls', []))))
            elif isinstance(message, ToolMessage):
                tool_call = ToolCall(id=message.tool_call_id, type=message.type, function= ToolFunction(name=message.additional_kwargs.get('name', '')))
                self._messages.append(Message(role=message.type, content=message.content, tool_calls=[tool_call]))
            else:
                self._messages.append(Message(role=message.type, content=message.content))

    def to_json(self):
        tools: List[Tool] = []
        for tool in self._invocation_params.get('tools', []):
            function = ToolFunction(name=tool.get('function', {}).get('name', ''),
                                    description=tool.get('function', {}).get('description', ''),
                                    parameters=tool.get('function', {}).get('parameters', {}))
            tools.append(Tool(type=tool.get('type', ''), function=function))
        if len(tools) == 0 and 'functions' in self._invocation_params:
            for bind_function in self._invocation_params['functions']:
                function = ToolFunction(name=bind_function.get('function', {}).get('name', ''),
                                        description=bind_function.get('description', ''),
                                        parameters=bind_function.get('parameters', {}))
                tools.append(Tool(type=bind_function.get('type', ''), function=function))
        return json.dumps(
            ModelTraceInputData(messages=self._messages, tools=tools),
            default=lambda o: dict((key, value) for key, value in o.__dict__.items() if value),
            sort_keys=False,
            ensure_ascii=False)


class ModelTraceOutput:
    def __init__(self, generations: List[Union[ChatGeneration, Generation]]):
        super().__init__()
        self.generations = generations[0] if len(generations) > 0 else {}

    def to_json(self):
        choices: List[Choice] = []
        for i, generation in enumerate(self.generations):
            choice: Choice = None
            if isinstance(generation, ChatGeneration):
                tool_calls = convert_tool_calls(generation.message.additional_kwargs.get('tool_calls', []))
                if len(tool_calls) == 0 and 'function_call' in generation.message.additional_kwargs:
                    function_call = generation.message.additional_kwargs.get('function_call', {})
                    function = ToolFunction(name=function_call.get('name', ''), arguments=json.loads(function_call.get('arguments', {})))
                    tool_calls.append(ToolCall(function=function, type='function_call(deprecated)'))
                message = Message(role=generation.message.type, content=generation.message.content, tool_calls=tool_calls)
                choice = Choice(index=i, message=message, finish_reason=generation.generation_info.get('finish_reason', ''))
            elif isinstance(generation, Generation):
                choice = Choice(index=i, message=Message(content=generation.text))
            choices.append(choice)
        return json.dumps(
            Choices(choices=choices),
            default=lambda o: dict((key, value) for key, value in o.__dict__.items() if value or key=='index'),
            sort_keys=False,
            ensure_ascii=False)


def convert_tool_calls(tool_calls: list) -> List[ToolCall]:
    format_tool_calls: List[ToolCall] = []
    for tool_call in tool_calls:
        function = ToolFunction(name=tool_call.get('function', {}).get('name', ''), arguments=json.loads(tool_call.get('function', {}).get('arguments', {})))
        format_tool_calls.append(ToolCall(id=tool_call.get('id', ''), type=tool_call.get('type', ''), function=function))
    return format_tool_calls