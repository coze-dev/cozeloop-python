# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import types
from abc import ABC, abstractmethod
from typing import Dict, Any
from datetime import datetime
from cozeloop.entities.prompt import Prompt
from cozeloop.spec.tracespec import Runtime


class SpanContext(ABC):
    """
    Interface for Span Context operations.
    """

    @property
    @abstractmethod
    def span_id(self) -> str:
        """
        Get the Span ID.
        """

    @property
    @abstractmethod
    def trace_id(self) -> str:
        """
        Get the Trace ID.
        """

    @property
    @abstractmethod
    def baggage(self) -> Dict[str, str]:
        """
        Get the baggage as a dictionary of key-value pairs.
        """


class CommonSpanSetter(ABC):
    """
    Interface for setting system-defined fields in a span.
    """

    @abstractmethod
    def set_input(self, input: Any) -> None:
        """
        Set input information, serialized into a JSON string.
        Key: `input`.
        The recommended standard format is ModelInput of spec package, but custom fields can also be used.
        """

    @abstractmethod
    def set_output(self, output: Any) -> None:
        """
        Set output information, serialized into a JSON string.
        Key: `output`.
        The recommended standard format is ModelOutput of spec package, but custom fields can also be used.
        """

    @abstractmethod
    def set_error(self, err: Exception) -> None:
        """
        Set error message.
        Key: `error`.
        """

    @abstractmethod
    def set_status_code(self, code: int) -> None:
        """
        Set status code. A non-zero code is considered an exception.
        Key: `_status_code`.
        """

    @abstractmethod
    def set_user_id(self, user_id: str) -> None:
        """
        Set user ID.
        Key: `user_id`.
        """

    @abstractmethod
    def set_user_id_baggage(self, user_id: str) -> None:
        """
        Set user ID as baggage.
        """

    @abstractmethod
    def set_message_id(self, message_id: str) -> None:
        """
        Set message ID.
        Key: `message_id`.
        """

    @abstractmethod
    def set_message_id_baggage(self, message_id: str) -> None:
        """
        Set message ID as baggage.
        """

    @abstractmethod
    def set_thread_id(self, thread_id: str) -> None:
        """
        Set thread ID for correlating multiple requests.
        Key: `thread_id`.
        """

    @abstractmethod
    def set_thread_id_baggage(self, thread_id: str) -> None:
        """
        Set thread ID as baggage.
        """

    @abstractmethod
    def set_prompt(self, prompt: Prompt) -> None:
        """
        Set the PromptKey and PromptVersion tags associated with the prompt.
        Key: `prompt`.
        """

    @abstractmethod
    def set_model_provider(self, model_provider: str) -> None:
        """
        Set the LLM provider, such as OpenAI.
        Key: `model_provider`.
        """

    @abstractmethod
    def set_model_name(self, model_name: str) -> None:
        """
        Set the name of the LLM model, such as gpt-4-1106-preview.
        Key: `model_name`.
        """

    @abstractmethod
    def set_model_call_options(self, model_call_options: Any) -> None:
        """
        Set the model call options
        Key: `call_options`.
        """

    @abstractmethod
    def set_input_tokens(self, input_tokens: int) -> None:
        """
        Set the usage of input tokens.
        Key: `input_tokens`.
        It will be automatically summed with output_tokens to calculate the tokens tag.
        """

    @abstractmethod
    def set_output_tokens(self, output_tokens: int) -> None:
        """
        Set the usage of output tokens.
        Key: `output_tokens`.
        It will be automatically summed with input_tokens to calculate the tokens tag.
        """

    @abstractmethod
    def set_start_time_first_resp(self, start_time_first_resp: int) -> None:
        """
        Set the timestamp of the first packet return from LLM in microseconds.
        Key: `start_time_first_resp`.
        """

    @abstractmethod
    def set_runtime(self, runtime: Runtime) -> None:
        """
        Set the runtime of the span. Only used for integration.
        Key: `runtime`.
        """

    @abstractmethod
    def set_service_name(self, service_name: str) -> None:
        """
        set the custom service name, identify different services.
        """

    @abstractmethod
    def set_log_id(self, log_id: str) -> None:
        """
        Set the custom log id, identify different query.
        """

    @abstractmethod
    def set_system_tags(self, system_tags: Dict[str, Any]) -> None:
        """
        Set system tags. DO NOT use this method unless you know what you are doing.
        """

    def set_deployment_env(self, deployment_env: str) -> None:
        """
        Set the deployment environment of the span, identify custom environments.
        """


class Span(CommonSpanSetter, SpanContext):
    """
    Interface for Span operations with tracing and tagging capabilities.
    """

    @abstractmethod
    def set_tags(self, tag_kvs: Dict[str, Any]) -> None:
        """
        Set business custom tags. Tag value should be JSON-serializable,str,int,float,bool,Sequence[str],Sequence[bool],Sequence[int],Sequence[float].
        """

    @abstractmethod
    def set_baggage(self, baggage_items: Dict[str, str]) -> None:
        """
        Set tags and also pass these tags to other downstream spans (assuming the user uses
        `to_header` and `from_header` to handle header passing between services).
        Value should be JSON-serializable,str,int,float,bool,Sequence[str],Sequence[bool],Sequence[int],Sequence[float].
        """

    @abstractmethod
    def finish(self) -> None:
        """
        The span will be reported only after an explicit call to Finish.
        Under the hood, it is actually placed in an asynchronous queue waiting to be reported.
        """

    @property
    @abstractmethod
    def start_time(self) -> datetime:
        """
        Returns the start time as a timestamp of the Span.
        """

    @abstractmethod
    def to_header(self) -> Dict[str, str]:
        """
        Convert the span to headers. Used for cross-process correlation.
        """

    @abstractmethod
    def __enter__(self):
        return self

    @abstractmethod
    def __exit__(self, exc, value, tb):
        self.finish()
