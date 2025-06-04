# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from .entities.prompt import Prompt, Message
from .logger import set_log_level, add_log_handler

from .internal import __version__
from .internal.consts import (
    CN_BASE_URL,
)
from .internal.consts.error import *

from .client import Client
from ._client import (
    new_client,
    set_default_client,
    workspace_id,
    close,
    get_prompt,
    prompt_format,
    start_span,
    get_span_from_context,
    get_span_from_header,
    flush,
    ENV_API_BASE_URL,
    ENV_WORKSPACE_ID,
    ENV_API_TOKEN,
    ENV_JWT_OAUTH_CLIENT_ID,
    ENV_JWT_OAUTH_PRIVATE_KEY,
    ENV_JWT_OAUTH_PUBLIC_KEY_ID
)

from .span import SpanContext, Span
