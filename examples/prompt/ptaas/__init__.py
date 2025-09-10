# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
PTaaS (Prompt Template as a Service) 示例

本包包含了PTaaS功能的各种使用示例，包括：
- 基础示例：同步非流式、异步非流式、异步流式调用
- 高级示例：占位符变量、标签使用、Jinja2模板、超时控制、多模态处理
"""

__all__ = [
    "ptaas",
    "ptaas_placeholder_variable", 
    "ptaas_with_label",
    "ptaas_jinja",
    "ptaas_timeout",
    "ptaas_multimodal"
]