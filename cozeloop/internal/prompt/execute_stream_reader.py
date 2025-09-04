# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import logging
from typing import Optional

from cozeloop.entities.prompt import ExecuteResult
from cozeloop.internal.consts.error import RemoteServiceError
from cozeloop.internal.prompt.converter import convert_execute_data_to_result
from cozeloop.internal.prompt.openapi import ExecuteData
from cozeloop.internal.stream.base_stream_reader import BaseStreamReader
from cozeloop.internal.stream.sse import ServerSentEvent

logger = logging.getLogger(__name__)


class ExecuteStreamReader(BaseStreamReader[ExecuteResult]):
    """
    Prompt执行结果的StreamReader实现
    
    继承自BaseStreamReader，实现具体的SSE数据解析逻辑
    将SSE事件中的数据解析为ExecuteResult对象
    支持同步和异步迭代器模式，提供完整的流式处理能力
    直接实现上下文管理器，无需单独的Context类
    """
    
    def __init__(self, stream_context, log_id: str = ""):
        """
        初始化ExecuteStreamReader
        
        Args:
            stream_context: 流上下文管理器
            log_id: 日志ID，用于错误追踪
        """
        self._stream_context = stream_context
        self._response = None
        self._context_entered = False
        self.log_id = log_id
        self._closed = False
        # 不调用super().__init__，因为还没有response对象
    
    def _parse_sse_data(self, sse: ServerSentEvent) -> Optional[ExecuteResult]:
        """
        解析SSE数据为ExecuteResult对象
        
        Args:
            sse: ServerSentEvent对象
            
        Returns:
            Optional[ExecuteResult]: 解析后的ExecuteResult对象，如果不需要返回则为None
        """
        # 跳过空数据
        if not sse.data or sse.data.strip() == "":
            return None
        
        # 跳过非data事件
        if sse.event and sse.event != "data":
            logger.debug(f"Skipping non-data event: {sse.event}")
            return None
        
        try:
            # 解析JSON数据
            data_dict = sse.json()
            
            # 验证数据结构
            if not isinstance(data_dict, dict):
                logger.warning(f"Invalid SSE data format, expected dict, got {type(data_dict)}")
                return None
            
            # 将字典转换为ExecuteData对象
            execute_data = ExecuteData.model_validate(data_dict)
            
            # 转换为ExecuteResult
            result = convert_execute_data_to_result(execute_data)
            
            logger.debug(f"Successfully parsed SSE data to ExecuteResult: {result}")
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse SSE data as JSON: {e}, data: {sse.data}")
            return None
        except ValueError as e:
            logger.warning(f"Failed to validate ExecuteData: {e}, data: {sse.data}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing SSE data: {e}, data: {sse.data}")
            return None
    
    def __enter__(self):
        """同步上下文管理器入口"""
        if not self._context_entered:
            self._response = self._stream_context.__enter__()            # 检查HTTP状态码
            if self._response.status_code != 200:
                try:
                    # 先读取完整响应内容
                    self._response.read()
                    
                    # 现在可以安全调用json()
                    error_data = self._response.json()
                    log_id = self._response.headers.get("x-tt-logid", "")
                    error_code = error_data.get('code', 0)
                    error_msg = error_data.get('msg', 'Unknown error')
                    # 确保关闭stream_context
                    self._stream_context.__exit__(None, None, None)
                    raise RemoteServiceError(self._response.status_code, error_code, error_msg, log_id)
                except Exception as e:
                    self._stream_context.__exit__(None, None, None)
                    if isinstance(e, RemoteServiceError):
                        raise
                    from cozeloop.internal.consts.error import InternalError
                    raise InternalError(f"Failed to parse error response: {e}")
            
            # 初始化BaseStreamReader的属性
            super().__init__(self._response, self.log_id)
            self._context_entered = True
        
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """同步上下文管理器出口"""
        self.close()
        if self._context_entered:
            return self._stream_context.__exit__(exc_type, exc_val, exc_tb)

    async def __aenter__(self):
        """异步上下文管理器入口"""
        if not self._context_entered:
            self._response = self._stream_context.__enter__()            # 检查HTTP状态码（同步版本逻辑）
            if self._response.status_code != 200:
                try:
                    # 先读取完整响应内容
                    await self._response.aread()
                    
                    # 现在可以安全调用json()
                    error_data = self._response.json()
                    log_id = self._response.headers.get("x-tt-logid", "")
                    error_code = error_data.get('code', 0)
                    error_msg = error_data.get('msg', 'Unknown error')
                    self._stream_context.__exit__(None, None, None)
                    raise RemoteServiceError(self._response.status_code, error_code, error_msg, log_id)
                except Exception as e:
                    self._stream_context.__exit__(None, None, None)
                    if isinstance(e, RemoteServiceError):
                        raise
                    from cozeloop.internal.consts.error import InternalError
                    raise InternalError(f"Failed to parse error response: {e}")
            
            # 初始化BaseStreamReader的属性
            super().__init__(self._response, self.log_id)
            self._context_entered = True
        
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.aclose()
        if self._context_entered:
            return self._stream_context.__exit__(exc_type, exc_val, exc_tb)
    
    def __iter__(self):
        """支持for循环直接读取"""
        if not self._context_entered:
            self.__enter__()
        return super().__iter__()

    def __aiter__(self):
        """支持async for循环直接读取"""
        # 注意：异步版本需要特殊处理
        return self._aiter_impl()

    async def _aiter_impl(self):
        """异步迭代器实现"""
        if not self._context_entered:
            await self.__aenter__()
        async for item in super().__aiter__():
            yield item
    
    def close(self) -> None:
        """关闭流"""
        self._closed = True
        # 如果还没有进入上下文，直接关闭stream_context
        if not self._context_entered:
            if hasattr(self._stream_context, '__exit__'):
                try:
                    self._stream_context.__exit__(None, None, None)
                except Exception:
                    pass
            return
        
        # 如果已经进入上下文，调用父类的close方法
        if hasattr(self, 'response'):
            super().close()
        else:
            # 如果response属性不存在，只关闭stream_context
            if hasattr(self._stream_context, '__exit__'):
                try:
                    self._stream_context.__exit__(None, None, None)
                except Exception:
                    pass

    async def aclose(self) -> None:
        """异步关闭流"""
        self._closed = True
        # 如果还没有进入上下文，直接关闭stream_context
        if not self._context_entered:
            if hasattr(self._stream_context, '__exit__'):
                try:
                    self._stream_context.__exit__(None, None, None)
                except Exception:
                    pass
            return
        
        # 如果已经进入上下文，调用父类的aclose方法
        if hasattr(self, 'response'):
            await super().aclose()
        else:
            # 如果response属性不存在，只关闭stream_context
            if hasattr(self._stream_context, '__exit__'):
                try:
                    self._stream_context.__exit__(None, None, None)
                except Exception:
                    pass