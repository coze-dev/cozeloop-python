# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

# SpanType tag builtin values
V_PROMPT_HUB_SPAN_TYPE = "prompt"
V_PROMPT_SPAN_TYPE = "prompt"
V_MODEL_SPAN_TYPE = "model"
V_RETRIEVER_SPAN_TYPE = "retriever"
V_TOOL_SPAN_TYPE = "tool"

V_ERR_DEFAULT = -1  # Default StatusCode for errors.

# Tag values for model messages.
V_ROLE_USER = "user"
V_ROLE_SYSTEM = "system"
V_ROLE_ASSISTANT = "assistant"
V_ROLE_TOOL = "tool"

# VToolChoiceNone Reference: https://platform.openai.com/docs/api-reference/chat/create#chat-create-messages
V_TOOL_CHOICE_NONE = "none"     # Means the model will not call any tool and instead generates a message.
V_TOOL_CHOICE_AUTO = "auto"     # Means the model can pick between generating a message or calling one or more tools.
V_TOOL_CHOICE_REQUIRED = "required"  # Means the model must call one or more tools.
V_TOOL_CHOICE_FUNCTION = "function"  # Forces the model to call that tool.

# Tag values for runtime tags.
V_LANG_GO = "go"
V_LANG_PYTHON = "python"
V_LANG_TYPESCRIPT = "ts"

V_LIB_EINO = "eino"
V_LIB_LANGCHAIN = "langchain"

V_SCENE_CUSTOM = "custom"          # user custom, it has the same meaning as blank.
V_SCENE_PROMPT_HUB = "prompt_hub"      # get_prompt
V_SCENE_PROMPT_TEMPLATE = "prompt_template"  # prompt_template
V_SCENE_INTEGRATION = "integration"   # integration like langchain

# Tag values for prompt input.
V_PROMPT_ARG_SOURCE_INPUT = "input"
V_PROMPT_ARG_SOURCE_PARTIAL = "partial"