from fastapi import APIRouter
from app.services.dataset_store import store
from app.services.eda_service import simple_eda

router = APIRouter(prefix="/eda", tags=["eda"])

@router.get("/{dataset_id}")
async def run_eda(dataset_id: str):
    df = store.get(dataset_id)
    if df is None:
        return {"error": "dataset not found"}
    
    return simple_eda(df)