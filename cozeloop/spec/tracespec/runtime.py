# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import Optional
from pydantic import BaseModel


class Runtime(BaseModel):
    language: Optional[str] = None # from enum VLang in span_value.py
    library: Optional[str] = None  # integration library, from enum VLib in span_value.py
    scene: Optional[str] = None  # usage scene, from enum VScene in span_value.py

    # Dependency Versions.
    library_version: Optional[str] = None
    loop_sdk_version: Optional[str] = None

    #   Extra info.
    extra: Optional[dict] = None