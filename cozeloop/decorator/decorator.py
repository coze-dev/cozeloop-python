# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
import time
from typing import Optional, Callable, Any, overload, Dict, Generic, Iterator, TypeVar, List, cast, AsyncIterator
from functools import wraps

from langchain_core.runnables import RunnableLambda, RunnableConfig

from cozeloop import Client, Span, start_span
from cozeloop.decorator.utils import is_async_func, is_gen_func, is_async_gen_func, is_class_func

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
            baggage: Optional[Dict[str, str]] = None,
            client: Optional[Client] = None,
            process_inputs: Optional[Callable[[dict], Any]] = None,
            process_outputs: Optional[Callable[[Any], Any]] = None,
            process_iterator_outputs: Optional[Callable[[Any], Any]] = None,
    ) -> Callable:
        """
        Decorator to add CozeLoop tracing to a function.

        :param func: The function to be decorated.
        :param name: The name of the Span. Defaults to the function name.
        :param span_type: The span_type of the Span. Defaults to 'custom'.
        :param tags: Set tags for the Span. The Priority is higher than the default tags.
        :param baggage: Set baggage for the Span. The Priority is higher than the default baggage.
                        baggage can cover tag of sample key, and baggage will pass to child span automatically.
        :param client: The Client to be used. Defaults to the default Client.
        :param process_inputs: process inputs result before report trace. The input is a dictionary with
                               the format: {"args": args, "kwargs": kwargs}
        :param process_outputs: process outputs result before report trace. For regular functions, the input
                                is Any type (the original function result). For generator functions, after being fully
                                consumed or closed, the result will be packaged into a List. If the generator is not
                                fully consumed or closed, it's considered unfinished, the result will be empty, and
                                no output will be reported.
        :param process_iterator_outputs: For functions that return iterators, you should define it to handle the
                                iterator results before reporting them to trace. The Input is List (since it's an
                                iterator, the result will be packaged into a List after being fully consumed).
        :return: Callable: The decorated function.
        """

        span_type = span_type or 'custom'
        tags = tags or None
        baggage = baggage or None
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
                    if baggage:
                        span.set_baggage(baggage)
                    res = func(*args, **kwargs)
                    output = res
                    if process_outputs:
                        output = process_outputs(output)
                        inject_inner_token(span, output)
                    span.set_output(output)
                except StopIteration:
                    pass
                except Exception as e:
                    span.set_error(e)
                    raise e
                finally:
                    # ignore self
                    if len(args) > 0 and is_class_func(func):
                        args = args[1:]
                    input = {"args": args, "kwargs": kwargs}
                    if process_inputs:
                        input = process_inputs(input)
                    span.set_input(input)
                    span.set_tags(tags)
                    span.finish()

                    if res is not None:
                        return res

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any):
                _name = name or func.__name__
                span = client.start_span(_name, span_type) if client else start_span(_name, span_type)

                res = None
                try:
                    if baggage:
                        span.set_baggage(baggage)
                    res = await func(*args, **kwargs)
                    output = res
                    if process_outputs:
                        output = process_outputs(output)
                        inject_inner_token(span, output)
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
                        raise e
                finally:
                    # ignore self
                    if len(args) > 0 and is_class_func(func):
                        args = args[1:]
                    input = {"args": args, "kwargs": kwargs}
                    if process_inputs:
                        input = process_inputs(input)
                    span.set_input(input)
                    span.set_tags(tags)
                    span.finish()

                    if res is not None:
                        return res

            @wraps(func)
            def gen_wrapper(*args: Any, **kwargs: Any):
                _name = name or func.__name__
                span = client.start_span(_name, span_type) if client else start_span(_name, span_type)

                try:
                    if baggage:
                        span.set_baggage(baggage)
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
                    raise e
                finally:
                    # ignore self
                    if len(args) > 0 and is_class_func(func):
                        args = args[1:]
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
                    if baggage:
                        span.set_baggage(baggage)
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
                        raise e
                finally:
                    # ignore self
                    if len(args) > 0 and is_class_func(func):
                        args = args[1:]
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
                    if baggage:
                        span.set_baggage(baggage)
                    res = func(*args, **kwargs)
                    output = res
                    if hasattr(output, "__iter__"):
                        return _CozeLoopTraceStream(output, span, process_iterator_outputs, span_type)
                    if process_outputs:
                        output = process_outputs(output)

                    span.set_output(output)
                except StopIteration:
                    pass
                except Exception as e:
                    span.set_error(e)
                    raise e
                finally:
                    # ignore self
                    if len(args) > 0 and is_class_func(func):
                        args = args[1:]
                    input = {"args": args, "kwargs": kwargs}
                    if process_inputs:
                        input = process_inputs(input)
                    span.set_input(input)
                    span.set_tags(tags)

                    if not hasattr(res, "__iter__") and res is not None:
                        return res

            @wraps(func)
            async def async_stream_wrapper(*args: Any, **kwargs: Any):
                _name = name or func.__name__
                span = client.start_span(_name, span_type) if client else start_span(_name, span_type)

                res = None
                try:
                    if baggage:
                        span.set_baggage(baggage)
                    res = await func(*args, **kwargs)
                    output = res
                    if hasattr(output, "__aiter__"):
                        return _CozeLoopAsyncTraceStream(output, span, process_iterator_outputs, span_type)
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
                        raise e
                finally:
                    # ignore self
                    if len(args) > 0 and is_class_func(func):
                        args = args[1:]
                    input = {"args": args, "kwargs": kwargs}
                    if process_inputs:
                        input = process_inputs(input)
                    span.set_input(input)
                    span.set_tags(tags)

                    if not hasattr(res, "__aiter__") and res is not None:
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

    def to_runnable(
            self,
            func: Callable = None,
    ) -> Callable:
        """
        Decorator to be RunnableLambda.

        :param func: The function to be decorated, Requirements are as follows：
                     1. When the func is called, parameter config(RunnableConfig) is required, you must use the config containing cozeloop callback handler of 'current request', otherwise, the trace may be lost!

        Examples:
            @to_runnable
            def runnable_func(my_input: dict) -> str:
                return input

            async def scorer_leader(state: MyState) -> dict | str:
                await runnable_func({"a": "111", "b": 222, "c": "333"}, config=state.config) # config is required
        """

        def decorator(func: Callable):

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any):
                config = kwargs.pop("config", None)
                config = _convert_config(config)
                res = None
                try:
                    extra = {}
                    if len(args) > 0 and is_class_func(func):
                        extra = {"_inner_class_self": args[0]}
                        args = args[1:]
                    inp = {}
                    if len(args) > 0:
                        inp['args'] = args
                    if len(kwargs) > 0:
                        inp['kwargs'] = kwargs
                    res = RunnableLambda(_param_wrapped_func).invoke(input=inp, config=config, **extra)
                    if hasattr(res, "__iter__"):
                        return res
                except StopIteration:
                    pass
                except Exception as e:
                    raise e
                finally:
                    if res is not None:
                        return res

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any):
                config = kwargs.pop("config", None)
                config = _convert_config(config)
                res = None
                try:
                    extra = {}
                    if len(args) > 0 and is_class_func(func):
                        extra = {"_inner_class_self": args[0]}
                        args = args[1:]
                    inp = {}
                    if len(args) > 0:
                        inp['args'] = args
                    if len(kwargs) > 0:
                        inp['kwargs'] = kwargs
                    res = await RunnableLambda(_param_wrapped_func_async).ainvoke(input=inp, config=config, **extra)
                    if hasattr(res, "__aiter__"):
                        return res
                except StopIteration:
                    pass
                except StopAsyncIteration:
                    pass
                except Exception as e:
                    if e.args and e.args[0] == 'coroutine raised StopIteration':  # coroutine StopIteration
                        pass
                    else:
                        raise e
                finally:
                    if res is not None:
                        return res

            @wraps(func)
            def gen_wrapper(*args: Any, **kwargs: Any):
                config = kwargs.pop("config", None)
                config = _convert_config(config)
                try:
                    extra = {}
                    if len(args) > 0 and is_class_func(func):
                        extra = {"_inner_class_self": args[0]}
                        args = args[1:]
                    inp = {}
                    if len(args) > 0:
                        inp['args'] = args
                    if len(kwargs) > 0:
                        inp['kwargs'] = kwargs
                    gen = RunnableLambda(_param_wrapped_func).invoke(input=inp, config=config, *extra)
                    try:
                        for item in gen:
                            yield item
                    except StopIteration:
                        pass
                except Exception as e:
                    raise e

            @wraps(func)
            async def async_gen_wrapper(*args: Any, **kwargs: Any):
                config = kwargs.pop("config", None)
                config = _convert_config(config)
                try:
                    extra = {}
                    if len(args) > 0 and is_class_func(func):
                        extra = {"_inner_class_self": args[0]}
                        args = args[1:]
                    inp = {}
                    if len(args) > 0:
                        inp['args'] = args
                    if len(kwargs) > 0:
                        inp['kwargs'] = kwargs
                    gen = RunnableLambda(_param_wrapped_func_async).invoke(input=inp, config=config, **extra)
                    items = []
                    try:
                        async for item in gen:
                            items.append(item)
                            yield item
                    finally:
                        pass
                except StopIteration:
                    pass
                except StopAsyncIteration:
                    pass
                except Exception as e:
                    if e.args and e.args[0] == 'coroutine raised StopIteration':
                        pass
                    else:
                        raise e

            # for convert parameter
            def _param_wrapped_func(input_dict: dict, **kwargs) -> Any:
                real_args = input_dict.get("args", ())
                real_kwargs = input_dict.get("kwargs", {})

                inner_class_self = kwargs.get("_inner_class_self", None)
                if inner_class_self is not None:
                    real_args = (inner_class_self, *real_args)

                return func(*real_args, **real_kwargs)

            async def _param_wrapped_func_async(input_dict: dict, **kwargs) -> Any:
                real_args = input_dict.get("args", ())
                real_kwargs = input_dict.get("kwargs", {})

                inner_class_self = kwargs.get("_inner_class_self", None)
                if inner_class_self is not None:
                    real_args = (inner_class_self, *real_args)

                return await func(*real_args, **real_kwargs)

            def _convert_config(config: RunnableConfig = None) -> RunnableConfig | None:
                if config is None:
                    config = RunnableConfig(run_name=func.__name__)
                    config['run_name'] = func.__name__
                elif isinstance(config, dict):
                    config['run_name'] = func.__name__
                return config

            if is_async_gen_func(func):
                return async_gen_wrapper
            if is_gen_func(func):
                return gen_wrapper
            elif is_async_func(func):
                return async_wrapper
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
            span_type: str = "",
    ):
        self.__stream__ = stream
        self.__span = span
        self.__output__: list[S] = []
        self.__process_iterator_outputs = process_iterator_outputs
        self.__is_set_start_time_first_token: bool = False
        self.__span_type = span_type

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
                if not self.__is_set_start_time_first_token and self.__span_type == "model":
                    self.__span.set_start_time_first_resp(time.time_ns() // 1_000)
                    self.__is_set_start_time_first_token = True
                yield s
        except StopIteration as e:
            return e

    def __end__(self, err: Exception = None):
        if self.__process_iterator_outputs:
            self.__output__ = self.__process_iterator_outputs(self.__output__)
            inject_inner_token(self.__span, self.__output__)
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
            span_type: str = "",
    ):
        self.__stream__ = stream
        self.__span = span
        self.__output__: list[S] = []
        self.__process_iterator_outputs = process_iterator_outputs
        self.__is_set_start_time_first_token: bool = False
        self.__span_type = span_type

    async def _aend(self, error: Optional[Exception] = None):
        if error:
            self.__span.set_error(error)
        if self.__process_iterator_outputs:
            self.__output__ = self.__process_iterator_outputs(self.__output__)
            inject_inner_token(self.__span, self.__output__)
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
            await self._aend(e)
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
                if not self.__is_set_start_time_first_token and self.__span_type == "model":
                    self.__span.set_start_time_first_resp(time.time_ns() // 1_000)
                    self.__is_set_start_time_first_token = True
                yield s
        except (StopIteration, StopAsyncIteration):
            pass


def inject_inner_token(span: Span, src):
    if isinstance(src, dict) and src.get("_inner_tokens_dict"):
        if input_tokens := src.get("_inner_tokens_dict").get("input_tokens", 0):
            span.set_input_tokens(input_tokens)
        if output_tokens := src.get("_inner_tokens_dict").get("output_tokens", 0):
            span.set_output_tokens(output_tokens)
