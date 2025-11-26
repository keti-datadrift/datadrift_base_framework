from fastapi import APIRouter
from pydantic import BaseModel

from app.services.dataset_store import store
from app.services.drift_service import simple_drift

router = APIRouter(prefix="/drift", tags=["drift"])

class DriftRequest(BaseModel):
    base_id: str
    target_id: str

@router.post("/")
async def compute_drift(req: DriftRequest):
    base = store.get(req.base_id)
    target = store.get(req.target_id)

    if base is None or target is None:
        return {"error": "dataset not found"}

    return simple_drift(base, target)