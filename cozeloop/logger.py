# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import sys

_logger = logging.getLogger('cozeloop')


def set_log_level(level: int):
    """
    Set logging level.
    :param level: logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR
    :return:
    """
    _logger.setLevel(level)
    for handler in _logger.handlers:
        handler.setLevel(level)


def add_log_handler(handler: logging.Handler):
    """
    Add custom logging handler and remove default stdout handler.
    :param handler: custom logging handler
    :return:
    """
    _logger.removeHandler(_default_handler)
    _logger.addHandler(handler)


_default_handler = logging.StreamHandler(sys.stdout)
_default_handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(filename)s:%(lineno)d [%(levelname)s] [cozeloop] %(message)s'))
_logger.addHandler(_default_handler)
_logger.setLevel(logging.WARN)
