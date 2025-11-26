from pydantic import BaseModel
from typing import Any, Optional

class DatasetSchema(BaseModel):
    id: str
    name: str
    type: str
    rows: int
    cols: int
    missing_rate: Optional[Any]
    preview: Optional[Any]
    dvc_path: str
    version: str

    class Config:
        orm_mode = True
        json_encoders = {
            float: lambda x: None if (x != x or x in [float("inf"), float("-inf")]) else x
        }