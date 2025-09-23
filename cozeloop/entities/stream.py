# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, AsyncIterator, Iterator

T = TypeVar('T')


class StreamReader(ABC, Generic[T]):
    """Stream reader interface"""
    
    @abstractmethod
    def __iter__(self) -> Iterator[T]:
        """Support synchronous iteration - for loop direct reading"""
        pass
    
    @abstractmethod
    def __next__(self) -> T:
        """Support next() function call"""
        pass
    
    @abstractmethod
    def __aiter__(self) -> AsyncIterator[T]:
        """Support asynchronous iteration - async for loop direct reading"""
        pass
    
    @abstractmethod
    async def __anext__(self) -> T:
        """Support async next() call"""
        pass
    
    @abstractmethod
    def close(self):
        """Close stream"""
        pass