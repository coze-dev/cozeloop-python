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
from cozeloop.internal.trace.queue_manager import BatchQueueManager, BatchQueueManagerOptions
from cozeloop.internal.trace.span import Span

DEFAULT_MAX_QUEUE_LENGTH = 2048
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
    def __init__(self, client):
        self.exporter = SpanExporter(client)

        self.file_retry_qm = BatchQueueManager(
            BatchQueueManagerOptions(
                queue_name='file_retry',
                batch_timeout=FILE_SCHEDULE_DELAY,
                max_queue_length=MAX_FILE_QUEUE_LENGTH,
                max_export_batch_length=MAX_FILE_EXPORT_BATCH_LENGTH,
                max_export_batch_byte_size=MAX_FILE_EXPORT_BATCH_BYTE_SIZE,
                export_func=self._new_export_files_func(self.exporter, None)
            )
        )

        self.file_qm = BatchQueueManager(
            BatchQueueManagerOptions(
                queue_name='file',
                batch_timeout=FILE_SCHEDULE_DELAY,
                max_queue_length=MAX_FILE_QUEUE_LENGTH,
                max_export_batch_length=MAX_FILE_EXPORT_BATCH_LENGTH,
                max_export_batch_byte_size=MAX_FILE_EXPORT_BATCH_BYTE_SIZE,
                export_func=self._new_export_files_func(self.exporter, self.file_retry_qm)
            )
        )

        self.span_retry_qm = BatchQueueManager(
            BatchQueueManagerOptions(
                queue_name='span_retry',
                batch_timeout=DEFAULT_SCHEDULE_DELAY,
                max_queue_length=DEFAULT_MAX_QUEUE_LENGTH,
                max_export_batch_length=MAX_RETRY_EXPORT_BATCH_LENGTH,
                max_export_batch_byte_size=DEFAULT_MAX_EXPORT_BATCH_BYTE_SIZE,
                export_func=self._new_export_spans_func(self.exporter, None, self.file_qm)
            )
        )

        self.span_qm = BatchQueueManager(
            BatchQueueManagerOptions(
                queue_name='span',
                batch_timeout=DEFAULT_SCHEDULE_DELAY,
                max_queue_length=DEFAULT_MAX_QUEUE_LENGTH,
                max_export_batch_length=DEFAULT_MAX_EXPORT_BATCH_LENGTH,
                max_export_batch_byte_size=DEFAULT_MAX_EXPORT_BATCH_BYTE_SIZE,
                export_func=self._new_export_spans_func(self.exporter, self.span_retry_qm, self.file_qm)
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

    def _new_export_spans_func(self, exporter, span_retry_queue, file_queue):
        def export_func(ctx: dict, items: List[Any]):
            spans = [s for s in items if isinstance(s, Span)]
            try:
                upload_spans, upload_files = transfer_to_upload_span_and_file(spans)
                logger.debug(f"upload_spans len[{len(upload_spans)}], upload_files len[{len(upload_files)}]")
            except Exception as e:
                logger.warning(f"transfer_to_upload_span_and_file fail")

            if not exporter.export_spans(ctx, upload_spans):
                if span_retry_queue:
                    for span in spans:
                        span_retry_queue.enqueue(span, span.bytes_size)
            else:
                for file in upload_files:
                    if file and file_queue:
                        file_queue.enqueue(file, len(file.data))

        return export_func

    def _new_export_files_func(self, exporter, file_retry_queue):
        def export_func(ctx: dict, items: List[Any]):
            files = [f for f in items if isinstance(f, UploadFile)]

            if not exporter.export_files(ctx, files):
                logger.warning(f" export_files fail")
                if file_retry_queue:
                    for file in files:
                        file_retry_queue.enqueue(file, len(file.data))

        return export_func