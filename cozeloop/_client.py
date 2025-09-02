# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import atexit
import hashlib
import logging
import os
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

import httpx

from cozeloop.client import Client
from cozeloop._noop import NOOP_SPAN, _NoopClient
from cozeloop.entities.prompt import Prompt, Message, PromptVariable
from cozeloop.internal import consts, httpclient
from cozeloop.internal.consts import ClientClosedError
from cozeloop.internal.httpclient import Auth
from cozeloop.internal.prompt import PromptProvider
from cozeloop.internal.trace import TraceProvider
from cozeloop.internal.trace.model.model import FinishEventInfo, TagTruncateConf, QueueConf
from cozeloop.internal.trace.trace import default_finish_event_processor
from cozeloop.span import SpanContext, Span

logger = logging.getLogger(__name__)

# environment keys for loop client
ENV_API_BASE_URL = "COZELOOP_API_BASE_URL"
ENV_WORKSPACE_ID = "COZELOOP_WORKSPACE_ID"
ENV_API_TOKEN = "COZELOOP_API_TOKEN"
ENV_JWT_OAUTH_CLIENT_ID = "COZELOOP_JWT_OAUTH_CLIENT_ID"
ENV_JWT_OAUTH_PRIVATE_KEY = "COZELOOP_JWT_OAUTH_PRIVATE_KEY"
ENV_JWT_OAUTH_PUBLIC_KEY_ID = "COZELOOP_JWT_OAUTH_PUBLIC_KEY_ID"

_client_cache = {}
_cache_lock = threading.Lock()

_default_client = None
_client_lock = threading.Lock()


class APIBasePath:
    def __init__(
            self,
            trace_span_upload_path: str = None,
            trace_file_upload_path: str = None,
    ):
        self.trace_span_upload_path = trace_span_upload_path
        self.trace_file_upload_path = trace_file_upload_path


def _generate_cache_key(*args) -> str:
    key_str = "\t".join(str(arg) for arg in args)
    return hashlib.md5(key_str.encode('utf-8')).hexdigest()


def new_client(
        api_base_url: str = "",
        workspace_id: str = "",
        api_token: str = "",
        jwt_oauth_client_id: str = "",
        jwt_oauth_private_key: str = "",
        jwt_oauth_public_key_id: str = "",
        timeout: int = consts.DEFAULT_TIMEOUT,
        upload_timeout: int = consts.DEFAULT_UPLOAD_TIMEOUT,
        ultra_large_report: bool = False,
        prompt_cache_max_count: int = consts.DEFAULT_PROMPT_CACHE_MAX_COUNT,
        prompt_cache_refresh_interval: int = consts.DEFAULT_PROMPT_CACHE_REFRESH_INTERVAL,
        prompt_trace: bool = False,
        http_client: Optional[httpx.Client] = None,
        trace_finish_event_processor: Optional[Callable[[FinishEventInfo], None]] = None,
        tag_truncate_conf: Optional[TagTruncateConf] = None,
        api_base_path: Optional[APIBasePath] = None,
        trace_queue_conf: Optional[QueueConf] = None,
) -> Client:
    cache_key = _generate_cache_key(  # all args are used to generate cache key
        api_base_url,
        workspace_id,
        api_token,
        jwt_oauth_client_id,
        jwt_oauth_private_key,
        jwt_oauth_public_key_id,
        timeout,
        upload_timeout,
        ultra_large_report,
        prompt_cache_max_count,
        prompt_cache_refresh_interval,
        prompt_trace,
        http_client,
        trace_finish_event_processor,
        tag_truncate_conf,
        api_base_path,
        trace_queue_conf,
    )

    with _cache_lock:
        if cache_key in _client_cache:
            logger.warning("You shouldn't creating a client with same options repeatedly, " +
                           "return the cached client instead.")
            return _client_cache[cache_key]
        client = _LoopClient(
            api_base_url=api_base_url,
            workspace_id=workspace_id,
            api_token=api_token,
            jwt_oauth_client_id=jwt_oauth_client_id,
            jwt_oauth_private_key=jwt_oauth_private_key,
            jwt_oauth_public_key_id=jwt_oauth_public_key_id,
            timeout=timeout,
            upload_timeout=upload_timeout,
            ultra_large_report=ultra_large_report,
            prompt_cache_max_count=prompt_cache_max_count,
            prompt_cache_refresh_interval=prompt_cache_refresh_interval,
            prompt_trace=prompt_trace,
            arg_http_client=http_client,
            trace_finish_event_processor=trace_finish_event_processor,
            tag_truncate_conf=tag_truncate_conf,
            api_base_path=api_base_path,
            trace_queue_conf=trace_queue_conf,
        )
        _client_cache[cache_key] = client
        return client


class _LoopClient(Client):
    _workspace_id: str
    _trace_provider: TraceProvider
    _prompt_provider: PromptProvider

    _closed: bool = False

    def __init__(
            self,
            api_base_url: str = "",
            workspace_id: str = "",
            api_token: str = "",
            jwt_oauth_client_id: str = "",
            jwt_oauth_private_key: str = "",
            jwt_oauth_public_key_id: str = "",
            timeout: int = consts.DEFAULT_TIMEOUT,
            upload_timeout: int = consts.DEFAULT_UPLOAD_TIMEOUT,
            ultra_large_report: bool = False,
            prompt_cache_max_count: int = consts.DEFAULT_PROMPT_CACHE_MAX_COUNT,
            prompt_cache_refresh_interval: int = consts.DEFAULT_PROMPT_CACHE_REFRESH_INTERVAL,
            prompt_trace: bool = False,
            arg_http_client: Optional[httpx.Client] = None,
            trace_finish_event_processor: Optional[Callable[[FinishEventInfo], None]] = None,
            tag_truncate_conf: Optional[TagTruncateConf] = None,
            api_base_path: Optional[APIBasePath] = None,
            trace_queue_conf: Optional[QueueConf] = None,
    ):
        workspace_id = self._get_from_env(workspace_id, ENV_WORKSPACE_ID)
        api_base_url = self._get_from_env(api_base_url, ENV_API_BASE_URL)
        api_token = self._get_from_env(api_token, ENV_API_TOKEN)
        jwt_oauth_client_id = self._get_from_env(jwt_oauth_client_id, ENV_JWT_OAUTH_CLIENT_ID)
        jwt_oauth_private_key = self._get_from_env(jwt_oauth_private_key, ENV_JWT_OAUTH_PRIVATE_KEY)
        jwt_oauth_public_key_id = self._get_from_env(jwt_oauth_public_key_id, ENV_JWT_OAUTH_PUBLIC_KEY_ID)

        api_base_url = consts.CN_BASE_URL if not api_base_url else api_base_url
        api_base_url = api_base_url.strip().rstrip("/")

        if not api_base_url:
            raise consts.InvalidParamError("api_base_url is required.")
        if not workspace_id:
            raise consts.InvalidParamError("workspace_id is required.")
        if prompt_cache_max_count <= 0:
            prompt_cache_max_count = consts.DEFAULT_PROMPT_CACHE_MAX_COUNT
        if prompt_cache_refresh_interval <= 0:
            prompt_cache_refresh_interval = consts.DEFAULT_PROMPT_CACHE_REFRESH_INTERVAL

        self._workspace_id = workspace_id
        inner_client = httpclient.HTTPClient()
        if arg_http_client:
            inner_client = arg_http_client
        auth = self._build_auth(
            api_base_url=api_base_url,
            http_client=inner_client,
            api_token=api_token,
            jwt_oauth_client_id=jwt_oauth_client_id,
            jwt_oauth_private_key=jwt_oauth_private_key,
            jwt_oauth_public_key_id=jwt_oauth_public_key_id
        )
        http_client = httpclient.Client(
            api_base_url=api_base_url,
            http_client=inner_client,
            auth=auth,
            timeout=timeout,
            upload_timeout=upload_timeout
        )
        finish_pro = default_finish_event_processor
        if trace_finish_event_processor:
            def combined_processor(event_info: FinishEventInfo):
                default_finish_event_processor(event_info)
                trace_finish_event_processor(event_info)

            finish_pro = combined_processor
        span_upload_path = None
        file_upload_path = None
        if api_base_path:
            span_upload_path = api_base_path.trace_span_upload_path
            file_upload_path = api_base_path.trace_file_upload_path
        self._trace_provider = TraceProvider(
            http_client=http_client,
            workspace_id=workspace_id,
            ultra_large_report=ultra_large_report,
            finish_event_processor=finish_pro,
            tag_truncate_conf=tag_truncate_conf,
            span_upload_path=span_upload_path,
            file_upload_path=file_upload_path,
            queue_conf=trace_queue_conf,
        )
        self._prompt_provider = PromptProvider(
            workspace_id=workspace_id,
            http_client=http_client,
            trace_provider=self._trace_provider,
            prompt_cache_max_count=prompt_cache_max_count,
            prompt_cache_refresh_interval=prompt_cache_refresh_interval,
            prompt_trace=prompt_trace
        )

    def _get_from_env(self, val: str, env_key: str) -> str:
        if val:
            return val
        env_val = os.environ.get(env_key)
        if env_val:
            return env_val
        else:
            return ""

    def _build_auth(
            self,
            api_base_url: str,
            http_client: httpclient.HTTPClient,
            api_token: str,
            jwt_oauth_client_id: str,
            jwt_oauth_private_key: str,
            jwt_oauth_public_key_id: str
    ) -> Auth:
        if jwt_oauth_client_id and jwt_oauth_private_key and jwt_oauth_public_key_id:
            return httpclient.JWTAuth(
                client_id=jwt_oauth_client_id,
                private_key=jwt_oauth_private_key,
                public_key_id=jwt_oauth_public_key_id,
                base_url=api_base_url,
                http_client=http_client
            )
        if api_token:
            return httpclient.TokenAuth(api_token)
        raise consts.AuthInfoRequiredError

    def workspace_id(self) -> str:
        # Return the space ID
        return self._workspace_id

    def close(self):
        if self._closed:
            return
        # Perform cleanup by flushing and closing the trace client
        self._trace_provider.close_trace()
        self._closed = True

    def get_prompt(self, prompt_key: str, version: str = '', label: str = '') -> Optional[Prompt]:
        if self._closed:
            raise ClientClosedError()
        return self._prompt_provider.get_prompt(prompt_key, version, label)

    def prompt_format(self, prompt: Prompt, variables: Dict[str, PromptVariable]) -> List[Message]:
        if self._closed:
            raise ClientClosedError()
        return self._prompt_provider.prompt_format(prompt, variables)

    def start_span(
            self,
            name: str,
            span_type: str,
            *,
            start_time: Optional[datetime] = None,
            child_of: Optional[SpanContext] = None,
            start_new_trace: bool = False,
    ) -> Span:
        if self._closed:
            return NOOP_SPAN
        try:
            if child_of is None:
                return self._trace_provider.start_span(name=name, span_type=span_type, start_time=start_time,
                                                       start_new_trace=start_new_trace)
            else:
                baggage = {}
                if isinstance(child_of.baggage, dict):  # SpanContext
                    baggage = child_of.baggage
                else:
                    baggage = child_of.baggage()  # Span
                return self._trace_provider.start_span(name=name, span_type=span_type, start_time=start_time,
                                                       parent_span_id=child_of.span_id, trace_id=child_of.trace_id,
                                                       baggage=baggage, start_new_trace=start_new_trace)
        except Exception as e:
            logger.warning(f"Start span failed, returning noop span. Error: {e}")
            return NOOP_SPAN

    def get_span_from_context(self) -> Span:
        if self._closed:
            return NOOP_SPAN
        span = self._trace_provider.get_span_from_context()
        if span is None:
            return NOOP_SPAN
        return span

    def get_span_from_header(self, header: dict) -> SpanContext:
        if self._closed:
            return NOOP_SPAN
        return self._trace_provider.get_span_from_header(header)

    def flush(self):
        if self._closed:
            return
        self._trace_provider.flush()


def set_default_client(client: Client):
    global _default_client
    with _client_lock:
        if _default_client:
            temp_client = _default_client
            _default_client = client
            if temp_client != client:
                temp_client.close()
        else:
            _default_client = client


def get_default_client() -> Client:
    global _default_client
    if _default_client is None:
        with _client_lock:
            if _default_client is None:
                try:
                    _default_client = new_client()
                    atexit.register(_graceful_shutdown)
                except Exception as e:
                    new_exception = e
                    _default_client = _NoopClient(new_exception)
    return _default_client


def _graceful_shutdown():
    global _default_client
    with _client_lock:
        if _default_client is not None:
            logger.info("Starting graceful shutdown...")
            _default_client.close()
            _default_client = _NoopClient(ClientClosedError())
            logger.info("Graceful shutdown finished.")


def workspace_id() -> str:
    return get_default_client().workspace_id


def close():
    return get_default_client().close()


def get_prompt(prompt_key: str, version: str = '', label: str = '') -> Prompt:
    return get_default_client().get_prompt(prompt_key, version, label)


def prompt_format(prompt: Prompt, variables: Dict[str, Any]) -> List[Message]:
    return get_default_client().prompt_format(prompt, variables)


def start_span(name: str, span_type: str, *, start_time: Optional[int] = None,
               child_of: Optional[SpanContext] = None) -> Span:
    return get_default_client().start_span(name, span_type, start_time=start_time, child_of=child_of)


def get_span_from_context() -> Span:
    return get_default_client().get_span_from_context()


def get_span_from_header(header: Dict[str, str]) -> SpanContext:
    return get_default_client().get_span_from_header(header)


def flush() -> None:
    return get_default_client().flush()
