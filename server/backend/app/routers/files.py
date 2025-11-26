from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter(prefix="/files", tags=["files"])

@router.get("/raw")
def get_raw_file(path: str):
    # URL로 들어온 경로 인코딩 문제 해결
    safe_path = os.path.normpath(path)

    if not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(safe_path)