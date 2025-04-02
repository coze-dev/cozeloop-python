# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import Optional
from pydantic import BaseModel

class Runtime(BaseModel):
    language: Optional[str] = None # from enum VLang in span_value.go
    library: Optional[str] = None  # integration library, from enum VLib in span_value.go
    scene: Optional[str] = None  # usage scene, from enum VScene in span_value.go

    # Dependency Versions.
    library_version: Optional[str] = None
    loop_sdk_version: Optional[str] = None