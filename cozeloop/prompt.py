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
        Execute Prompt request
        
        :param prompt_key: Unique identifier of the prompt
        :param version: Prompt version, optional
        :param label: Prompt label, optional
        :param variable_vals: Variable values dictionary, optional
        :param messages: Message list, optional
        :param stream: Whether to return stream response, default False
        :param timeout: Request timeout (seconds), optional, default is 600 seconds (10 minutes)
        :return: Returns ExecuteResult when stream=False, returns StreamReader[ExecuteResult] when stream=True
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
        Asynchronously execute Prompt request
        
        :param prompt_key: Unique identifier of the prompt
        :param version: Prompt version, optional
        :param label: Prompt label, optional
        :param variable_vals: Variable values dictionary, optional
        :param messages: Message list, optional
        :param stream: Whether to return stream response, default False
        :param timeout: Request timeout (seconds), optional, default is 600 seconds (10 minutes)
        :return: Returns ExecuteResult when stream=False, returns StreamReader[ExecuteResult] when stream=True
        """