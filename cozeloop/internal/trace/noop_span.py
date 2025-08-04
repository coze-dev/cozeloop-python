# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import types
from abc import ABC
from datetime import datetime
from typing import Dict, Any

from cozeloop.entities.prompt import Prompt
from cozeloop.span import Span
from cozeloop.spec.tracespec import Runtime


class NoopSpan(Span, ABC):
    @property
    def get_span_id(self) -> str:
        return ''

    @property
    def get_trace_id(self) -> str:
        return ''

    @property
    def get_baggage(self) -> Dict[str, str]:
        return {}

    @property
    def get_start_time(self) -> datetime:
        return datetime.now()

    def set_tags(self, tag_kvs: Dict[str, Any]) -> None:
        pass

    def set_baggage(self, baggage_items: Dict[str, str]) -> None:
        pass

    def finish(self) -> None:
        pass

    @property
    def baggage(self) -> Dict[str, str]:
        return {}

    @property
    def trace_id(self) -> str:
        return ""

    @property
    def span_id(self) -> str:
        return ""

    @property
    def start_time(self) -> int:
        return 0

    def to_header(self) -> Dict[str, str]:
        return {}

    def set_input(self, input: Any) -> None:
        pass

    def set_output(self, output: Any) -> None:
        pass

    def set_error(self, err: Exception) -> None:
        pass

    def set_status_code(self, code: int) -> None:
        pass

    def set_user_id(self, user_id: str) -> None:
        pass

    def set_user_id_baggage(self, user_id: str) -> None:
        pass

    def set_message_id(self, message_id: str) -> None:
        pass

    def set_message_id_baggage(self, message_id: str) -> None:
        pass

    def set_thread_id(self, thread_id: str) -> None:
        pass

    def set_thread_id_baggage(self, thread_id: str) -> None:
        pass

    def set_prompt(self, prompt: Prompt) -> None:
        pass

    def set_model_provider(self, model_provider: str) -> None:
        pass

    def set_model_name(self, model_name: str) -> None:
        pass

    def set_model_call_options(self, call_options: Any) -> None:
        pass

    def set_input_tokens(self, input_tokens: int) -> None:
        pass

    def set_output_tokens(self, output_tokens: int) -> None:
        pass

    def set_start_time_first_resp(self, start_time_first_resp: int) -> None:
        pass

    def set_runtime(self, runtime: Runtime) -> None:
        pass

    def set_service_name(self, service_name: str) -> None:
        pass

    def set_log_id(self, log_id: str) -> None:
        pass

    def set_system_tags(self, system_tags: Dict[str, Any]) -> None:
        pass

    def set_deployment_env(self, deployment_env: str) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        self.finish()
