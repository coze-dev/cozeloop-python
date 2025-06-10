# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import importlib.metadata as metadata
from typing import Optional, Any

from cozeloop.spec import tracespec


class RuntimeInfo(tracespec.Runtime):
    language: Optional[str] = tracespec.V_LANG_PYTHON
    library: Optional[str] = tracespec.V_LIB_LANGCHAIN

    def model_post_init(self, context: Any) -> None:
        try:
            langchain_version = metadata.version('langchain')
        except metadata.PackageNotFoundError:
            langchain_version = ''

        self.library_version = langchain_version

    def to_json(self):
        return json.dumps(
            self,
            default=lambda o: o.__dict__,
            sort_keys=False,
            ensure_ascii=False)
