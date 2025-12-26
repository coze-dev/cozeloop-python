# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import importlib.metadata as metadata
from typing import Optional, Any

from cozeloop.spec import tracespec

LANGCHAIN_VERSION = ''
LANGCHAIN_CORE_VERSION = ''
try:
    LANGCHAIN_VERSION = metadata.version('langchain')
except metadata.PackageNotFoundError:
    LANGCHAIN_VERSION = ''
try:
    LANGCHAIN_CORE_VERSION = metadata.version('langchain-core')
except metadata.PackageNotFoundError:
    LANGCHAIN_CORE_VERSION = ''


class RuntimeInfo(tracespec.Runtime):
    language: Optional[str] = tracespec.V_LANG_PYTHON
    library: Optional[str] = tracespec.V_LIB_LANGCHAIN

    def model_post_init(self, context: Any) -> None:
        self.library_version = LANGCHAIN_VERSION
        self.extra = {'langchain_core_version': LANGCHAIN_CORE_VERSION}

    def to_json(self):
        return json.dumps(
            self,
            default=lambda o: o.__dict__,
            sort_keys=False,
            ensure_ascii=False)
