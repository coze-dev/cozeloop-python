# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
from typing import Dict, Optional, List

from cozeloop.client import Client
from cozeloop.entities.prompt import Prompt, Message, PromptVariable
from cozeloop.internal.trace.noop_span import NoopSpan
from cozeloop.span import SpanContext, Span

NOOP_SPAN = NoopSpan()


logger = logging.getLogger(__name__)


class _NoopClient(Client):
    def __init__(self, e: Exception):
        self.new_exception = e

    @property
    def workspace_id(self) -> str:
        logger.warning(f"Noop client not supported. {self.new_exception}")
        return ""

    def close(self):
        logger.warning(f"Noop client not supported. {self.new_exception}")

    def get_prompt(self, prompt_key: str, version: str = '', label: str = '') -> Optional[Prompt]:
        logger.warning(f"Noop client not supported. {self.new_exception}")
        raise self.new_exception

    def prompt_format(self, prompt: Prompt, variables: Dict[str, PromptVariable]) -> List[Message]:
        logger.warning(f"Noop client not supported. {self.new_exception}")
        raise self.new_exception

    def start_span(self, name: str, span_type: str, *, start_time: Optional[int] = None,
                   child_of: Optional[SpanContext] = None, start_new_trace: bool = False) -> Span:
        logger.warning(f"Noop client not supported. {self.new_exception}")
        return NOOP_SPAN

    def get_span_from_context(self) -> Span:
        logger.warning(f"Noop client not supported. {self.new_exception}")
        return NOOP_SPAN

    def get_span_from_header(self, header: Dict[str, str]) -> SpanContext:
        logger.warning(f"Noop client not supported. {self.new_exception}")
        return NOOP_SPAN

    def flush(self) -> None:
        logger.warning(f"Noop client not supported. {self.new_exception}")
