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
    Generic StreamReader base class
    
    Based on Fornax's Stream design pattern, integrates SSEDecoder for SSE data decoding
    Supports synchronous and asynchronous iterator patterns, implements context manager
    Provides unified error handling mechanism and resource management
    """
    
    def __init__(self, response: httpx.Response, log_id: str = ""):
        """
        Initialize BaseStreamReader
        
        Args:
            response: httpx response object
            log_id: Log ID for error tracking
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
        Parse SSE data into business object, must be implemented by subclasses
        
        Args:
            sse: ServerSentEvent object
            
        Returns:
            Optional[T]: Parsed business object, None if no return needed
        """
        pass
    
    def _iter_events(self) -> Iterator[ServerSentEvent]:
        """
        Iterate SSE events
        
        Yields:
            ServerSentEvent: Decoded SSE events
        """
        try:
            for sse in self._decoder.iter_bytes(self.response.iter_bytes()):
                yield sse
        except Exception as e:
            logger.error(f"Error iterating SSE events: {e}")
            raise InternalError(f"Failed to decode SSE stream: {e}")
    
    async def _aiter_events(self) -> AsyncIterator[ServerSentEvent]:
        """
        Asynchronously iterate SSE events
        
        Yields:
            ServerSentEvent: Decoded SSE events
        """
        try:
            # Use async iterator
            async for sse in self._decoder.aiter_bytes(self.response.aiter_bytes()):
                yield sse
        except Exception as e:
            logger.error(f"Error async iterating SSE events: {e}")
            raise InternalError(f"Failed to decode SSE stream: {e}")
    
    def _handle_sse_error(self, sse: ServerSentEvent) -> None:
        """
        Handle errors in SSE events
        
        Args:
            sse: ServerSentEvent object
            
        Raises:
            RemoteServiceError: When error event is detected
        """
        if not sse.data:
            return
        
        try:
            data = sse.json()
            
            # Check if contains error information
            if isinstance(data, dict):
                # Check error code field
                if 'code' in data and data['code'] != 0:
                    error_code = data.get('code', 0)
                    error_msg = data.get('msg', 'Unknown error')
                    raise RemoteServiceError(200, error_code, error_msg, self.log_id)
                
                # Check error field
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
            # If not JSON format, ignore error checking
            pass
        except RemoteServiceError:
            # Re-raise RemoteServiceError
            raise
        except Exception as e:
            logger.warning(f"Error checking SSE error: {e}")
    
    def __stream__(self) -> Iterator[T]:
        """
        Core stream processing logic
        
        Yields:
            T: Parsed business objects
        """
        if self._closed:
            return
        
        try:
            for sse in self._iter_events():
                if self._closed:
                    break
                
                # Check for errors
                self._handle_sse_error(sse)
                
                # Parse data
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
        Asynchronous core stream processing logic
        
        Yields:
            T: Parsed business objects
        """
        if self._closed:
            return
        
        try:
            async for sse in self._aiter_events():
                if self._closed:
                    break
                
                # Check for errors
                self._handle_sse_error(sse)
                
                # Parse data
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
    
    # Synchronous iterator interface
    def __iter__(self) -> Iterator[T]:
        """Support synchronous iteration - direct reading with for loop"""
        if self._sync_iterator is None:
            self._sync_iterator = self.__stream__()
        return self._sync_iterator
    
    def __next__(self) -> T:
        """Support next() function call"""
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
    
    # Asynchronous iterator interface
    def __aiter__(self) -> AsyncIterator[T]:
        """Support asynchronous iteration - direct reading with async for loop"""
        if self._async_iterator is None:
            self._async_iterator = self.__astream__()
        return self._async_iterator
    
    async def __anext__(self) -> T:
        """Support async next() call"""
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
    
    # Context manager interface
    def __enter__(self) -> BaseStreamReader[T]:
        """Synchronous context manager entry"""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Synchronous context manager exit"""
        self.close()
    
    async def __aenter__(self) -> BaseStreamReader[T]:
        """Asynchronous context manager entry"""
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Asynchronous context manager exit"""
        await self.aclose()
    
    # Resource management
    def close(self) -> None:
        """Close stream"""
        self._closed = True
        if hasattr(self.response, 'close'):
            self.response.close()
    
    async def aclose(self) -> None:
        """Asynchronously close stream"""
        self._closed = True
        if hasattr(self.response, 'aclose'):
            await self.response.aclose()
    
    @property
    def closed(self) -> bool:
        """Check if stream is closed"""
        return self._closed