# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

# Tags for model-type span.
CALL_OPTIONS = "call_options" # Used to identify option for model, like temperature, etc. Recommend use ModelCallOption class.
STREAM = "stream"             # Used to identify whether it is a streaming output.
REASONING_TOKENS = "reasoning_tokens"   # The token usage during the reasoning process.
REASONING_DURATION = "reasoning_duration" # The duration during the reasoning process, unit: microseconds.

# Tags for retriever-type span
RETRIEVER_PROVIDER = "retriever_provider" # Data retrieval providers, such as Elasticsearch (ES), VikingDB, etc.
VIKINGDB_NAME = "vikingdb_name"      # When using VikingDB to provide retrieval capabilities, db name.
VIKINGDB_REGION = "vikingdb_region"    # When using VikingDB to provide retrieval capabilities, db region.
ES_NAME = "es_name"            # When using ES to provide retrieval capabilities, es name.
ES_INDEX = "es_index"           # When using ES to provide retrieval capabilities, es index.
ES_CLUSTER = "es_cluster"         # When using ES to provide retrieval capabilities, es cluster.

# Tags for prompt-type span.
PROMPT_PROVIDER = "prompt_provider" # Prompt providers, such as Loop, Langsmith, etc.
PROMPT_KEY = "prompt_key"
PROMPT_VERSION = "prompt_version"
PROMPT_LABEL = "prompt_label"

# Internal experimental field.
# It is not recommended to use for the time being. Instead, use the corresponding Set method.
SPAN_TYPE = "span_type"
INPUT = "input"
OUTPUT = "output"
ERROR = "error"
RUNTIME_ = "runtime"

MODEL_PROVIDER = "model_provider"
MODEL_NAME = "model_name"
INPUT_TOKENS = "input_tokens"
OUTPUT_TOKENS = "output_tokens"
TOKENS = "tokens"
MODEL_PLATFORM = "model_platform"
MODEL_IDENTIFICATION = "model_identification"
TOKEN_USAGE_BACKUP = "token_usage_backup"