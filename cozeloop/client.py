# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod

from cozeloop.prompt import PromptClient
from cozeloop.trace import TraceClient


class Client(PromptClient, TraceClient, ABC):
    """
    Abstract base class for a thread-safe loop client.
    Do not create multiple instances.
    """

    @property
    @abstractmethod
    def workspace_id(self) -> str:
        """
        Return the workspace ID.
        """

    @abstractmethod
    def close(self):
        """
        Close the client. Should be called before program exit.
        """

