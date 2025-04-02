# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import List, Optional
from pydantic import BaseModel

class RetrieverInput(BaseModel):
    query: Optional[str] = None

class RetrieverDocument(BaseModel):
    id: Optional[str] = None
    index: Optional[str] = None
    content: str
    vector: Optional[List[float]] = None
    score: float

class RetrieverOutput(BaseModel):
    documents: Optional[List[RetrieverDocument]] = None

class RetrieverCallOption(BaseModel):
    top_k: Optional[int] = None
    min_score: Optional[float] = None
    filter: Optional[str] = None