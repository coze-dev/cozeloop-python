# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
from typing import Any, Iterator, Optional


class ServerSentEvent:
    """
    Server-Sent Event (SSE) 数据结构
    
    封装SSE事件的各个字段：event, data, id, retry
    提供JSON解析功能
    """

    def __init__(
            self,
            *,
            event: str | None = None,
            data: str | None = None,
            id: str | None = None,
            retry: int | None = None,
    ) -> None:
        """
        初始化ServerSentEvent
        
        Args:
            event: 事件类型
            data: 事件数据
            id: 事件ID
            retry: 重试间隔（毫秒）
        """
        if data is None:
            data = ""

        self._id = id
        self._data = data
        self._event = event or None
        self._retry = retry

    @property
    def event(self) -> str | None:
        """获取事件类型"""
        return self._event

    @property
    def id(self) -> str | None:
        """获取事件ID"""
        return self._id

    @property
    def retry(self) -> int | None:
        """获取重试间隔"""
        return self._retry

    @property
    def data(self) -> str:
        """获取事件数据"""
        return self._data

    def json(self) -> Any:
        """
        将data字段解析为JSON对象
        
        Returns:
            解析后的JSON对象
            
        Raises:
            json.JSONDecodeError: 当data不是有效的JSON时
        """
        return json.loads(self.data)

    def __repr__(self) -> str:
        return f"ServerSentEvent(event={self.event}, data={self.data}, id={self.id}, retry={self.retry})"


class SSEDecoder:
    """
    Server-Sent Event (SSE) 解码器
    
    负责将字节流解码为ServerSentEvent对象
    支持SSE协议的完整规范，包括多行数据累积和各种字段处理
    """

    def __init__(self) -> None:
        """初始化SSE解码器"""
        self._event: Optional[str] = None
        self._data: list[str] = []
        self._last_event_id: Optional[str] = None
        self._retry: Optional[int] = None

    def iter_bytes(self, iterator: Iterator[bytes]) -> Iterator[ServerSentEvent]:
        """
        同步解码字节流为SSE事件
        
        Args:
            iterator: 字节流迭代器
            
        Yields:
            ServerSentEvent: 解码后的SSE事件
        """
        for chunk in self._iter_chunks(iterator):
            # 先分割再解码，确保splitlines()只使用\r和\n
            for raw_line in chunk.splitlines():
                line = raw_line.decode("utf-8")
                sse = self.decode(line)
                if sse:
                    yield sse

    def _iter_chunks(self, iterator: Iterator[bytes]) -> Iterator[bytes]:
        """
        同步处理字节块，确保完整的SSE消息
        
        Args:
            iterator: 字节流迭代器
            
        Yields:
            bytes: 完整的SSE消息块
        """
        data = b""
        for chunk in iterator:
            for line in chunk.splitlines(keepends=True):
                data += line
                if data.endswith((b"\r\r", b"\n\n", b"\r\n\r\n")):
                    yield data
                    data = b""
        if data:
            yield data

    def decode(self, line: str) -> Optional[ServerSentEvent]:
        """
        解码单行SSE数据
        
        Args:
            line: SSE数据行
            
        Returns:
            Optional[ServerSentEvent]: 解码后的SSE事件，如果未完成则返回None
        """
        if not line:
            # 空行表示事件结束，构造SSE事件
            if not self._event and not self._data and not self._last_event_id and self._retry is None:
                return None

            sse = ServerSentEvent(
                event=self._event,
                data="\n".join(self._data),
                id=self._last_event_id,
                retry=self._retry,
            )

            # 重置状态，准备下一个事件
            self._event = None
            self._data = []
            self._retry = None

            return sse

        # 解析字段
        fieldname, _, value = line.partition(":")

        # 去掉值前面的空格
        if value.startswith(" "):
            value = value[1:]

        # 处理各种字段
        if fieldname == "event":
            self._event = value
        elif fieldname == "data":
            self._data.append(value)
        elif fieldname == "id":
            # 根据SSE规范，id字段不能包含null字符
            if "\0" not in value:
                self._last_event_id = value
        elif fieldname == "retry":
            try:
                self._retry = int(value)
            except (TypeError, ValueError):
                # 忽略无效的retry值
                pass
        # 其他字段被忽略

        return None
