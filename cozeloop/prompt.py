# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from cozeloop.entities.prompt import Prompt, Message, PromptVariable


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
