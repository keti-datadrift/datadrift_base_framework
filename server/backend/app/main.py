from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import datasets, eda, drift

app = FastAPI(title="On-prem Dataset Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router)
app.include_router(eda.router)
app.include_router(drift.router)

@app.get("/")
async def root():
    return {"message": "Dataset Analyzer Backend Running!"}