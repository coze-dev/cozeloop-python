# Copyright The OpenTelemetry Authors
# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: Apache-2.0
#
# This file has been modified by Bytedance Ltd. and/or its affiliates on 2025
#
# Original file was released under Apache-2.0, with the full license text
# available at https://github.com/open-telemetry/opentelemetry-python/blob/main/opentelemetry-sdk/src/opentelemetry/sdk/trace/export/__init__.py
#
# This modified file is released under the same license.
import threading

from cozeloop.internal.trace.exporter import *
from cozeloop.internal.trace.model.model import FinishEventInfo, QueueConf, FinishEventInfoExtra
from cozeloop.internal.trace.queue_manager import BatchQueueManager, BatchQueueManagerOptions, QUEUE_NAME_FILE_RETRY, \
    QUEUE_NAME_FILE, QUEUE_NAME_SPAN_RETRY, QUEUE_NAME_SPAN
from cozeloop.internal.trace.span import Span

DEFAULT_MAX_QUEUE_LENGTH = 1024
DEFAULT_MAX_RETRY_QUEUE_LENGTH = 512
DEFAULT_MAX_EXPORT_BATCH_LENGTH = 100
DEFAULT_MAX_EXPORT_BATCH_BYTE_SIZE = 4 * 1024 * 1024  # 4MB
MAX_RETRY_EXPORT_BATCH_LENGTH = 50
DEFAULT_SCHEDULE_DELAY = 1000  # millisecond

MAX_FILE_QUEUE_LENGTH = 512
MAX_FILE_EXPORT_BATCH_LENGTH = 1
MAX_FILE_EXPORT_BATCH_BYTE_SIZE = 100 * 1024 * 1024  # 100MB
FILE_SCHEDULE_DELAY = 5000  # millisecond

logger = logging.getLogger(__name__)


class SpanProcessor:
    def on_span_end(self, s: Span):
        raise NotImplementedError

    def shutdown(self) -> bool:
        raise NotImplementedError

    def force_flush(self) -> bool:
        raise NotImplementedError


class BatchSpanProcessor(SpanProcessor):
    def __init__(
            self,
            client,
            upload_path: UploadPath = None,
            finish_event_processor: Optional[Callable[[FinishEventInfo], None]] = None,
            queue_conf: Optional[QueueConf] = None,
    ):
        span_upload_path = PATH_INGEST_TRACE
        file_upload_path = PATH_UPLOAD_FILE
        if upload_path:
            if upload_path.span_upload_path:
                span_upload_path = upload_path.span_upload_path
            if upload_path.file_upload_path:
                file_upload_path = upload_path.file_upload_path
        self.exporter = SpanExporter(
            client,
            UploadPath(
                span_upload_path=span_upload_path,
                file_upload_path=file_upload_path,
            )
        )

        span_queue_length = DEFAULT_MAX_QUEUE_LENGTH
        span_export_batch_size = DEFAULT_MAX_EXPORT_BATCH_LENGTH
        if queue_conf:
            if queue_conf.span_queue_length > 0:
                span_queue_length = queue_conf.span_queue_length
            if queue_conf.span_max_export_batch_length > 0:  # todo: need max limit
                span_export_batch_size = queue_conf.span_max_export_batch_length

        self.file_retry_qm = BatchQueueManager(
            BatchQueueManagerOptions(
                queue_name=QUEUE_NAME_FILE_RETRY,
                batch_timeout=FILE_SCHEDULE_DELAY,
                max_queue_length=MAX_FILE_QUEUE_LENGTH,
                max_export_batch_length=MAX_FILE_EXPORT_BATCH_LENGTH,
                max_export_batch_byte_size=MAX_FILE_EXPORT_BATCH_BYTE_SIZE,
                export_func=self._new_export_files_func(self.exporter, None, finish_event_processor),
                finish_event_processor=finish_event_processor,
            )
        )

        self.file_qm = BatchQueueManager(
            BatchQueueManagerOptions(
                queue_name=QUEUE_NAME_FILE,
                batch_timeout=FILE_SCHEDULE_DELAY,
                max_queue_length=MAX_FILE_QUEUE_LENGTH,
                max_export_batch_length=MAX_FILE_EXPORT_BATCH_LENGTH,
                max_export_batch_byte_size=MAX_FILE_EXPORT_BATCH_BYTE_SIZE,
                export_func=self._new_export_files_func(self.exporter, self.file_retry_qm, finish_event_processor),
                finish_event_processor=finish_event_processor,
            )
        )

        self.span_retry_qm = BatchQueueManager(
            BatchQueueManagerOptions(
                queue_name=QUEUE_NAME_SPAN_RETRY,
                batch_timeout=DEFAULT_SCHEDULE_DELAY,
                max_queue_length=DEFAULT_MAX_RETRY_QUEUE_LENGTH,
                max_export_batch_length=MAX_RETRY_EXPORT_BATCH_LENGTH,
                max_export_batch_byte_size=DEFAULT_MAX_EXPORT_BATCH_BYTE_SIZE,
                export_func=self._new_export_spans_func(self.exporter, None, self.file_qm, finish_event_processor),
                finish_event_processor=finish_event_processor,
            )
        )

        self.span_qm = BatchQueueManager(
            BatchQueueManagerOptions(
                queue_name=QUEUE_NAME_SPAN,
                batch_timeout=DEFAULT_SCHEDULE_DELAY,
                max_queue_length=span_queue_length,
                max_export_batch_length=span_export_batch_size,
                max_export_batch_byte_size=DEFAULT_MAX_EXPORT_BATCH_BYTE_SIZE,
                export_func=self._new_export_spans_func(self.exporter, self.span_retry_qm, self.file_qm,
                                                        finish_event_processor),
                finish_event_processor=finish_event_processor,
            )
        )

        self._stopped = threading.Event()

    def on_span_end(self, s: Span):
        if self._stopped.is_set():
            return
        self.span_qm.enqueue(s, s.bytes_size)

    def shutdown(self) -> bool:
        success = True
        for qm in [self.span_qm, self.span_retry_qm, self.file_qm, self.file_retry_qm]:
            if not qm.shutdown():
                success = False
        self._stopped.set()
        return success

    def force_flush(self) -> bool:
        success = True
        for qm in [self.span_qm, self.span_retry_qm, self.file_qm, self.file_retry_qm]:
            if not qm.force_flush():
                success = False
        return success

    def _new_export_spans_func(
            self,
            exporter,
            span_retry_queue,
            file_queue,
            finish_event_processor: Optional[Callable[[FinishEventInfo], None]] = None
    ):
        def export_func(ctx: dict, items: List[Any]):
            spans = [s for s in items if isinstance(s, Span)]
            if not spans or len(spans) == 0:
                return
            try:
                upload_spans, upload_files = transfer_to_upload_span_and_file(spans)
            except Exception as e:
                logger.warning(f"transfer_to_upload_span_and_file fail, {e}")
                return

            event_err_msg = ""
            before = time.perf_counter()

            is_export_pass = True
            export_msg = ""
            try:
                exporter.export_spans(ctx, upload_spans)
            except Exception as e:
                is_export_pass = False
                export_msg = f"{e}"

            elapsed_time_ms = (time.perf_counter() - before) * 1000
            if not is_export_pass:
                if span_retry_queue:
                    for span in spans:
                        span_retry_queue.enqueue(span, span.bytes_size)
                    event_err_msg = f'{export_msg}, retry later'
                else:
                    event_err_msg = f'{export_msg}, retry second time failed'
            else:
                for file in upload_files:
                    if file and file_queue:
                        file_queue.enqueue(file, len(file.data))
            if finish_event_processor:
                finish_event_processor(FinishEventInfo(
                    event_type="exporter.span_flush.rate",
                    is_event_fail=not is_export_pass,
                    item_num=len(spans),
                    detail_msg=event_err_msg,
                    extra_params=FinishEventInfoExtra(
                        latency_ms=int(elapsed_time_ms)
                    )
                ))

        return export_func

    def _new_export_files_func(
            self,
            exporter,
            file_retry_queue,
            finish_event_processor: Optional[Callable[[FinishEventInfo], None]] = None
    ):
        def export_func(ctx: dict, items: List[Any]):
            files = [f for f in items if isinstance(f, UploadFile)]
            if not files or len(files) == 0:
                return

            event_err_msg = ""
            before = time.perf_counter()

            is_export_pass = True
            export_msg = ""
            try:
                exporter.export_files(ctx, files)
            except Exception as e:
                is_export_pass = True
                export_msg = f"{e}"

            elapsed_time_ms = (time.perf_counter() - before) * 1000
            if not is_export_pass:
                if file_retry_queue:
                    for file in files:
                        file_retry_queue.enqueue(file, len(file.data))
                    event_err_msg = f'{export_msg}, retry later'
                else:
                    event_err_msg = f'{export_msg}, retry second time failed'
            if finish_event_processor:
                finish_event_processor(FinishEventInfo(
                    event_type="exporter.file_flush.rate",
                    is_event_fail=not is_export_pass,
                    item_num=len(files),
                    detail_msg=event_err_msg,
                    extra_params=FinishEventInfoExtra(
                        latency_ms=int(elapsed_time_ms)
                    )
                ))

        return export_func
