import os
import uuid
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Dataset, DriftResult, AnalysisTask, EDAResult
from app.services.drift_service import run_drift
from app.services.task_queue import get_task_queue
from app.services.progress_tracker import TimeEstimator

router = APIRouter(prefix="/drift", tags=["drift"])


# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Request Body
class DriftRequest(BaseModel):
    base_id: str
    target_id: str
    force: Optional[bool] = False  # 강제 재분석 옵션


# -------------------------------
# COMMON Response Wrapper
# -------------------------------
def wrap_drift_response(
    base: Dataset, 
    target: Dataset, 
    result: dict, 
    version: str,
    cached: bool = False
):
    """
    drift_service.py의 결과(result)를 안정적인 JSON 형태로 감싸주는 공통 포맷
    """

    return {
        "version": version,
        "cached": cached,
        "meta": {
            "base": {
                "id": base.id,
                "name": base.name,
                "type": base.type,
                "dvc_path": base.dvc_path,
            },
            "target": {
                "id": target.id,
                "name": target.name,
                "type": target.type,
                "dvc_path": target.dvc_path,
            },
        },
        "result": result,   # drift_service.py 의 핵심 분석값
    }


def _get_eda_cache(db: Session, dataset_id: str) -> dict:
    """
    데이터셋의 EDA 캐시(속성 분석, 임베딩)를 조회합니다.
    
    Returns:
        dict: {image_analysis: {...}, clustering: {...}} 또는 빈 dict
    """
    eda_result = db.query(EDAResult).filter(EDAResult.dataset_id == dataset_id).first()
    
    if not eda_result or not eda_result.stats:
        return {}
    
    cache = {}
    
    # 이미지 속성 분석 캐시
    if eda_result.stats.get("image_analysis"):
        cache["image_analysis"] = eda_result.stats["image_analysis"]
    
    # 클러스터링 캐시 (임베딩 포함)
    if eda_result.stats.get("clustering"):
        cache["clustering"] = eda_result.stats["clustering"]
    
    return cache


def _get_or_create_drift_result(
    db: Session,
    base: Dataset,
    target: Dataset,
    force: bool = False
) -> tuple[dict, bool]:
    """
    드리프트 분석 결과를 캐시에서 조회하거나 새로 생성합니다.
    
    EDA 분석 결과(속성, 임베딩)가 있으면 재사용하여 속도를 향상시킵니다.
    
    Returns:
        tuple: (분석 결과 dict, 캐시 여부 bool)
    """
    # 1) 드리프트 결과 캐시 조회 (force가 아닐 때만)
    if not force:
        cached = db.query(DriftResult).filter(
            DriftResult.base_id == base.id,
            DriftResult.target_id == target.id
        ).first()
        
        if cached and cached.summary:
            return cached.summary, True
    
    # 2) EDA 캐시 조회 (속성 분석, 임베딩)
    base_cache = _get_eda_cache(db, base.id)
    target_cache = _get_eda_cache(db, target.id)
    
    # 캐시 상태 로깅
    print(f"📊 드리프트 분석 - EDA 캐시 상태:")
    print(f"   Base ({base.name}): 속성={bool(base_cache.get('image_analysis'))}, 임베딩={bool(base_cache.get('clustering', {}).get('embeddings'))}")
    print(f"   Target ({target.name}): 속성={bool(target_cache.get('image_analysis'))}, 임베딩={bool(target_cache.get('clustering', {}).get('embeddings'))}")
    
    # 3) 분석 수행 (EDA 캐시 전달)
    result = run_drift(
        base.dvc_path, 
        target.dvc_path,
        base_cache=base_cache,
        target_cache=target_cache
    )
    
    # 4) 결과 저장 (upsert)
    existing = db.query(DriftResult).filter(
        DriftResult.base_id == base.id,
        DriftResult.target_id == target.id
    ).first()
    
    # overall 점수 추출 (advanced_drift에서 가져오거나 기본값)
    overall_score = None
    if "advanced_drift" in result and result["advanced_drift"]:
        ensemble = result["advanced_drift"].get("ensemble", {})
        overall_score = ensemble.get("overall_score")
    
    if existing:
        # 업데이트
        existing.summary = result
        existing.feature_drift = result.get("drift") or result.get("advanced_drift")
        existing.overall = overall_score
    else:
        # 새로 생성
        drift_result = DriftResult(
            id=str(uuid.uuid4()),
            base_id=base.id,
            target_id=target.id,
            summary=result,
            feature_drift=result.get("drift") or result.get("advanced_drift"),
            overall=overall_score,
        )
        db.add(drift_result)
    
    db.commit()
    
    return result, False


# ============================================================
# Drift V1
# ============================================================

@router.post("/")
def drift(req: DriftRequest, db: Session = Depends(get_db)):
    """
    두 데이터셋 간의 드리프트 분석을 수행합니다.
    
    - 캐시된 결과가 있으면 캐시에서 반환
    - 캐시가 없거나 force=true이면 새로 분석 후 저장
    """
    base = db.query(Dataset).filter(Dataset.id == req.base_id).first()
    target = db.query(Dataset).filter(Dataset.id == req.target_id).first()

    if not base or not target:
        raise HTTPException(status_code=404, detail="Dataset not found")

    result, cached = _get_or_create_drift_result(db, base, target, req.force or False)

    return wrap_drift_response(base, target, result, version="v1", cached=cached)


# ============================================================
# Drift V2 (확장 포맷)
# ============================================================

@router.post("/v2")
def drift_v2(req: DriftRequest, db: Session = Depends(get_db)):
    """
    두 데이터셋 간의 드리프트 분석을 수행합니다. (V2 포맷)
    
    - 캐시된 결과가 있으면 캐시에서 반환
    - 캐시가 없거나 force=true이면 새로 분석 후 저장
    """
    base = db.query(Dataset).filter(Dataset.id == req.base_id).first()
    target = db.query(Dataset).filter(Dataset.id == req.target_id).first()

    if not base or not target:
        raise HTTPException(status_code=404, detail="Dataset not found")

    result, cached = _get_or_create_drift_result(db, base, target, req.force or False)

    return wrap_drift_response(base, target, result, version="v2", cached=cached)


# ============================================================
# 작업 상태 조회
# ============================================================

@router.get("/task/{task_id}")
def get_drift_task_status(task_id: str, db: Session = Depends(get_db)):
    """드리프트 분석 작업의 상태를 조회합니다."""
    task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": task.id,
        "dataset_id": task.dataset_id,
        "target_id": task.target_id,
        "task_type": task.task_type,
        "status": task.status,
        "progress": task.progress,
        "message": task.message,
        "error": task.error,
        "metadata": task.task_metadata,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


# ============================================================
# 비동기 드리프트 분석
# ============================================================

@router.post("/async")
def drift_async(req: DriftRequest, db: Session = Depends(get_db)):
    """
    드리프트 분석을 비동기로 실행합니다 (중복 실행 방지).
    
    Returns:
        - status: queued | already_running | completed
        - task_id: 작업 ID (폴링/WebSocket 연결용)
    """
    # 1) 데이터셋 확인
    base = db.query(Dataset).filter(Dataset.id == req.base_id).first()
    target = db.query(Dataset).filter(Dataset.id == req.target_id).first()
    
    if not base or not target:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    task_queue = get_task_queue()
    
    # 2) 이미 실행 중인지 확인
    existing_task_id = task_queue.is_running(req.base_id, "drift", req.target_id)
    if existing_task_id:
        return {
            "status": "already_running",
            "task_id": existing_task_id,
            "message": "이미 드리프트 분석이 진행 중입니다."
        }
    
    # 3) 캐시 확인 (force가 아닐 때만)
    if not req.force:
        cached = db.query(DriftResult).filter(
            DriftResult.base_id == req.base_id,
            DriftResult.target_id == req.target_id
        ).first()
        
        if cached and cached.summary:
            return {
                "status": "completed",
                "cached": True,
                "message": "이미 분석 결과가 존재합니다."
            }
    
    # 4) 새 작업 생성
    task_id = str(uuid.uuid4())
    
    # 예상 시간 계산 (ZIP 데이터셋의 경우 이미지 파일 수 기반)
    estimated_time = None
    total_files = 0
    
    if base.type.lower() == "zip" and target.type.lower() == "zip":
        # 이미지 파일 수 추정
        from app.services.eda_service import collect_image_files
        
        base_dir = base.dvc_path
        target_dir = target.dvc_path
        
        for f in os.listdir(base_dir):
            if f.lower().endswith(".zip"):
                extracted_dir = os.path.join(base_dir, f) + "_extracted"
                if os.path.isdir(extracted_dir):
                    total_files += len(collect_image_files(extracted_dir))
                break
        
        for f in os.listdir(target_dir):
            if f.lower().endswith(".zip"):
                extracted_dir = os.path.join(target_dir, f) + "_extracted"
                if os.path.isdir(extracted_dir):
                    total_files += len(collect_image_files(extracted_dir))
                break
        
        estimated_time = TimeEstimator.estimate_time("drift", total_files)
    
    task = AnalysisTask(
        id=task_id,
        dataset_id=req.base_id,
        target_id=req.target_id,
        task_type="drift",
        status="pending",
        progress=0.0,
        message="대기 중...",
        task_metadata={
            "total_files": total_files,
            "estimated_seconds": estimated_time,
            "estimated_formatted": TimeEstimator.format_time(estimated_time),
        }
    )
    db.add(task)
    db.commit()
    
    # 5) 작업 큐에 등록
    if not task_queue.start_task(task_id, req.base_id, "drift", req.target_id):
        return {
            "status": "already_running",
            "task_id": task_queue.is_running(req.base_id, "drift", req.target_id),
            "message": "이미 드리프트 분석이 진행 중입니다."
        }
    
    # 6) 백그라운드에서 실행
    task_queue.submit_task(
        _run_drift_task,
        task_id,
        req.base_id,
        req.target_id,
        base.dvc_path,
        target.dvc_path,
        req.force or False
    )
    
    return {
        "status": "queued",
        "task_id": task_id,
        "message": "드리프트 분석 작업이 시작되었습니다.",
        "estimated_seconds": estimated_time,
        "estimated_formatted": TimeEstimator.format_time(estimated_time),
    }


# ============================================================
# 백그라운드 작업 실행 함수
# ============================================================

def _run_drift_task(
    task_id: str, 
    base_id: str, 
    target_id: str,
    base_path: str,
    target_path: str,
    force: bool
):
    """백그라운드에서 드리프트 분석 실행 (EDA 캐시 활용)"""
    from app.services.progress_tracker import ProgressTracker
    
    db = SessionLocal()
    task_queue = get_task_queue()
    
    try:
        # 상태 업데이트: 시작
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if task:
            task.status = "in_progress"
            task.started_at = datetime.utcnow()
            task.message = "드리프트 분석 시작..."
            task.progress = 0.1
            db.commit()
        
        # 진행률 업데이트 함수 (예외 처리 포함)
        def update_progress(progress: float, message: str):
            nonlocal task
            try:
                task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
                if task:
                    task.progress = progress
                    task.message = message
                    db.commit()
            except Exception as e:
                db.rollback()
                print(f"⚠️ update_progress DB 오류: {e}")
        
        update_progress(0.15, "EDA 캐시 조회 중...")
        
        # EDA 캐시 조회
        base_cache = _get_eda_cache(db, base_id)
        target_cache = _get_eda_cache(db, target_id)
        
        # 캐시 상태 로깅
        base_has_attrs = bool(base_cache.get('image_analysis'))
        base_has_embs = bool(base_cache.get('clustering', {}).get('embeddings'))
        target_has_attrs = bool(target_cache.get('image_analysis'))
        target_has_embs = bool(target_cache.get('clustering', {}).get('embeddings'))
        
        print(f"📊 드리프트 분석 - EDA 캐시 상태:")
        print(f"   Base: 속성={base_has_attrs}, 임베딩={base_has_embs}")
        print(f"   Target: 속성={target_has_attrs}, 임베딩={target_has_embs}")
        
        update_progress(0.2, "데이터 로드 중...")
        
        # 분석 수행 (EDA 캐시 전달)
        update_progress(0.3, "드리프트 분석 수행 중...")
        result = run_drift(
            base_path, 
            target_path,
            base_cache=base_cache,
            target_cache=target_cache
        )
        
        update_progress(0.8, "결과 저장 중...")
        
        # 결과 저장
        existing = db.query(DriftResult).filter(
            DriftResult.base_id == base_id,
            DriftResult.target_id == target_id
        ).first()
        
        overall_score = None
        if "advanced_drift" in result and result["advanced_drift"]:
            ensemble = result["advanced_drift"].get("ensemble", {})
            overall_score = ensemble.get("overall_score")
        
        if existing:
            existing.summary = result
            existing.feature_drift = result.get("drift") or result.get("advanced_drift")
            existing.overall = overall_score
        else:
            drift_result = DriftResult(
                id=str(uuid.uuid4()),
                base_id=base_id,
                target_id=target_id,
                summary=result,
                feature_drift=result.get("drift") or result.get("advanced_drift"),
                overall=overall_score,
            )
            db.add(drift_result)
        
        # 완료
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if task:
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            task.progress = 1.0
            task.message = "완료"
        
        db.commit()
        print(f"✅ 드리프트 분석 완료: task_id={task_id}")
        
    except Exception as e:
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if task:
            task.status = "failed"
            task.completed_at = datetime.utcnow()
            task.error = str(e)
            task.message = "실패"
            db.commit()
        print(f"⚠️ 드리프트 분석 실패: task_id={task_id}, error={e}")
        
    finally:
        task_queue.finish_task(base_id, "drift", target_id)
        db.close()