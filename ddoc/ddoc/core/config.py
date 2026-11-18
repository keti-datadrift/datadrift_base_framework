from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, Dict, Any

class RuntimeConfig(BaseModel):
    plugins: Optional[list[str]] = None

class DDConfig(BaseModel):
    runtime: RuntimeConfig = RuntimeConfig()
    tracking: Dict[str, Any] = {}
    pipelines: Dict[str, Any] = {}