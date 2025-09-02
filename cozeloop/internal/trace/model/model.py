# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from enum import Enum

from pydantic import BaseModel
from typing import List, Optional, Literal
from pydantic.dataclasses import dataclass


class Attachment(BaseModel):
    field: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None  # text, image, file
    tos_key: Optional[str] = None


class ObjectStorage(BaseModel):
    input_tos_key: Optional[str] = None  # The key for reporting long input data
    output_tos_key: Optional[str] = None  # The key for reporting long output data
    attachments: List['Attachment'] = None  # attachments in input or output


class UploadType(str, Enum):
    LONG = 1
    MULTI_MODALITY = 2


SpanFinishEvent = Literal[
    "queue_manager.span_entry.rate",
    "queue_manager.file_entry.rate",
    "exporter.span_flush.rate",
    "exporter.file_flush.rate"
]


@dataclass
class FinishEventInfoExtra:
    is_root_span: bool = False
    latency_ms: int = 0


@dataclass
class FinishEventInfo:
    event_type: SpanFinishEvent
    is_event_fail: bool
    item_num: int  # maybe multiple span is processed in one event
    detail_msg: str
    extra_params: Optional[FinishEventInfoExtra] = None


class TagTruncateConf:
    def __init__(
            self,
            normal_field_max_byte: int,
            input_output_field_max_byte: int,
    ):
        self.normal_field_max_byte = normal_field_max_byte
        self.input_output_field_max_byte = input_output_field_max_byte


class QueueConf:
    def __init__(
            self,
            span_queue_length: int,
            span_max_export_batch_length: int,
    ):
        self.span_queue_length = span_queue_length
        self.span_max_export_batch_length = span_max_export_batch_length
