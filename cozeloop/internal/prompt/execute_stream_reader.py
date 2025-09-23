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
    StreamReader implementation for Prompt execution results
    
    Inherits from BaseStreamReader, implements specific SSE data parsing logic
    Parses data from SSE events into ExecuteResult objects
    Supports synchronous and asynchronous iterator patterns, providing complete streaming processing capabilities
    Directly implements context manager, no separate Context class needed
    """
    
    def __init__(self, stream_context, log_id: str = ""):
        """
        Initialize ExecuteStreamReader
        
        Args:
            stream_context: Stream context manager
            log_id: Log ID for error tracking
        """
        self._stream_context = stream_context
        self._response = None
        self._context_entered = False
        self.log_id = log_id
        self._closed = False
        # Don't call super().__init__() because there's no response object yet
    
    def _parse_sse_data(self, sse: ServerSentEvent) -> Optional[ExecuteResult]:
        """
        Parse SSE data into ExecuteResult object
        
        Args:
            sse: ServerSentEvent object
            
        Returns:
            Optional[ExecuteResult]: Parsed ExecuteResult object, None if no return needed
        """
        # Skip empty data
        if not sse.data or sse.data.strip() == "":
            return None
        
        # Skip non-data events
        if sse.event and sse.event != "data":
            logger.debug(f"Skipping non-data event: {sse.event}")
            return None
        
        try:
            # Parse JSON data
            data_dict = sse.json()
            
            # Validate data structure
            if not isinstance(data_dict, dict):
                logger.warning(f"Invalid SSE data format, expected dict, got {type(data_dict)}")
                return None
            
            # Convert dictionary to ExecuteData object
            execute_data = ExecuteData.model_validate(data_dict)
            
            # Convert to ExecuteResult
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
        """Synchronous context manager entry"""
        if not self._context_entered:
            self._response = self._stream_context.__enter__()            # Check HTTP status code
            if self._response.status_code != 200:
                try:
                    # Read complete response content first
                    self._response.read()
                    
                    # Now can safely call json()
                    error_data = self._response.json()
                    log_id = self._response.headers.get("x-tt-logid", "")
                    error_code = error_data.get('code', 0)
                    error_msg = error_data.get('msg', 'Unknown error')
                    # Ensure stream_context is closed
                    self._stream_context.__exit__(None, None, None)
                    raise RemoteServiceError(self._response.status_code, error_code, error_msg, log_id)
                except Exception as e:
                    self._stream_context.__exit__(None, None, None)
                    if isinstance(e, RemoteServiceError):
                        raise
                    from cozeloop.internal.consts.error import InternalError
                    raise InternalError(f"Failed to parse error response: {e}")
            
            # Initialize BaseStreamReader attributes
            super().__init__(self._response, self.log_id)
            self._context_entered = True
        
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Synchronous context manager exit"""
        self.close()
        if self._context_entered:
            return self._stream_context.__exit__(exc_type, exc_val, exc_tb)

    async def __aenter__(self):
        """Asynchronous context manager entry"""
        if not self._context_entered:
            self._response = await self._stream_context.__aenter__()            # Check HTTP status code (async version logic)
            if self._response.status_code != 200:
                try:
                    # Read complete response content first
                    await self._response.aread()
                    
                    # Now can safely call json()
                    error_data = self._response.json()
                    log_id = self._response.headers.get("x-tt-logid", "")
                    error_code = error_data.get('code', 0)
                    error_msg = error_data.get('msg', 'Unknown error')
                    await self._stream_context.__aexit__(None, None, None)
                    raise RemoteServiceError(self._response.status_code, error_code, error_msg, log_id)
                except Exception as e:
                    await self._stream_context.__aexit__(None, None, None)
                    if isinstance(e, RemoteServiceError):
                        raise
                    from cozeloop.internal.consts.error import InternalError
                    raise InternalError(f"Failed to parse error response: {e}")
            
            # Initialize BaseStreamReader attributes
            super().__init__(self._response, self.log_id)
            self._context_entered = True
        
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Asynchronous context manager exit"""
        await self.aclose()
        if self._context_entered:
            return await self._stream_context.__aexit__(exc_type, exc_val, exc_tb)
    
    def __iter__(self):
        """Support direct reading with for loop"""
        if not self._context_entered:
            self.__enter__()
        return super().__iter__()

    def __aiter__(self):
        """Support direct reading with async for loop"""
        # Note: Async version requires special handling
        return self._aiter_impl()

    async def _aiter_impl(self):
        """Async iterator implementation"""
        if not self._context_entered:
            await self.__aenter__()
        async for item in super().__aiter__():
            yield item
    
    def close(self) -> None:
        """Close stream"""
        self._closed = True
        # If context hasn't been entered yet, directly close stream_context
        if not self._context_entered:
            if hasattr(self._stream_context, '__exit__'):
                try:
                    self._stream_context.__exit__(None, None, None)
                except Exception:
                    pass
            return
        
        
        # If context has been entered, call parent class close method
        if hasattr(self, 'response'):
            super().close()
        else:
            # If response attribute doesn't exist, only close stream_contextt
            if hasattr(self._stream_context, '__exit__'):
                try:
                    self._stream_context.__exit__(None, None, None)
                except Exception:
                    pass

    async def aclose(self) -> None:
        """Asynchronously close stream"""
        self._closed = True
        # If context hasn't been entered yet, directly close stream_context
        if not self._context_entered:
            if hasattr(self._stream_context, '__aexit__'):
                try:
                    await self._stream_context.__aexit__(None, None, None)
                except Exception:
                    pass
            return
        
        # If context has been entered, call parent class aclose method
        if hasattr(self, 'response'):
            await super().aclose()
        else:
            # If response attribute doesn't exist, only close stream_context
            if hasattr(self._stream_context, '__aexit__'):
                try:
                    await self._stream_context.__aexit__(None, None, None)
                except Exception:
                    pass