# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import contextlib
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


def go_safe(fn: callable):
    def wrapper():
        try:
            fn()
        except Exception as e:
            logger.error(f"goroutine panic: {e}\n{traceback.format_exc()}")

    with ThreadPoolExecutor() as executor:
        executor.submit(wrapper)