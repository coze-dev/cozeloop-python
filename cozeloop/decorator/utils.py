# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

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

def is_class_func(func: Callable) -> bool:
    sig = inspect.signature(func)
    first_param = next(iter(sig.parameters))
    if first_param == 'self':
        return True
    return False