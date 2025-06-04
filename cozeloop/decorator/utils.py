import inspect
from typing import Callable


def is_async_func(func: Callable) -> bool:
    return inspect.iscoroutinefunction(func) or (
        hasattr(func, "__wrapped__") and inspect.iscoroutinefunction(func.__wrapped__)
    )

def is_gen_func(func: Callable) -> bool:
    return inspect.isgeneratorfunction(func)


def is_async_gen_func(func: Callable) -> bool:
    return inspect.isasyncgenfunction(func)