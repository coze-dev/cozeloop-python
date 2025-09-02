# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from contextvars import ContextVar

from .error import *
from ...spec.tracespec.span_key import INPUT_TOKENS, OUTPUT_TOKENS, TOKENS, INPUT, OUTPUT

# default values for loop client
# ComBaseURL = "https://api.coze.com"
CN_BASE_URL = "https://api.coze.cn"
DEFAULT_OAUTH_REFRESH_TTL = 900
OAUTH_REFRESH_ADVANCE_TIME = 60
DEFAULT_PROMPT_CACHE_MAX_COUNT = 100
DEFAULT_PROMPT_CACHE_REFRESH_INTERVAL = 60
DEFAULT_TIMEOUT = 3
DEFAULT_UPLOAD_TIMEOUT = 30

LOG_ID_HEADER = "x-tt-logid"
AUTHORIZE_HEADER = "Authorization"

# Define various boundary size.
MAX_TAG_KV_COUNT_IN_ONE_SPAN = 50

MAX_BYTES_OF_ONE_TAG_VALUE_OF_INPUT_OUTPUT = 1 * 1024 * 1024
TEXT_TRUNCATE_CHAR_LENGTH             = 1000

MAX_BYTES_OF_ONE_TAG_VALUE_DEFAULT = 1024
MAX_BYTES_OF_ONE_TAG_KEY_DEFAULT = 1024

STATUS_CODE_ERROR_DEFAULT = -1

GLOBAL_TRACE_VERSION = 0


# System reserved tag fields.
USER_ID = "user_id"
MESSAGE_ID = "message_id"
THREAD_ID = "thread_id"
START_TIME_FIRST_RESP = "start_time_first_resp"
LATENCY_FIRST_RESP = "latency_first_resp"
DEPLOYMENT_ENV = "deployment_env"
CUT_OFF = "cut_off"

# ReserveFieldTypes Define the allowed types for each reserved field.
RESERVE_FIELD_TYPES = {
    USER_ID: [str],
    MESSAGE_ID: [str],
    THREAD_ID: [str],
    INPUT_TOKENS: [int],
    OUTPUT_TOKENS: [int],
    TOKENS: [int],
    START_TIME_FIRST_RESP: [int],
    LATENCY_FIRST_RESP: [int]
}

MODEL_MESSAGE_PART_TYPE_TEXT = "text"
MODEL_MESSAGE_PART_TYPE_IMAGE = "image"
MODEL_MESSAGE_PART_TYPE_FILE = "file"

EQUAL = "="
COMMA = ","

# On the basis of W3C, the "loop" prefix is added to avoid conflicts with other traces that use W3C.
TRACE_CONTEXT_HEADER_PARENT = "X-Cozeloop-Traceparent"
TRACE_CONTEXT_HEADER_BAGGAGE = "X-Cozeloop-Tracestate"

TRACE_PROMPT_HUB_SPAN_TYPE = "prompt_hub"
TRACE_PROMPT_TEMPLATE_SPAN_TYPE = "prompt"

TRACE_PROMPT_HUB_SPAN_NAME = "PromptHub"
TRACE_PROMPT_TEMPLATE_SPAN_NAME = "PromptTemplate"

PROMPT_NORMAL_TEMPLATE_START_TAG = "{{"
PROMPT_NORMAL_TEMPLATE_END_TAG = "}}"


# Span key
# Common tags for all span types.
# SPAN_TYPE = "span_type"
# INPUT = "input"
# OUTPUT = "output"
# ERROR = "error"
# RUNTIME = "runtime"
# STATUS_CODE = "_status_code"
# CALL_OPTIONS = "call_options"

# Tags for entity-type span.
# MODEL_PROVIDER = "model_provider"
# MODEL_NAME = "model_name"
# INPUT_TOKENS = "input_tokens"
# OUTPUT_TOKENS = "output_tokens"
# TOKENS = "tokens"
# LATENCY_FIRST_RESP = "latency_first_resp"
# STREAM = "stream"
# TOKEN_USAGE_BACKUP = "token_usage_backup"
# MODEL_PLATFORM = "model_platform"
# MODEL_IDENTIFICATION = "model_identification"
# REASONING_TOKENS = "reasoning_tokens"
# REASONING_DURATION = "reasoning_duration"

# Tags for retriever-type span
# RETRIEVER_PROVIDER = "retriever_provider"
# VIKING_DB_NAME = "vikingdb_name"
# VIKING_DB_REGION = "vikingdb_region"
# ES_NAME = "es_name"
# ES_INDEX = "es_index"
# ES_CLUSTER = "es_cluster"

# Tags for prompt-type span.
# PROMPT_PROVIDER = "prompt_provider"
# PROMPT_KEY = "prompt_key"
# PROMPT_VERSION = "prompt_version"


TAG_VALUE_SIZE_LIMIT = {
    INPUT: MAX_BYTES_OF_ONE_TAG_VALUE_OF_INPUT_OUTPUT,
    OUTPUT: MAX_BYTES_OF_ONE_TAG_VALUE_OF_INPUT_OUTPUT,
}

BAGGAGE_SPECIAL_CHARS = {"=", ","}
