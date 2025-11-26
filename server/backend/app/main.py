from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from .routers import datasets, eda, drift

# 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hybrid Dataset Analyzer")

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
def root():
    return {"status": "ok"}