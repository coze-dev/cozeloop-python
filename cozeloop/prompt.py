# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any

from cozeloop.entities.prompt import Prompt, Message, PromptVariable, ExecuteResult
from cozeloop.entities.stream import StreamReader


class PromptClient(ABC):
    """
    Interface for PromptClient.
    """

    @abstractmethod
    def get_prompt(self, prompt_key: str, version: str = '', label: str = '') -> Optional[Prompt]:
        """
        Get a prompt by prompt key and version.

        :param prompt_key: A unique key for retrieving the prompt.
        :param version: The version of the prompt. Defaults to empty, which represents fetching the latest version.
        :param label: The label of the prompt. Defaults to empty.
        :return: An instance of `entity.Prompt` if found, or None.
        """

    @abstractmethod
    def prompt_format(
            self,
            prompt: Prompt,
            variables: Dict[str, PromptVariable]
    ) -> List[Message]:
        """
        Format a prompt with variables.

        :param prompt: Instance of the prompt to format.
        :param variables: A dictionary of variables to use when formatting the prompt.
        :return: A list of formatted messages (`entity.Message`) if successful, or None.
        """

    @abstractmethod
    def execute_prompt(
        self,
        prompt_key: str,
        *,
        version: Optional[str] = None,
        label: Optional[str] = None,
        variable_vals: Optional[Dict[str, Any]] = None,
        messages: Optional[List[Message]] = None,
        stream: bool = False,
        timeout: Optional[int] = None
    ) -> Union[ExecuteResult, StreamReader[ExecuteResult]]:
        """
        执行Prompt请求
        
        :param prompt_key: prompt的唯一标识
        :param version: prompt版本，可选
        :param label: prompt标签，可选
        :param variable_vals: 变量值字典，可选
        :param messages: 消息列表，可选
        :param stream: 是否流式返回，默认False
        :param timeout: 请求超时时间（秒），可选，默认为600秒（10分钟）
        :return: stream=False时返回ExecuteResult，stream=True时返回StreamReader[ExecuteResult]
        """

    @abstractmethod  
    async def aexecute_prompt(
        self,
        prompt_key: str,
        *,
        version: Optional[str] = None,
        label: Optional[str] = None,
        variable_vals: Optional[Dict[str, Any]] = None,
        messages: Optional[List[Message]] = None,
        stream: bool = False,
        timeout: Optional[int] = None
    ) -> Union[ExecuteResult, StreamReader[ExecuteResult]]:
        """
        异步执行Prompt请求
        
        :param prompt_key: prompt的唯一标识
        :param version: prompt版本，可选
        :param label: prompt标签，可选
        :param variable_vals: 变量值字典，可选
        :param messages: 消息列表，可选
        :param stream: 是否流式返回，默认False
        :param timeout: 请求超时时间（秒），可选，默认为600秒（10分钟）
        :return: stream=False时返回ExecuteResult，stream=True时返回StreamReader[ExecuteResult]
        """