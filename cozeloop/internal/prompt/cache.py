# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import threading
from typing import List, Optional, Tuple

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from cachetools import LFUCache

from cozeloop.entities import Prompt
from cozeloop.internal.prompt.converter import _convert_prompt
from cozeloop.internal.prompt.openapi import PromptQuery, OpenAPIClient

logger = logging.getLogger(__name__)

class PromptCache:
    def __init__(self, workspace_id: str,
                 openapi_client: Optional[OpenAPIClient] = None,
                 *,
                 max_size: int = 100,
                 refresh_interval: int = 60,
                 auto_refresh: bool = False):
        """Initialize prompt cache
        
        Args:
            max_size: Maximum cache capacity
            refresh_interval: Refresh interval (seconds)
            auto_refresh: Whether to automatically start refresh task
        """
        self.workspace_id = workspace_id
        self.cache = LFUCache(maxsize=max_size)
        self._scheduler = None
        self.refresh_interval = refresh_interval
        self.auto_refresh = auto_refresh
        self.openapi_client = openapi_client
        self._lock = threading.Lock()
        
        # If auto refresh and callback function are set, try to start refresh task
        if auto_refresh and self.openapi_client is not None:
            self._start_refresh_task()

    def get(self, prompt_key: str, version: str, label: str = '') -> Optional['Prompt']:
        cache_key = self._get_cache_key(prompt_key, version, label)
        return self.cache.get(cache_key)

    def set(self, prompt_key: str, version: str, label: str, value: 'Prompt') -> None:
        cache_key = self._get_cache_key(prompt_key, version, label)
        self.cache[cache_key] = value

    def get_all_prompt_queries(self) -> List[Tuple[str, str, str]]:
        result = []
        for cache_key in self.cache.keys():
            parsed = self._parse_cache_key(cache_key)
            if parsed:
                result.append(parsed)
        return result

    def _get_cache_key(self, prompt_key: str, version: str, label: str = '') -> str:
        return f"prompt_hub:{prompt_key}:{version}:{label}"

    def _parse_cache_key(self, cache_key: str) -> Optional[Tuple[str, str, str]]:
        parts = cache_key.split(':')
        if len(parts) == 4:
            return parts[1], parts[2], parts[3]
        return None

    def _start_refresh_task(self):
        """Start timed refresh task, ensuring it's executed only once in multi-threaded environment"""
        with self._lock:
            if self._scheduler is not None:
                return  # Refresh task already started

            # Create scheduler
            self._scheduler = BackgroundScheduler()

            # Add scheduled task to execute at specified intervals
            self._scheduler.add_job(
                self._refresh_all_prompts,
                trigger=IntervalTrigger(seconds=self.refresh_interval),
                id='refresh_prompts',
                replace_existing=True
            )

            # Start scheduler
            self._scheduler.start()
            # logger.info(f"Prompt refresh scheduler started with interval of {self.refresh_interval} seconds")

    def _refresh_all_prompts(self):
        """Refresh all cached prompts"""
        try:
            # Get all cached prompt_keys and versions
            key_tuples = self.get_all_prompt_queries()
            queries = [PromptQuery(prompt_key=prompt_key, version=version, label=label) for prompt_key, version, label in key_tuples]
            try:
                results = self.openapi_client.mpull_prompt(self.workspace_id, queries)
                for result in results:
                    prompt_key, version, label = result.query.prompt_key, result.query.version, result.query.label
                    self.set(prompt_key, version, label, _convert_prompt(result.prompt))
            except Exception as e:
                logger.error(f"Error refreshing prompts: {e}")

        except Exception as e:
            # Handle exceptions without interrupting the scheduler
            logger.error(f"Error in refresh task: {e}")

    def stop_refresh_task(self):
        """Stop refresh task"""
        with self._lock:
            if self._scheduler and self._scheduler.running:
                self._scheduler.shutdown(wait=False)
                self._scheduler = None
                # logger.info("Prompt refresh scheduler stopped")

    def __del__(self):
        """Clean up resources"""
        self.stop_refresh_task()
