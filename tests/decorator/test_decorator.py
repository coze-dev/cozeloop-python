"""CozeLoopDecorator 单测：覆盖原函数返回空值的情况

测试风格参考现有 tests/* 文件：使用 pytest、类封装、plain 断言。
"""
import sys
import types
import os
import asyncio
from typing import AsyncIterator, Iterator

import pytest

# 在导入被测模块前，构造轻量级依赖，避免引入 requests/charset_normalizer 等重依赖
_cozeloop = types.ModuleType('cozeloop')
_cozeloop.__path__ = [os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'cozeloop'))]
sys.modules['cozeloop'] = _cozeloop

class SpanMock:
    def __init__(self):
        self.output = None  # string，覆盖
        self.input = None   # string，覆盖
        self.tag = None     # dict，覆盖
        self.error = None   # string，覆盖
        self.finished = False
        self.baggage = None

    # CozeLoopSpan 接口
    def set_baggage(self, baggage):
        self.baggage = baggage

    def set_output(self, output):
        self.output = str(output)

    def set_input(self, _input):
        self.input = str(_input)

    def set_tags(self, tagKV):
        if tagKV is not None:
            assert isinstance(tagKV, dict)
            self.tag = tagKV

    def set_error(self, err):
        self.error = str(err)

    def finish(self):
        self.finished = True

    # 供 stream 包装器调用的额外方法（空实现）
    def set_start_time_first_resp(self, *_args, **_kwargs):
        pass

    def set_input_tokens(self, *_args, **_kwargs):
        pass

    def set_output_tokens(self, *_args, **_kwargs):
        pass

class Client:
    @classmethod
    def start_span(cls, *_a, **_k):
        return SpanMock()

class Span:
    pass

_cozeloop.Client = Client
_cozeloop.Span = Span
_cozeloop.start_span = Client.start_span

# 允许加载子模块
_decorator_mod = types.ModuleType('cozeloop.decorator')
_decorator_mod.__path__ = [os.path.join(_cozeloop.__path__[0], 'decorator')]
sys.modules['cozeloop.decorator'] = _decorator_mod

from cozeloop.decorator import decorator as decorator_module
import cozeloop as _cozeloop_mod


class TestCozeLoopDecoratorEmptyOutputs:
    """覆盖原函数返回空值（None/空字符串/空列表、空迭代器/空异步迭代器）的行为"""

    def test_sync_func_return_none(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        def f():
            return None

        decorated = decorator_module.CozeLoopDecorator().observe()(f)
        res = decorated()

        assert res is None
        assert span.output == 'None'
        assert span.finished is True

    def test_sync_func_return_empty_string(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        def f():
            return ""

        decorated = decorator_module.CozeLoopDecorator().observe()(f)
        res = decorated()

        assert res == ""
        assert span.output == ""
        assert span.finished is True

    def test_sync_func_return_empty_list(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        def f():
            return []

        decorated = decorator_module.CozeLoopDecorator().observe()(f)
        res = decorated()

        assert res == []
        assert span.output == '[]'
        assert span.finished is True

    def test_generator_func_no_yield(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        def gen() -> Iterator[int]:
            if False:
                yield 1

        decorated = decorator_module.CozeLoopDecorator().observe()(gen)
        result = list(decorated())

        assert result == []
        assert span.output == '[]'
        assert span.finished is True

    def test_async_func_return_none(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        async def af():
            return None

        decorated = decorator_module.CozeLoopDecorator().observe()(af)
        res = asyncio.run(decorated())

        assert res is None
        assert span.output == 'None'
        assert span.finished is True

    def test_async_generator_no_yield(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        async def agen() -> AsyncIterator[int]:
            if False:
                yield 1
            return

        decorated = decorator_module.CozeLoopDecorator().observe()(agen)

        async def collect():
            return [item async for item in decorated()]

        result = asyncio.run(collect())

        assert result == []
        assert span.output == '[]'
        assert span.finished is True

    def test_sync_iterator_stream_wrapper_empty(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        def make_iter():
            return iter([])

        # 设置 process_iterator_outputs 以走 stream 包装器路径
        decorated = decorator_module.CozeLoopDecorator().observe(process_iterator_outputs=lambda xs: xs)(make_iter)
        stream = decorated()
        result = list(stream)

        assert result == []
        assert span.output == '[]'
        assert span.finished is True

    def test_async_iterator_stream_wrapper_empty(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        class EmptyAsyncIter:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

        async def make_async_iter():
            return EmptyAsyncIter()

        decorated = decorator_module.CozeLoopDecorator().observe(process_iterator_outputs=lambda xs: xs)(make_async_iter)

        async def collect():
            stream = await decorated()
            return [item async for item in stream]

        result = asyncio.run(collect())

        assert result == []
        assert span.output == '[]'
        assert span.finished is True


class TestCozeLoopDecoratorNormalOutputs:
    """覆盖正常返回值与迭代产出的情况"""

    def test_sync_func_return_int(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        def f():
            return 123

        decorated = decorator_module.CozeLoopDecorator().observe()(f)
        res = decorated()

        assert res == 123
        assert span.output == '123'
        assert span.finished is True

    def test_sync_func_return_dict(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        def f():
            return {"a": 1, "b": 2}

        decorated = decorator_module.CozeLoopDecorator().observe()(f)
        res = decorated()

        assert res == {"a": 1, "b": 2}
        assert span.output == "{'a': 1, 'b': 2}"
        assert span.finished is True

    def test_sync_func_process_outputs_applied(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        def f():
            return 21

        decorated = decorator_module.CozeLoopDecorator().observe(process_outputs=lambda x: x * 2)(f)
        res = decorated()

        assert res == 21
        assert span.output == '42'
        assert span.finished is True

    def test_generator_func_yield_items(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        def gen() -> Iterator[int]:
            yield 1
            yield 2
            yield 3

        decorated = decorator_module.CozeLoopDecorator().observe()(gen)
        result = list(decorated())

        assert result == [1, 2, 3]
        assert span.output == '[1, 2, 3]'
        assert span.finished is True

    def test_generator_func_process_outputs_applied(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        def gen() -> Iterator[int]:
            yield 1
            yield 2

        decorated = decorator_module.CozeLoopDecorator().observe(process_outputs=lambda xs: [x * 10 for x in xs])(gen)
        result = list(decorated())

        assert result == [1, 2]
        assert span.output == '[10, 20]'
        assert span.finished is True

    def test_async_func_return_string(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        async def af():
            return "ok"

        decorated = decorator_module.CozeLoopDecorator().observe()(af)
        res = asyncio.run(decorated())

        assert res == "ok"
        assert span.output == 'ok'
        assert span.finished is True

    def test_async_generator_yield_items(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        async def agen() -> AsyncIterator[int]:
            for i in [7, 8]:
                yield i

        decorated = decorator_module.CozeLoopDecorator().observe()(agen)

        async def collect():
            return [item async for item in decorated()]

        result = asyncio.run(collect())

        assert result == [7, 8]
        assert span.output == '[7, 8]'
        assert span.finished is True

    def test_sync_stream_wrapper_nonempty(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        def make_iter():
            return iter(["a", "b"])

        decorated = decorator_module.CozeLoopDecorator().observe(process_iterator_outputs=lambda xs: list(reversed(xs)))(make_iter)
        stream = decorated()
        result = list(stream)

        assert result == ["a", "b"]
        assert span.output == "['b', 'a']"
        assert span.finished is True

    def test_async_stream_wrapper_nonempty(self, monkeypatch):
        span = SpanMock()
        monkeypatch.setattr(decorator_module, "start_span", lambda *args, **kwargs: span)

        class AsyncIter:
            def __init__(self, items):
                self._items = list(items)
                self._idx = 0
            def __aiter__(self):
                return self
            async def __anext__(self):
                if self._idx >= len(self._items):
                    raise StopAsyncIteration
                v = self._items[self._idx]
                self._idx += 1
                return v

        async def make_async_iter():
            return AsyncIter([1, 2, 3])

        decorated = decorator_module.CozeLoopDecorator().observe(process_iterator_outputs=lambda xs: [x * 2 for x in xs])(make_async_iter)

        async def collect():
            stream = await decorated()
            return [item async for item in stream]

        result = asyncio.run(collect())

        assert result == [1, 2, 3]
        assert span.output == '[2, 4, 6]'
        assert span.finished is True
