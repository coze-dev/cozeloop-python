# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
import logging
import time
from datetime import datetime
from typing import Dict, Optional, Callable

from cozeloop.internal.trace.exporter import UploadPath
from cozeloop.internal.trace.model.model import FinishEventInfo, TagTruncateConf, QueueConf
from cozeloop.spec.tracespec import Runtime, RUNTIME_
from cozeloop.internal import consts
from cozeloop.internal.trace.span import from_header, Span, SpanContext, \
    get_newest_span_from_context, set_span_to_context, logger
from cozeloop.internal.trace.span_processor import BatchSpanProcessor, SpanProcessor
from cozeloop.internal.utils.get import gen_16char_id, gen_32char_id

logger = logging.getLogger(__name__)

class TraceOptions:
    def __init__(self, workspace_id: str, ultra_large_report: bool = False):
        self.workspace_id = workspace_id
        self.ultra_large_report = ultra_large_report


class StartSpanOptions:
    def __init__(self):
        self.start_time: Optional[datetime] = None
        self.parent_span_id: Optional[str] = None
        self.trace_id: Optional[str] = None
        self.baggage: Dict[str, str] = {}


class TraceProvider:
    def __init__(
            self,
            http_client,
            workspace_id: str,
            *,
            ultra_large_report: bool = False,
            finish_event_processor: Optional[Callable[[FinishEventInfo], None]] = None,
            tag_truncate_conf: Optional[TagTruncateConf] = None,
            span_upload_path: str = None,
            file_upload_path: str = None,
            queue_conf: Optional[QueueConf] = None,
    ):
        self.workspace_id = workspace_id
        self.ultra_large_report = ultra_large_report
        upload_path = None
        if span_upload_path or file_upload_path:
            upload_path = UploadPath(
                span_upload_path=span_upload_path,
                file_upload_path=file_upload_path,
            )
        self.span_processor: SpanProcessor = BatchSpanProcessor(
            http_client,
            upload_path,
            finish_event_processor,
            queue_conf,
        )
        self.tag_truncate_conf = tag_truncate_conf

    def start_span(
            self,
            name: str,
            span_type: str,
            start_time: datetime = None,
            parent_span_id: str = None,
            trace_id: str = None,
            baggage: Dict[str, str] = None,
            start_new_trace: bool = False,
            scene: str = ''
    ) -> Span:
        if name == '':
            name = 'unknown'
        if span_type == '':
            span_type = 'unknown'
        if len(name) > consts.MAX_BYTES_OF_ONE_TAG_VALUE_DEFAULT:
            logger.warning(
                f"Name is too long, will be truncated to {consts.MAX_BYTES_OF_ONE_TAG_VALUE_DEFAULT} bytes, original name: {name}"
            )
            name = name[:consts.MAX_BYTES_OF_ONE_TAG_VALUE_DEFAULT]
        if len(span_type) > consts.MAX_BYTES_OF_ONE_TAG_VALUE_DEFAULT:
            logger.warning(
                f"Name is too long, will be truncated to {consts.MAX_BYTES_OF_ONE_TAG_VALUE_DEFAULT} bytes, original name: {name}"
            )
            span_type = span_type[:consts.MAX_BYTES_OF_ONE_TAG_VALUE_DEFAULT]

        # Prioritize using the data from param, and fall back to parent_span
        parent_span = self.get_span_from_context()
        if parent_span and not start_new_trace:
            if trace_id is None:
                trace_id = parent_span.trace_id
            if parent_span_id is None:
                parent_span_id = parent_span.span_id
            if baggage is None:
                baggage = parent_span.baggage()

        loop_span = self._start_span(name, span_type, start_time, parent_span_id, trace_id, baggage, scene)
        set_span_to_context(loop_span)

        return loop_span

    def get_span_from_context(self) -> Span:
        return get_newest_span_from_context()

    def get_span_from_header(self, header: Dict[str, str]) -> SpanContext:
        return from_header(header)

    def _start_span(self,
                    span_name: str,
                    span_type: str,
                    start_time: datetime = None,
                    parent_span_id: str = None,
                    trace_id: str = None,
                    baggage: Dict[str, str] = None,
                    scene: str = ''
                    ) -> Span:

        parent_id = parent_span_id if parent_span_id else "0"
        trace_id = trace_id if trace_id else gen_32char_id()
        start_time = start_time if start_time else datetime.now()

        system_tag_map = {}
        if scene:
            system_tag_map[RUNTIME_] = Runtime(scene=scene)

        span = Span(
            span_type=span_type,
            name=span_name,
            space_id=self.workspace_id,
            trace_id=trace_id,
            span_id=str(gen_16char_id())[:16],
            parent_span_id=parent_id,
            baggage={},
            start_time=start_time,
            duration=0,
            tag_map={},
            system_tag_map=system_tag_map,
            status_code=0,
            ultra_large_report=self.ultra_large_report,
            multi_modality_key_map={},
            span_processor=self.span_processor,
            flags=1,     # default sampled
            is_finished=0,
            tag_truncate_conf=self.tag_truncate_conf,
        )

        span.set_baggage_escape(baggage, False)
        return span

    def flush(self):
        self.span_processor.force_flush()

    def close_trace(self):
        self.span_processor.shutdown()


def default_finish_event_processor(info: FinishEventInfo):
    if info is None:
        return
    if info.is_event_fail:
        logger.error(f"[fornax_sdk] finish_event[{info.event_type}] fail, msg: {info.detail_msg}")
    else:
        logger.debug(f"[fornax_sdk] finish_event[{info.event_type}] success, item num: {info.item_num}, msg: {info.detail_msg}")