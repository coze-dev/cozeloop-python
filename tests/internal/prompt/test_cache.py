# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch

import pytest
from cachetools import LFUCache

from cozeloop.entities import Prompt
from cozeloop.internal.prompt.cache import PromptCache
from cozeloop.internal.prompt.openapi import PromptQuery, OpenAPIClient


@pytest.fixture
def mock_openapi_client():
    client = MagicMock(spec=OpenAPIClient)
    return client


@pytest.fixture
def prompt_cache(mock_openapi_client):
    return PromptCache(
        workspace_id="test_workspace",
        openapi_client=mock_openapi_client,
        max_size=10,
        refresh_interval=30,
        auto_refresh=False
    )


def test_init(mock_openapi_client):
    # Test basic initialization
    cache = PromptCache(
        workspace_id="test_workspace",
        openapi_client=mock_openapi_client,
        max_size=20,
        refresh_interval=45,
        auto_refresh=False
    )
    
    assert cache.workspace_id == "test_workspace"
    assert cache.openapi_client == mock_openapi_client
    assert cache.refresh_interval == 45
    assert cache.auto_refresh is False
    assert isinstance(cache.cache, LFUCache)
    assert cache.cache.maxsize == 20


def test_get_set(prompt_cache):
    mock_prompt = MagicMock(spec=Prompt)
    
    # Cache should be empty initially
    assert prompt_cache.get("test_key", "v1") is None
    
    # Set cache item
    prompt_cache.set("test_key", "v1", mock_prompt)
    
    # Verify cache retrieval
    assert prompt_cache.get("test_key", "v1") == mock_prompt


def test_get_all_prompt_queries(prompt_cache):
    # Set multiple cache items
    mock_prompt1 = MagicMock(spec=Prompt)
    mock_prompt2 = MagicMock(spec=Prompt)
    
    prompt_cache.set("key1", "v1", mock_prompt1)
    prompt_cache.set("key2", "v2", mock_prompt2)
    
    # Get all queries
    queries = prompt_cache.get_all_prompt_queries()
    
    # Verify results
    assert len(queries) == 2
    assert ("key1", "v1") in queries
    assert ("key2", "v2") in queries


def test_cache_key_methods(prompt_cache):
    # Test cache key generation
    cache_key = prompt_cache._get_cache_key("test_prompt", "v3")
    assert cache_key == "prompt_hub:test_prompt:v3"
    
    # Test cache key parsing
    parsed = prompt_cache._parse_cache_key(cache_key)
    assert parsed == ("test_prompt", "v3")
    
    # Test invalid cache key
    assert prompt_cache._parse_cache_key("invalid_key") is None


@patch('cozeloop.internal.prompt.cache.BackgroundScheduler')
def test_start_refresh_task(mock_scheduler_class, mock_openapi_client):
    mock_scheduler = MagicMock()
    mock_scheduler_class.return_value = mock_scheduler
    
    # Create cache with auto-refresh enabled
    cache = PromptCache(
        workspace_id="test_workspace",
        openapi_client=mock_openapi_client,
        refresh_interval=60,
        auto_refresh=True
    )
    
    # Verify scheduler was started
    mock_scheduler.add_job.assert_called_once()
    mock_scheduler.start.assert_called_once()


def test_refresh_all_prompts(prompt_cache, mock_openapi_client):
    # Setup mock data
    mock_prompt1 = MagicMock(spec=Prompt)
    mock_prompt2 = MagicMock(spec=Prompt)
    
    prompt_cache.set("key1", "v1", mock_prompt1)
    prompt_cache.set("key2", "v2", mock_prompt2)
    
    # Setup mpull_prompt return values
    mock_result1 = MagicMock()
    mock_result1.query.prompt_key = "key1"
    mock_result1.query.version = "v1"
    mock_result1.prompt = MagicMock()  # This will be converted by _convert_prompt
    
    mock_result2 = MagicMock()
    mock_result2.query.prompt_key = "key2"
    mock_result2.query.version = "v2"
    mock_result2.prompt = MagicMock()
    
    mock_openapi_client.mpull_prompt.return_value = [mock_result1, mock_result2]
    
    # Mock _convert_prompt function
    with patch('cozeloop.internal.prompt.cache._convert_prompt') as mock_convert:
        mock_convert.side_effect = lambda x: MagicMock(spec=Prompt)
        
        # Execute refresh
        prompt_cache._refresh_all_prompts()
        
        # Verify mpull_prompt was called
        mock_openapi_client.mpull_prompt.assert_called_once()
        # Verify call parameters contain correct workspace and queries
        args, kwargs = mock_openapi_client.mpull_prompt.call_args
        assert args[0] == "test_workspace"
        assert len(args[1]) == 2
        assert all(isinstance(q, PromptQuery) for q in args[1])


def test_refresh_error_handling(prompt_cache, mock_openapi_client):
    # Setup mock data
    mock_prompt = MagicMock(spec=Prompt)
    prompt_cache.set("key1", "v1", mock_prompt)
    
    # Setup mpull_prompt to raise exception
    mock_openapi_client.mpull_prompt.side_effect = Exception("API error")
    
    # Execute refresh, should not raise exception
    prompt_cache._refresh_all_prompts()
    
    # Verify call
    mock_openapi_client.mpull_prompt.assert_called_once()


def test_stop_refresh_task(prompt_cache):
    # Mock scheduler
    mock_scheduler = MagicMock()
    prompt_cache._scheduler = mock_scheduler
    mock_scheduler.running = True
    
    # Stop refresh task
    prompt_cache.stop_refresh_task()
    
    # Verify scheduler was shutdown
    mock_scheduler.shutdown.assert_called_once_with(wait=False)
    assert prompt_cache._scheduler is None


def test_del_method(prompt_cache):
    # Mock scheduler
    mock_scheduler = MagicMock()
    prompt_cache._scheduler = mock_scheduler
    mock_scheduler.running = True
    
    # Mock object destruction
    with patch.object(prompt_cache, 'stop_refresh_task') as mock_stop:
        prompt_cache.__del__()
        
        # Verify stop_refresh_task was called
        mock_stop.assert_called_once() 