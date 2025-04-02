# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from pydantic import BaseModel


class BaseResponse(BaseModel):
    code: int
    msg: str
