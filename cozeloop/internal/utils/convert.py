# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import random
import string
from typing import Any, Dict, List, Optional, TypeVar, Sequence
from functools import singledispatch

import pydantic
from pydantic import BaseModel

T = TypeVar('T')

def rm_dup_str_slice(slice: List[str]) -> List[str]:
    return list(dict.fromkeys(slice))

class StringBufferPool:
    _pool = []

    @classmethod
    def get(cls) -> str:
        if cls._pool:
            return cls._pool.pop()
        return ""

    @classmethod
    def recycle(cls, buffer: str):
        cls._pool.append(buffer)

def map_to_string_string(mp: Dict[str, str]) -> str:
    if not mp:
        return ""
    return ",".join(f"{k}={v}" for k, v in mp.items())

def ptr_value(s: Optional[T]) -> T:
    return s if s is not None else None

def ptr(s: T) -> T:
    return s

def generate_random_string(length: int) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def get_value_of_int(value: Any) -> int:
    if isinstance(value, (int, float, str)):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0

def truncate_string_by_char(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[:n]

def truncate_string_by_byte(value_str: str, limit: int) -> (str, bool):
    byte_str = value_str.encode('utf-8')

    if len(byte_str) <= limit:
        return value_str, False

    truncated_byte_str = byte_str[:limit]

    try:
        truncated_str = truncated_byte_str.decode('utf-8')
    except UnicodeDecodeError:
        truncated_str = truncated_byte_str.decode('utf-8', errors='ignore')

    return truncated_str, True

def to_json(param: Any) -> str:
    if param is None:
        return ""
    if isinstance(param, str):
        return param
    try:
        if isinstance(param, BaseModel):
            if pydantic.VERSION.startswith('1'):
                return param.json()
            else:
                return param.model_dump_json()
        return json.dumps(param, ensure_ascii=False)
    except json.JSONDecodeError:
        return param.__str__()
    except Exception:
        return param.__str__()

@singledispatch
def stringify(value: Any) -> str:
    return str(value)

@stringify.register(type(None))
def _(value: None) -> str:
    return ""

@stringify.register(bool)
def _(value: bool) -> str:
    return "true" if value else "false"

@stringify.register(str)
def _(value: str) -> str:
    return value

@stringify.register(bytes)
def _(value: bytes) -> str:
    return value.decode()

@stringify.register(int)
def _(value: int) -> str:
    return str(value)

@stringify.register(float)
def _(value: float) -> str:
    return f"{value:.3f}"