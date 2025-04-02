# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import platform as platform_pkg
import importlib.metadata as metadata
from typing import Optional
from pydantic.dataclasses import dataclass

from cozeloop.internal.version import VERSION

@dataclass
class RuntimeInfo:
    language: Optional[str] = 'python'
    library: Optional[str] = 'langchain'
    runtime: Optional[str] = 'python'
    runtime_version: Optional[str] = platform_pkg.python_version()
    py_implementation: Optional[str] = platform_pkg.python_implementation()
    loop_sdk_version: Optional[str] = None
    langchain_version: Optional[str] = None
    langchain_core_version: Optional[str] = None

    def __post_init__(self):
        try:
            langchain_version = metadata.version('langchain')
        except metadata.PackageNotFoundError:
            langchain_version = ''
        try:
            langchain_core_version = metadata.version('langchain-core')
        except metadata.PackageNotFoundError:
            langchain_core_version = ''
        self.loop_sdk_version = VERSION
        self.langchain_version = langchain_version
        self.langchain_core_version = langchain_core_version

    def to_json(self):
        return json.dumps(
            self,
            default=lambda o: o.__dict__,
            sort_keys=False,
            ensure_ascii=False)
