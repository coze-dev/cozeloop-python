import asyncio
import logging
from time import sleep
from typing import Optional, Callable, Any, overload, Dict, Generic, Iterator, TypeVar, List, cast, AsyncIterator
from functools import wraps

from cozeloop import Client, Span, start_span
from cozeloop.decorator.utils import is_async_func, is_gen_func, is_async_gen_func

S = TypeVar("S")


class CozeLoopDecorator:
    @overload
    def observe(self, func: Callable) -> Callable:
        ...

    @overload
    def observe(
            self,
            func: None = None,
            *,
            name: Optional[str] = None,
    ) -> Callable:
        ...

    def observe(
            self,
            func: Callable = None,
            *,
            name: Optional[str] = None,
            span_type: Optional[str] = None,
            tags: Optional[Dict[str, Any]] = None,
            client: Optional[Client] = None,
            process_inputs: Optional[Callable[[dict], Any]] = None,
            process_outputs: Optional[Callable[[Any], Any]] = None,
            process_iterator_outputs: Optional[Callable[[Any], Any]] = None,
    ) -> Callable:

        span_type = span_type or 'custom'
        tags = tags or None
        client = client or None
        process_inputs = process_inputs or None
        process_outputs = process_outputs or None
        process_iterator_outputs = process_iterator_outputs or None

        def decorator(func: Callable):

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any):
                _name = name or func.__name__
                span = client.start_span(_name, span_type) if client else start_span(_name, span_type)

                res = None
                try:
                    res = func(*args, **kwargs)
                    output = res
                    if process_outputs:
                        output = process_outputs(output)

                    span.set_output(output)
                except StopIteration:
                    pass
                except Exception as e:
                    span.set_error(e)
                finally:
                    input = {"args": args, "kwargs": kwargs}
                    if process_inputs:
                        input = process_inputs(input)
                    span.set_input(input)
                    span.set_tags(tags)
                    span.finish()

                    if res:
                        return res

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any):
                _name = name or func.__name__
                span = client.start_span(_name, span_type) if client else start_span(_name, span_type)

                res = None
                try:
                    res = await func(*args, **kwargs)
                    output = res
                    if process_outputs:
                        output = process_outputs(output)
                    span.set_output(output)
                except StopIteration:
                    pass
                except StopAsyncIteration:
                    pass
                except Exception as e:
                    if e.args and e.args[0] == 'coroutine raised StopIteration':  # coroutine StopIteration
                        pass
                    else:
                        span.set_error(e)
                finally:
                    input = {"args": args, "kwargs": kwargs}
                    if process_inputs:
                        input = process_inputs(input)
                    span.set_input(input)
                    span.set_tags(tags)
                    span.finish()

                    if res:
                        return res

            @wraps(func)
            def gen_wrapper(*args: Any, **kwargs: Any):
                _name = name or func.__name__
                span = client.start_span(_name, span_type) if client else start_span(_name, span_type)

                try:
                    gen = func(*args, **kwargs)
                    items = []
                    try:
                        for item in gen:
                            items.append(item)
                            yield item
                    except StopIteration:
                        pass
                    finally:
                        if process_outputs:
                            items = process_outputs(items)
                        span.set_output(items)

                except Exception as e:
                    span.set_error(e)
                finally:
                    input = {"args": args, "kwargs": kwargs}
                    if process_inputs:
                        input = process_inputs(input)
                    span.set_input(input)
                    span.set_tags(tags)
                    span.finish()

            @wraps(func)
            async def async_gen_wrapper(*args: Any, **kwargs: Any):
                _name = name or func.__name__
                span = client.start_span(_name, span_type) if client else start_span(_name, span_type)

                try:
                    gen = func(*args, **kwargs)
                    items = []
                    try:
                        async for item in gen:
                            items.append(item)
                            yield item
                    finally:
                        if process_outputs:
                            items = process_outputs(items)
                        span.set_output(items)
                except StopIteration:
                    pass
                except StopAsyncIteration:
                    pass
                except Exception as e:
                    if e.args and e.args[0] == 'coroutine raised StopIteration':
                        pass
                    else:
                        span.set_error(e)
                finally:
                    input = {"args": args, "kwargs": kwargs}
                    if process_inputs:
                        input = process_inputs(input)
                    span.set_input(input)
                    span.set_tags(tags)
                    span.finish()

            @wraps(func)
            def sync_stream_wrapper(*args: Any, **kwargs: Any):
                _name = name or func.__name__
                span = client.start_span(_name, span_type) if client else start_span(_name, span_type)

                res = None
                try:
                    res = func(*args, **kwargs)
                    output = res
                    if hasattr(output, "__iter__"):
                        return _CozeLoopTraceStream(output, span, process_iterator_outputs)
                    if process_outputs:
                        output = process_outputs(output)

                    span.set_output(output)
                except StopIteration:
                    pass
                except Exception as e:
                    span.set_error(e)
                finally:
                    input = {"args": args, "kwargs": kwargs}
                    if process_inputs:
                        input = process_inputs(input)
                    span.set_input(input)
                    span.set_tags(tags)

                    if not hasattr(res, "__iter__") and res:
                        return res

            @wraps(func)
            async def async_stream_wrapper(*args: Any, **kwargs: Any):
                _name = name or func.__name__
                span = client.start_span(_name, span_type) if client else start_span(_name, span_type)

                res = None
                try:
                    res = await func(*args, **kwargs)
                    output = res
                    if hasattr(output, "__aiter__"):
                        return _CozeLoopAsyncTraceStream(output, span, process_iterator_outputs)
                    if process_outputs:
                        output = process_outputs(output)
                    span.set_output(output)
                except StopIteration:
                    pass
                except StopAsyncIteration:
                    pass
                except Exception as e:
                    if e.args and e.args[0] == 'coroutine raised StopIteration':  # coroutine StopIteration
                        pass
                    else:
                        span.set_error(e)
                finally:
                    input = {"args": args, "kwargs": kwargs}
                    if process_inputs:
                        input = process_inputs(input)
                    span.set_input(input)
                    span.set_tags(tags)

                    if not hasattr(res, "__aiter__") and res:
                        return res


            if is_async_gen_func(func):
                return async_gen_wrapper
            if is_gen_func(func):
                return gen_wrapper
            elif is_async_func(func):
                if process_iterator_outputs:
                    return async_stream_wrapper
                else:
                    return async_wrapper
            else:
                if process_iterator_outputs:
                    return sync_stream_wrapper
                else:
                    return sync_wrapper

        if func is None:
            return decorator
        else:
            return decorator(func)


class _CozeLoopTraceStream(Generic[S]):
    def __init__(
            self,
            stream: Iterator[S],
            span: Span,
            process_iterator_outputs: Optional[Callable[[Any], Any]] = None,
    ):
        self.__stream__ = stream
        self.__span = span
        self.__output__: list[S] = []
        self.__process_iterator_outputs = process_iterator_outputs

    def __next__(self) -> S:
        try:
            return next(self.__streamer__())
        except StopIteration:
            self.__end__()
            raise

    def __iter__(self) -> Iterator[S]:
        try:
            yield from self.__streamer__()
        except Exception as e:
            self.__span.set_error(e)
            self.__span.finish()
            raise
        else:
            self.__end__()

    def __enter__(self):
        return self.__stream__.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            return self.__stream__.__exit__(exc_type, exc_val, exc_tb)
        finally:
            if exc_type:
                self.__end__(exc_val)
            else:
                self.__end__()

    def __streamer__(
            self,
    ):
        try:
            temp_stream = self.__stream__
            while True:
                s = next(temp_stream)
                self.__output__.append(s)
                yield s
        except StopIteration as e:
            return e

    def __end__(self, err: Exception = None):
        if self.__process_iterator_outputs:
            self.__output__ = self.__process_iterator_outputs(self.__output__)
        self.__span.set_output(self.__output__)
        if err:
            self.__span.set_error(err)
        self.__span.finish()


class _CozeLoopAsyncTraceStream(Generic[S]):
    def __init__(
            self,
            stream: AsyncIterator[S],
            span: Span,
            process_iterator_outputs: Optional[Callable[[Any], Any]] = None,
    ):
        self.__stream__ = stream
        self.__span = span
        self.__output__: list[S] = []
        self.__process_iterator_outputs = process_iterator_outputs

    async def _aend(self, error: Optional[Exception] = None):
        if error:
            self.__span.set_error(error)
        if self.__process_iterator_outputs:
            self.__output__ = self.__process_iterator_outputs(self.__output__)
        self.__span.set_output(self.__output__)
        self.__span.finish()

    async def __anext__(self) -> S:
        try:
            return await self.__async_streamer__().__anext__()
        except StopAsyncIteration:
            await self._aend()
            raise

    async def __aiter__(self) -> AsyncIterator[S]:
        try:
            async for item in self.__async_streamer__():
                yield item
        except StopIteration:
            await self._aend()
            raise
        except StopAsyncIteration:
            await self._aend()
            raise
        except Exception as e:
            await self._aend()
            raise e
        else:
            await self._aend()

    async def __aenter__(self):
        return await self.__stream__.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            return await self.__stream__.__aexit__(exc_type, exc_val, exc_tb)
        finally:
            await self._aend()

    async def __async_streamer__(
            self,
    ):
        try:
            temp_stream = self.__stream__
            while True:
                s = await temp_stream.__anext__()
                self.__output__.append(s)
                yield s
        except StopIteration:
            pass
