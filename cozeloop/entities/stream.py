# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, AsyncIterator, Iterator

T = TypeVar('T')


class StreamReader(ABC, Generic[T]):
    """流式读取器接口"""
    
    @abstractmethod
    def __iter__(self) -> Iterator[T]:
        """支持同步迭代 - for循环直接读取"""
        pass
    
    @abstractmethod
    def __next__(self) -> T:
        """支持next()函数调用"""
        pass
    
    @abstractmethod
    def __aiter__(self) -> AsyncIterator[T]:
        """支持异步迭代 - async for循环直接读取"""
        pass
    
    @abstractmethod
    async def __anext__(self) -> T:
        """支持async next()调用"""
        pass
    
    @abstractmethod
    def close(self):
        """关闭流"""
        pass