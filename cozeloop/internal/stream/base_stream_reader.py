# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Iterator, AsyncIterator, Optional, Any
import json

import httpx

from cozeloop.entities.stream import StreamReader
from cozeloop.internal.stream.sse import SSEDecoder, ServerSentEvent
from cozeloop.internal.consts.error import RemoteServiceError, InternalError

T = TypeVar('T')

logger = logging.getLogger(__name__)


class BaseStreamReader(StreamReader[T], ABC, Generic[T]):
    """
    通用StreamReader基类
    
    基于Fornax的Stream设计模式，集成SSEDecoder进行SSE数据解码
    支持同步和异步迭代器模式，实现上下文管理器
    提供统一的错误处理机制和资源管理
    """
    
    def __init__(self, response: httpx.Response, log_id: str = ""):
        """
        初始化BaseStreamReader
        
        Args:
            response: httpx响应对象
            log_id: 日志ID，用于错误追踪
        """
        self.response = response
        self.log_id = log_id
        self._decoder = SSEDecoder()
        self._closed = False
        self._sync_iterator: Optional[Iterator[T]] = None
        self._async_iterator: Optional[AsyncIterator[T]] = None
    
    @abstractmethod
    def _parse_sse_data(self, sse: ServerSentEvent) -> Optional[T]:
        """
        解析SSE数据为业务对象，子类必须实现
        
        Args:
            sse: ServerSentEvent对象
            
        Returns:
            Optional[T]: 解析后的业务对象，如果不需要返回则为None
        """
        pass
    
    def _iter_events(self) -> Iterator[ServerSentEvent]:
        """
        迭代SSE事件
        
        Yields:
            ServerSentEvent: 解码后的SSE事件
        """
        try:
            for sse in self._decoder.iter_bytes(self.response.iter_bytes()):
                yield sse
        except Exception as e:
            logger.error(f"Error iterating SSE events: {e}")
            raise InternalError(f"Failed to decode SSE stream: {e}")
    
    async def _aiter_events(self) -> AsyncIterator[ServerSentEvent]:
        """
        异步迭代SSE事件
        
        Yields:
            ServerSentEvent: 解码后的SSE事件
        """
        try:
            # 由于httpx.stream()返回的是同步流，即使在异步上下文中也需要使用同步迭代
            # 将同步迭代包装成异步生成器
            for sse in self._decoder.iter_bytes(self.response.iter_bytes()):
                yield sse
        except Exception as e:
            logger.error(f"Error async iterating SSE events: {e}")
            raise InternalError(f"Failed to decode SSE stream: {e}")
    
    def _handle_sse_error(self, sse: ServerSentEvent) -> None:
        """
        处理SSE事件中的错误
        
        Args:
            sse: ServerSentEvent对象
            
        Raises:
            RemoteServiceError: 当检测到错误事件时
        """
        if not sse.data:
            return
        
        try:
            data = sse.json()
            
            # 检查是否包含错误信息
            if isinstance(data, dict):
                # 检查错误码字段
                if 'code' in data and data['code'] != 0:
                    error_code = data.get('code', 0)
                    error_msg = data.get('msg', 'Unknown error')
                    raise RemoteServiceError(200, error_code, error_msg, self.log_id)
                
                # 检查error字段
                if 'error' in data:
                    error_info = data['error']
                    if isinstance(error_info, dict):
                        error_code = error_info.get('code', 0)
                        error_msg = error_info.get('message', 'Unknown error')
                    else:
                        error_code = 0
                        error_msg = str(error_info)
                    raise RemoteServiceError(200, error_code, error_msg, self.log_id)
                    
        except json.JSONDecodeError:
            # 如果不是JSON格式，忽略错误检查
            pass
        except RemoteServiceError:
            # 重新抛出RemoteServiceError
            raise
        except Exception as e:
            logger.warning(f"Error checking SSE error: {e}")
    
    def __stream__(self) -> Iterator[T]:
        """
        核心流处理逻辑
        
        Yields:
            T: 解析后的业务对象
        """
        if self._closed:
            return
        
        try:
            for sse in self._iter_events():
                if self._closed:
                    break
                
                # 检查错误
                self._handle_sse_error(sse)
                
                # 解析数据
                result = self._parse_sse_data(sse)
                if result is not None:
                    yield result
                    
        except RemoteServiceError:
            raise
        except Exception as e:
            logger.error(f"Error in stream processing: {e}")
            raise InternalError(f"Stream processing failed: {e}")
        finally:
            self._closed = True
    
    async def __astream__(self) -> AsyncIterator[T]:
        """
        异步核心流处理逻辑
        
        Yields:
            T: 解析后的业务对象
        """
        if self._closed:
            return
        
        try:
            async for sse in self._aiter_events():
                if self._closed:
                    break
                
                # 检查错误
                self._handle_sse_error(sse)
                
                # 解析数据
                result = self._parse_sse_data(sse)
                if result is not None:
                    yield result
                    
        except RemoteServiceError:
            raise
        except Exception as e:
            logger.error(f"Error in async stream processing: {e}")
            raise InternalError(f"Async stream processing failed: {e}")
        finally:
            self._closed = True
    
    # 同步迭代器接口
    def __iter__(self) -> Iterator[T]:
        """支持同步迭代 - for循环直接读取"""
        if self._sync_iterator is None:
            self._sync_iterator = self.__stream__()
        return self._sync_iterator
    
    def __next__(self) -> T:
        """支持next()函数调用"""
        if self._closed:
            raise StopIteration("Stream is closed")
        
        try:
            if self._sync_iterator is None:
                self._sync_iterator = self.__stream__()
            return next(self._sync_iterator)
        except StopIteration:
            self._closed = True
            raise
        except Exception as e:
            self._closed = True
            raise StopIteration from e
    
    # 异步迭代器接口
    def __aiter__(self) -> AsyncIterator[T]:
        """支持异步迭代 - async for循环直接读取"""
        if self._async_iterator is None:
            self._async_iterator = self.__astream__()
        return self._async_iterator
    
    async def __anext__(self) -> T:
        """支持async next()调用"""
        if self._closed:
            raise StopAsyncIteration("Stream is closed")
        
        try:
            if self._async_iterator is None:
                self._async_iterator = self.__astream__()
            return await self._async_iterator.__anext__()
        except StopAsyncIteration:
            self._closed = True
            raise
        except Exception as e:
            self._closed = True
            raise StopAsyncIteration from e
    
    # 上下文管理器接口
    def __enter__(self) -> BaseStreamReader[T]:
        """同步上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """同步上下文管理器出口"""
        self.close()
    
    async def __aenter__(self) -> BaseStreamReader[T]:
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """异步上下文管理器出口"""
        await self.aclose()
    
    # 资源管理
    def close(self) -> None:
        """关闭流"""
        self._closed = True
        if hasattr(self.response, 'close'):
            self.response.close()
    
    async def aclose(self) -> None:
        """异步关闭流"""
        self._closed = True
        if hasattr(self.response, 'aclose'):
            await self.response.aclose()
    
    @property
    def closed(self) -> bool:
        """检查流是否已关闭"""
        return self._closed