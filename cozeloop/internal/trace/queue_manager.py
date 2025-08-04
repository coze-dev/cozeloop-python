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

import logging
import queue
import threading
from typing import Any, Callable, List, Optional
from queue import Queue

from pydantic import BaseModel

from cozeloop.internal.trace.model.model import FinishEventInfo, FinishEventInfoExtra

logger = logging.getLogger(__name__)

QUEUE_NAME_SPAN = "span"
QUEUE_NAME_SPAN_RETRY = "span_retry"
QUEUE_NAME_FILE = "file"
QUEUE_NAME_FILE_RETRY = "file_retry"

class QueueManager:
    def enqueue(self, s: Any, byte_size: int):
        raise NotImplementedError

    def shutdown(self) -> bool:
        raise NotImplementedError

    def force_flush(self) -> bool:
        raise NotImplementedError


class BatchQueueManagerOptions(BaseModel):
    queue_name: str
    max_queue_length: int
    batch_timeout: int
    max_export_batch_length: int
    max_export_batch_byte_size: int
    export_func: Callable[[dict, List[Any]], None]
    finish_event_processor: Optional[Callable[[FinishEventInfo], None]] = None


class BatchQueueManager(QueueManager):
    def __init__(self, options: BatchQueueManagerOptions):
        self.options = options
        self.queue = Queue(maxsize=options.max_queue_length)
        self.dropped = 0
        self.batch = []
        self.batch_byte_size = 0
        self.batch_lock = threading.Lock()
        self.size_lock = threading.Lock()
        self.export_func = options.export_func
        self.stop_event = threading.Event()

        self.condition = threading.Condition(threading.Lock())
        self.worker_thread = threading.Thread(
            name=f"{self.options.queue_name} BatchQueueManager", target=self.worker, daemon=True
        )
        self.worker_thread.start()

    def worker(self):
        timeout = self.options.batch_timeout / 1000
        while not self.stop_event.is_set():
            with self.condition:
                if self.stop_event.is_set(): # may have stopped, avoid wait
                    break
                if self.queue.qsize() < self.options.max_export_batch_length:  # if queue is full, export now
                    self.condition.wait(timeout)
                    if not self.queue:
                        # queue is not ready, reset timeout and wait again
                        timeout = self.options.batch_timeout / 1000
                        continue
                    if self.stop_event.is_set():  # flush or shutdown
                        break

            self._do_export()
            timeout = self.options.batch_timeout / 1000

        # send last batch in queue
        self._drain_queue()

    def is_should_export(self) -> bool:
        if len(self.batch) >= self.options.max_export_batch_length:
            return True
        with self.size_lock:
            if self.batch_byte_size >= self.options.max_export_batch_byte_size:
                return True
        return False

    def _drain_queue(self):
        # logger.debug(f"{self.options.queue_name} queue _drain_queue, len: {self.queue.qsize()}")
        while not self.queue.empty():
            item = self.queue.get()
            is_batch = False
            with self.batch_lock:
                self.batch.append(item)
                if len(self.batch) == self.options.max_export_batch_length:
                    is_batch = True
            if is_batch:
                self._do_export_batch()

        self._do_export_batch()

    def _do_export(self):
        with self.batch_lock:
            while not self.queue.empty():
                item = self.queue.get()
                self.batch.append(item)
                if len(self.batch) == self.options.max_export_batch_length:
                    break
        self._do_export_batch()

    def _do_export_batch(self):
        with self.batch_lock:
            if self.batch:
                if self.export_func:
                    logger.debug(
                        f"{self.options.queue_name} queue _do_export, len: {len(self.batch)}")
                    self.export_func({}, self.batch)
                self.batch = []
                with self.size_lock:
                    self.batch_byte_size = 0

    def enqueue(self, item: Any, byte_size: int):
        if self.stop_event.is_set():
            return

        is_fail = False
        detail_msg = ""
        try:
            self.queue.put_nowait(item)
            if self.queue.qsize() >= self.options.max_queue_length:
                with self.condition:
                    self.condition.notify()
            detail_msg = f"{self.options.queue_name} enqueue, queue length: {self.queue.qsize()}"
        except queue.Full:
            is_fail = True
            detail_msg = f"{self.options.queue_name} queue is full, dropped span"
            self.dropped += 1
        else:
            with self.size_lock:
                self.batch_byte_size += byte_size

        event_typ = "queue_manager.file_entry.rate"
        extra_params = FinishEventInfoExtra(is_root_span=False)
        if self.options.queue_name == QUEUE_NAME_SPAN or self.options.queue_name == QUEUE_NAME_SPAN_RETRY:
            event_typ = "queue_manager.span_entry.rate"
            if item.is_root_span():
                extra_params = FinishEventInfoExtra(
                    is_root_span=True,
                )

        if self.options and self.options.finish_event_processor:
            self.options.finish_event_processor(FinishEventInfo(
                event_type=event_typ,
                is_event_fail=is_fail,
                item_num=1,
                detail_msg=detail_msg,
                extra_params=extra_params
            ))

    def shutdown(self) -> bool:
        if self.stop_event.is_set():
            return True

        self.stop_event.set()
        with self.condition:
            self.condition.notify_all()

        self.worker_thread.join() # wait worker_thread finish
        return True

    def force_flush(self) -> bool:
        if self.stop_event.is_set():
            return False

        self._drain_queue()
        return True
