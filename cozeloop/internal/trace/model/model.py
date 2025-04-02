# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from enum import Enum

from pydantic import BaseModel
from typing import List, Optional


class ObjectStorage(BaseModel):
    input_tos_key: Optional[str] = None  # The key for reporting long input data
    output_tos_key: Optional[str] = None  # The key for reporting long output data
    attachments: List['Attachment'] = None  # attachments in input or output


class Attachment(BaseModel):
    field: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None  # text, image, file
    tos_key: Optional[str] = None


class UploadType(str, Enum):
    LONG = 1
    MULTI_MODALITY = 2
