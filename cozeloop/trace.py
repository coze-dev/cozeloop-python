# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from typing import Dict, Optional

from cozeloop.span import SpanContext, Span


class TraceClient(ABC):
    """
    Interface for handling trace-related operations in the client.
    """

    @abstractmethod
    def start_span(
            self,
            name: str,
            span_type: str,
            *,
            start_time: Optional[int] = None,
            child_of: Optional[SpanContext] = None,
            start_new_trace: bool = False,
    ) -> Span:
        """
        Generate a span that automatically links to the previous span in the context.
        The start time of the span starts counting from the call of start_span.
        The generated span will be automatically written into the context.
        Subsequent spans that need to be chained should call start_span based on the new context.
        """

    @abstractmethod
    def get_span_from_context(self) -> Span:
        """
        Get the span from the context.
        """

    @abstractmethod
    def get_span_from_header(self, header: Dict[str, str]) -> SpanContext:
        """
        Get the span from the header.
        """

    @abstractmethod
    def flush(self) -> None:
        """
        Force the reporting of spans in the queue.
        """
