# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import threading
import subprocess
import sys
import textwrap
from collections import Counter

import pytest

from cozeloop.internal import consts
from cozeloop.internal.httpclient.base_model import BaseResponse
from cozeloop.internal.trace.model.model import QueueConf
from cozeloop.internal.trace.queue_manager import BatchQueueManager, BatchQueueManagerOptions
from cozeloop.internal.trace.trace import TraceProvider


@pytest.fixture
def make_queue():
    queues = []

    def create(export_func, **kwargs):
        options = dict(
            queue_name="file",
            max_queue_length=64,
            batch_timeout=60000,
            max_export_batch_length=1,
            max_export_batch_byte_size=1024,
            export_concurrency=3,
            export_func=export_func,
        )
        options.update(kwargs)
        manager = BatchQueueManager(BatchQueueManagerOptions(**options))
        queues.append(manager)
        return manager

    yield create
    for manager in queues:
        manager.shutdown()


@pytest.mark.parametrize("concurrency", [-3, 0, 1, 3])
def test_concurrency_and_default_configuration(concurrency):
    conf = QueueConf(16, 7, concurrency)
    provider = TraceProvider(None, "workspace", queue_conf=conf)
    processor = provider.span_processor
    try:
        for manager in (processor.span_qm, processor.span_retry_qm,
                        processor.file_qm, processor.file_retry_qm):
            assert manager.options.export_concurrency == max(1, concurrency)
        assert processor.span_qm.options.max_queue_length == 16
        assert processor.span_qm.options.max_export_batch_length == 7
        assert QueueConf().export_concurrency == 1
    finally:
        provider.close_trace()


def test_concurrency_limit_and_batch_ownership(make_queue):
    release = threading.Event()
    saturated = threading.Event()
    lock = threading.Lock()
    batches = []
    active = 0
    peak = 0

    def export(ctx, items):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
            batches.append(items)
            if active == 3:
                saturated.set()
        try:
            assert release.wait(5)
        finally:
            with lock:
                active -= 1

    manager = make_queue(export, max_export_batch_length=2)
    try:
        for item in range(12):
            manager.enqueue(item, 1)
        assert saturated.wait(5), "three exports should run simultaneously"
        assert peak == 3
        release.set()
        assert manager.force_flush()
        assert sorted(item for batch in batches for item in batch) == list(range(12))
        assert all(len(batch) == 2 for batch in batches)
        assert peak == 3
    finally:
        release.set()


@pytest.mark.parametrize("trigger", ["length", "bytes", "timeout"])
def test_batch_triggers(make_queue, trigger):
    exported = threading.Event()
    batches = []

    def export(ctx, items):
        batches.append(items)
        exported.set()

    manager = make_queue(
        export,
        max_export_batch_length=2 if trigger == "length" else 10,
        max_export_batch_byte_size=6 if trigger == "bytes" else 1024,
        batch_timeout=20 if trigger == "timeout" else 60000,
    )
    manager.enqueue("first", 3)
    if trigger != "timeout":
        manager.enqueue("second", 3)
    assert exported.wait(5), "batch should export without an explicit flush"
    assert manager.force_flush()
    expected = [["first"]] if trigger == "timeout" else [["first", "second"]]
    assert batches == expected


@pytest.mark.parametrize("operation", ["force_flush", "shutdown"])
def test_flush_and_shutdown_wait_for_inflight_exports(make_queue, operation):
    entered = threading.Event()
    release = threading.Event()
    completed = threading.Event()
    exported = []
    results = []

    def export(ctx, items):
        entered.set()
        assert release.wait(5)
        exported.extend(items)

    manager = make_queue(export)
    manager.enqueue("first", 1)
    assert entered.wait(5)
    manager.enqueue("second", 1)

    def finish():
        results.append(getattr(manager, operation)())
        completed.set()

    thread = threading.Thread(target=finish, daemon=True)
    thread.start()
    try:
        assert not completed.wait(0.05), "must wait for blocked exports"
        release.set()
        assert completed.wait(5)
        thread.join(5)
        assert results == [True]
        assert sorted(exported) == ["first", "second"]
        if operation == "shutdown":
            manager.enqueue("ignored", 1)
            assert manager.queue.empty()
            assert not manager.force_flush()
            assert manager.shutdown()
    finally:
        release.set()


def test_full_queue_drops_without_unbounded_pending_batches(make_queue):
    release = threading.Event()
    saturated = threading.Event()
    lock = threading.Lock()
    started = 0
    exported = []

    def export(ctx, items):
        nonlocal started
        with lock:
            started += 1
            if started == 2:
                saturated.set()
        assert release.wait(5)
        with lock:
            exported.extend(items)

    manager = make_queue(export, export_concurrency=2, max_queue_length=2)
    try:
        manager.enqueue(0, 1)
        manager.enqueue(1, 1)
        assert saturated.wait(5)
        for item in range(2, 22):
            manager.enqueue(item, 1)
        assert manager.dropped > 0
        assert manager.queue.qsize() <= 2
        release.set()
        manager.force_flush()
        assert len(exported) == 22 - manager.dropped
        assert len(exported) == len(set(exported))
    finally:
        release.set()


def test_export_exception_does_not_disable_workers(make_queue):
    exported = []

    def export(ctx, items):
        if items == [0]:
            raise RuntimeError("export failed")
        exported.extend(items)

    manager = make_queue(export)
    for item in range(6):
        manager.enqueue(item, 1)
    assert manager.force_flush()
    manager.enqueue(6, 1)
    assert manager.force_flush()
    assert sorted(exported) == list(range(1, 7))


def test_simultaneous_flushes_and_shutdowns(make_queue, monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    markers_enqueued = threading.Event()
    exported = []
    results = []
    marker_count = 0

    def export(ctx, items):
        entered.set()
        assert release.wait(5)
        exported.extend(items)

    manager = make_queue(export)
    for item in range(8):
        manager.enqueue(item, 1)
    assert entered.wait(5)
    original_put = manager.queue.put

    def put_marker(item, *args, **kwargs):
        nonlocal marker_count
        original_put(item, *args, **kwargs)
        marker_count += 1
        if marker_count == 2:
            markers_enqueued.set()

    monkeypatch.setattr(manager.queue, "put", put_marker)
    threads = []
    try:
        for operation in ("force_flush", "force_flush", "shutdown", "shutdown"):
            if operation == "shutdown":
                assert markers_enqueued.wait(5)
            thread = threading.Thread(
                target=lambda op=operation: results.append(getattr(manager, op)()),
                daemon=True,
            )
            threads.append(thread)
            thread.start()
        release.set()
        for thread in threads:
            thread.join(5)
            assert not thread.is_alive()
        assert results == [True] * 4
        assert sorted(exported) == list(range(8))
    finally:
        release.set()


def test_atexit_drains_concurrent_exports():
    script = textwrap.dedent("""
        import atexit
        from cozeloop.internal.trace.queue_manager import (
            BatchQueueManager, BatchQueueManagerOptions,
        )
        manager = BatchQueueManager(BatchQueueManagerOptions(
            queue_name="file", max_queue_length=16, batch_timeout=60000,
            max_export_batch_length=1, max_export_batch_byte_size=1024,
            export_concurrency=3,
            export_func=lambda ctx, items: print(items[0], flush=True),
        ))
        atexit.register(manager.shutdown)
        for item in range(8):
            manager.enqueue(item, 1)
    """)
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=10, check=True,
    )
    assert sorted(map(int, result.stdout.splitlines())) == list(range(8))


@pytest.mark.parametrize("operation", ["flush", "close_trace"])
def test_processor_drains_span_and_file_retries(operation):
    lock = threading.Lock()
    span_attempts = Counter()
    file_attempts = Counter()
    events = []

    class HTTPClient:
        def post(self, path, response_model, data):
            with lock:
                for span in data.spans:
                    span_attempts[span.span_id] += 1
                needs_retry = any(span_attempts[span.span_id] == 1 for span in data.spans)
            if needs_retry:
                raise RuntimeError("retry span")
            return BaseResponse(code=0, msg="")

        def upload_file(self, path, response_model, data, file_name, form):
            with lock:
                file_attempts[file_name] += 1
                attempt = file_attempts[file_name]
            if attempt == 1:
                raise RuntimeError("retry file")
            return BaseResponse(code=0, msg="")

    provider = TraceProvider(
        HTTPClient(), "workspace", ultra_large_report=True,
        queue_conf=QueueConf(span_max_export_batch_length=1, export_concurrency=3),
        finish_event_processor=events.append,
    )
    try:
        for index in range(4):
            span = provider.start_span(str(index), "custom", start_new_trace=True)
            span.set_input("x" * (consts.MAX_BYTES_OF_ONE_TAG_VALUE_OF_INPUT_OUTPUT + 1))
            span.finish()
        getattr(provider, operation)()
        assert len(span_attempts) == 4
        assert set(span_attempts.values()) == {2}
        assert len(file_attempts) == 4
        assert set(file_attempts.values()) == {2}
        assert sum(event.is_event_fail for event in events
                   if event.event_type == "exporter.file_flush.rate") == 4
    finally:
        provider.close_trace()
