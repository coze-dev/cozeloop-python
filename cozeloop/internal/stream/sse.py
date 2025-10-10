# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
from typing import Any, Iterator, Optional, AsyncIterator, Union


class ServerSentEvent:
    """
    Server-Sent Event (SSE) data structure
    
    Encapsulates various fields of SSE events: event, data, id, retry
    Provides JSON parsing functionality
    """

    def __init__(
            self,
            *,
            event: Union[str, None] = None,
            data: Union[str, None] = None,
            id: Union[str, None] = None,
            retry: Union[int, None] = None,
    ) -> None:
        """
        Initialize ServerSentEvent
        
        Args:
            event: Event type
            data: Event data
            id: Event ID
            retry: Retry interval (milliseconds)
        """
        if data is None:
            data = ""

        self._id = id
        self._data = data
        self._event = event or None
        self._retry = retry

    @property
    def event(self) -> Union[str, None]:
        """Get event type"""
        return self._event

    @property
    def id(self) -> Union[str, None]:
        """Get event ID"""
        return self._id

    @property
    def retry(self) -> Union[int, None]:
        """Get retry interval"""
        return self._retry

    @property
    def data(self) -> str:
        """Get event data"""
        return self._data

    def json(self) -> Any:
        """
        Parse data field as JSON object
        
        Returns:
            Parsed JSON object
            
        Raises:
            json.JSONDecodeError: When data is not valid JSON
        """
        return json.loads(self.data)

    def __repr__(self) -> str:
        return f"ServerSentEvent(event={self.event}, data={self.data}, id={self.id}, retry={self.retry})"


class SSEDecoder:
    """
    Server-Sent Event (SSE) decoder
    
    Responsible for decoding byte streams into ServerSentEvent objects
    Supports complete SSE protocol specification, including multi-line data accumulation and various field processing
    """

    def __init__(self) -> None:
        """Initialize SSE decoder"""
        self._event: Optional[str] = None
        self._data: list[str] = []
        self._last_event_id: Optional[str] = None
        self._retry: Optional[int] = None

    def iter_bytes(self, iterator: Iterator[bytes]) -> Iterator[ServerSentEvent]:
        """
        Synchronously decode byte stream into SSE events
        
        Args:
            iterator: Byte stream iterator
            
        Yields:
            ServerSentEvent: Decoded SSE events
        """
        for chunk in self._iter_chunks(iterator):
            # Split first then decode, ensure splitlines() only uses \r and \n
            for raw_line in chunk.splitlines():
                line = raw_line.decode("utf-8")
                sse = self.decode(line)
                if sse:
                    yield sse

    def _iter_chunks(self, iterator: Iterator[bytes]) -> Iterator[bytes]:
        """
        Synchronously process byte chunks, ensuring complete SSE messages
        
        Args:
            iterator: Byte stream iterator
            
        Yields:
            bytes: Complete SSE message chunks
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

    async def aiter_bytes(self, iterator: AsyncIterator[bytes]) -> AsyncIterator[ServerSentEvent]:
        """
        Asynchronously decode byte stream into SSE events
        
        Args:
            iterator: Asynchronous byte stream iterator
            
        Yields:
            ServerSentEvent: Decoded SSE events
        """
        async for chunk in self._aiter_chunks(iterator):
            # Split first then decode, ensure splitlines() only uses \r and \n
            for raw_line in chunk.splitlines():
                line = raw_line.decode("utf-8")
                sse = self.decode(line)
                if sse:
                    yield sse

    async def _aiter_chunks(self, iterator: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
        """
        Asynchronously process byte chunks, ensuring complete SSE messages
        
        Args:
            iterator: Asynchronous byte stream iterator
            
        Yields:
            bytes: Complete SSE message chunks
        """
        data = b""
        async for chunk in iterator:
            for line in chunk.splitlines(keepends=True):
                data += line
                if data.endswith((b"\r\r", b"\n\n", b"\r\n\r\n")):
                    yield data
                    data = b""
        if data:
            yield data

    def decode(self, line: str) -> Optional[ServerSentEvent]:
        """
        Decode single line SSE data
        
        Args:
            line: SSE data line
            
        Returns:
            Optional[ServerSentEvent]: Decoded SSE event, None if not complete
        """
        if not line:
            # Empty line indicates end of event, construct SSE event
            if not self._event and not self._data and not self._last_event_id and self._retry is None:
                return None

            sse = ServerSentEvent(
                event=self._event,
                data="\n".join(self._data),
                id=self._last_event_id,
                retry=self._retry,
            )

            # Reset state, prepare for next event
            self._event = None
            self._data = []
            self._retry = None

            return sse

        # Parse fields
        fieldname, _, value = line.partition(":")

        # Remove leading space from value
        # 去掉值前面的空格
        if value.startswith(" "):
            value = value[1:]

        # Process various fields
        if fieldname == "event":
            self._event = value
        elif fieldname == "data":
            self._data.append(value)
        elif fieldname == "id":
            # According to SSE specification, id field cannot contain null characters
            if "\0" not in value:
                self._last_event_id = value
        elif fieldname == "retry":
            try:
                self._retry = int(value)
            except (TypeError, ValueError):
                # Ignore invalid retry values
                pass
        # Other fields are ignored

        return None