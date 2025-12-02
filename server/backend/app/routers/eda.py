import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database import SessionLocal
from app.models import Dataset, EDAResult, AnalysisTask
from app.services.eda_service import run_eda, run_image_attributes, run_image_clustering
from app.services.task_queue import get_task_queue
from app.services.progress_tracker import TimeEstimator
from app.utils.json_sanitize import clean_json_value


router = APIRouter(prefix="/eda", tags=["eda"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/{dataset_id}")
def eda(
    dataset_id: str, 
    force: bool = Query(False, description="강제 재분석 여부"),
    db: Session = Depends(get_db)
):
    """
    데이터셋 EDA 분석 결과를 반환합니다.
    
    - 캐시된 결과가 있으면 캐시에서 반환
    - 캐시가 없거나 force=true이면 새로 분석 후 저장
    """
    # 1) 데이터셋 존재 확인
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # 2) 캐시 조회 (force가 아닐 때만)
    if not force:
        cached = db.query(EDAResult).filter(EDAResult.dataset_id == dataset_id).first()
        if cached and cached.stats:
            return {
                "cached": True,
                "dataset_id": dataset_id,
                **cached.stats
            }

    # 3) 분석 수행
    result = run_eda(
        file_path=ds.dvc_path,
        dtype=ds.type.lower() if ds.type else "csv"
    )

    # 4) 결과 저장 (upsert)
    existing = db.query(EDAResult).filter(EDAResult.dataset_id == dataset_id).first()
    if existing:
        # 업데이트
        existing.stats = result
        existing.summary = result.get("summary")
        existing.missing_rate = result.get("missing_rate")
    else:
        # 새로 생성
        eda_result = EDAResult(
            id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            stats=result,
            summary=result.get("summary"),
            missing_rate=result.get("missing_rate"),
        )
        db.add(eda_result)
    
    db.commit()

    return {
        "cached": False,
        "dataset_id": dataset_id,
        **result
    }

@router.get("/{dataset_id}/image-analysis")
def eda_image_analysis(
    dataset_id: str,
    force: bool = Query(False, description="강제 재분석 여부"),
    db: Session = Depends(get_db)
):
    """
    이미지 속성 분석 (크기, 노이즈, 선명도, 품질 점수, 분포).
    ZIP 데이터셋에만 사용 가능합니다.
    """
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    if ds.type.lower() != "zip":
        raise HTTPException(status_code=400, detail="이미지 분석은 ZIP 데이터셋에만 사용 가능합니다.")
    
    # 캐시 확인 (force가 아닐 때만)
    if not force:
        cached = db.query(EDAResult).filter(EDAResult.dataset_id == dataset_id).first()
        if cached and cached.stats and cached.stats.get("image_analysis"):
            return {
                "cached": True,
                "dataset_id": dataset_id,
                **cached.stats["image_analysis"]
            }
    
    # root_dir 찾기
    import os
    dataset_dir = ds.dvc_path
    raw_zip = None
    for f in os.listdir(dataset_dir):
        if f.lower().endswith(".zip"):
            raw_zip = os.path.join(dataset_dir, f)
            break
    
    if not raw_zip:
        raise HTTPException(status_code=404, detail="ZIP 파일을 찾을 수 없습니다.")
    
    # 추출된 디렉토리 경로
    extracted_dir = raw_zip + "_extracted"
    if not os.path.isdir(extracted_dir):
        raise HTTPException(status_code=404, detail="추출된 디렉토리를 찾을 수 없습니다. 먼저 기본 EDA를 실행해주세요.")
    
    # 이미지 속성 분석 실행
    result = run_image_attributes(extracted_dir)
    if not result:
        raise HTTPException(status_code=404, detail="분석 가능한 이미지가 없습니다.")
    
    # 캐시에 저장
    existing = db.query(EDAResult).filter(EDAResult.dataset_id == dataset_id).first()
    if existing and existing.stats:
        existing.stats["image_analysis"] = result
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(existing, "stats")
        db.commit()
    
    return clean_json_value({
        "cached": False,
        "dataset_id": dataset_id,
        **result
    })


@router.get("/{dataset_id}/clustering")
def eda_clustering(
    dataset_id: str,
    force: bool = Query(False, description="강제 재분석 여부"),
    db: Session = Depends(get_db)
):
    """
    이미지 임베딩 추출 및 K-means 클러스터링.
    ZIP 데이터셋에만 사용 가능합니다.
    """
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    if ds.type.lower() != "zip":
        raise HTTPException(status_code=400, detail="클러스터링은 ZIP 데이터셋에만 사용 가능합니다.")
    
    # 캐시 확인 (force가 아닐 때만)
    if not force:
        cached = db.query(EDAResult).filter(EDAResult.dataset_id == dataset_id).first()
        if cached and cached.stats and cached.stats.get("clustering"):
            return {
                "cached": True,
                "dataset_id": dataset_id,
                **cached.stats["clustering"]
            }
    
    # root_dir 찾기
    import os
    dataset_dir = ds.dvc_path
    raw_zip = None
    for f in os.listdir(dataset_dir):
        if f.lower().endswith(".zip"):
            raw_zip = os.path.join(dataset_dir, f)
            break
    
    if not raw_zip:
        raise HTTPException(status_code=404, detail="ZIP 파일을 찾을 수 없습니다.")
    
    # 추출된 디렉토리 경로
    extracted_dir = raw_zip + "_extracted"
    if not os.path.isdir(extracted_dir):
        raise HTTPException(status_code=404, detail="추출된 디렉토리를 찾을 수 없습니다. 먼저 기본 EDA를 실행해주세요.")
    
    # 클러스터링 실행
    result = run_image_clustering(extracted_dir)
    if not result:
        raise HTTPException(status_code=500, detail="클러스터링 실행 실패")
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # 캐시에 저장
    existing = db.query(EDAResult).filter(EDAResult.dataset_id == dataset_id).first()
    if existing and existing.stats:
        existing.stats["clustering"] = result
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(existing, "stats")
        db.commit()
    
    return clean_json_value({
        "cached": False,
        "dataset_id": dataset_id,
        **result
    })


# ============================================================
# 작업 상태 조회 엔드포인트
# ============================================================

@router.get("/task/{task_id}")
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """특정 작업의 상태를 조회합니다."""
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


@router.get("/{dataset_id}/status")
def get_dataset_analysis_status(dataset_id: str, db: Session = Depends(get_db)):
    """데이터셋의 EDA 분석 작업 상태를 조회합니다. (드리프트 제외)"""
    # 데이터셋 존재 확인
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # 진행 중인 EDA 작업 조회 (드리프트 작업 제외)
    tasks = db.query(AnalysisTask).filter(
        AnalysisTask.dataset_id == dataset_id,
        AnalysisTask.status.in_(["pending", "in_progress"]),
        AnalysisTask.task_type.in_(["image_analysis", "clustering"])  # EDA 작업만
    ).all()
    
    # 캐시된 결과 확인 (분석 수행 없이 존재 여부만 확인)
    cached = db.query(EDAResult).filter(EDAResult.dataset_id == dataset_id).first()
    image_analysis_cached = False
    clustering_cached = False
    
    if cached and cached.stats:
        image_analysis_cached = bool(cached.stats.get("image_analysis"))
        clustering_cached = bool(cached.stats.get("clustering"))
    
    return {
        "dataset_id": dataset_id,
        "has_running_tasks": len(tasks) > 0,
        "running_tasks": [
            {
                "task_id": t.id,
                "task_type": t.task_type,
                "status": t.status,
                "progress": t.progress,
                "message": t.message,
                "metadata": t.task_metadata,
            }
            for t in tasks
        ],
        "cache_status": {
            "image_analysis": image_analysis_cached,
            "clustering": clustering_cached,
        }
    }


# ============================================================
# 비동기 분석 엔드포인트
# ============================================================

@router.post("/async/{dataset_id}/image-analysis")
def eda_image_analysis_async(
    dataset_id: str, 
    force: bool = Query(False, description="강제 재분석 여부"),
    db: Session = Depends(get_db)
):
    """
    이미지 속성 분석을 비동기로 실행합니다 (중복 실행 방지).
    
    Args:
        force: True면 캐시 무시하고 재분석
    
    Returns:
        - status: queued | already_running | completed
        - task_id: 작업 ID (폴링/WebSocket 연결용)
    """
    # 1) 데이터셋 확인
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    if ds.type.lower() != "zip":
        raise HTTPException(status_code=400, detail="이미지 분석은 ZIP 데이터셋에만 사용 가능합니다.")
    
    task_queue = get_task_queue()
    
    # 2) 이미 실행 중인지 확인
    existing_task_id = task_queue.is_running(dataset_id, "image_analysis")
    if existing_task_id:
        return {
            "status": "already_running",
            "task_id": existing_task_id,
            "message": "이미 분석이 진행 중입니다."
        }
    
    # 3) 캐시 확인 (force가 아닐 때만)
    if not force:
        cached = db.query(EDAResult).filter(EDAResult.dataset_id == dataset_id).first()
        if cached and cached.stats and cached.stats.get("image_analysis"):
            return {
                "status": "completed",
                "cached": True,
                "message": "이미 분석 결과가 존재합니다."
            }
    
    # 4) 새 작업 생성
    task_id = str(uuid.uuid4())
    
    # 이미지 파일 수 조회 (예상 시간 계산용)
    dataset_dir = ds.dvc_path
    raw_zip = None
    for f in os.listdir(dataset_dir):
        if f.lower().endswith(".zip"):
            raw_zip = os.path.join(dataset_dir, f)
            break
    
    extracted_dir = raw_zip + "_extracted" if raw_zip else None
    estimated_time = None
    total_files = 0
    
    if extracted_dir and os.path.isdir(extracted_dir):
        from app.services.eda_service import collect_image_files
        image_files = collect_image_files(extracted_dir)
        total_files = len(image_files)
        estimated_time = TimeEstimator.estimate_time("image_analysis", total_files)
    
    task = AnalysisTask(
        id=task_id,
        dataset_id=dataset_id,
        task_type="image_analysis",
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
    if not task_queue.start_task(task_id, dataset_id, "image_analysis"):
        return {
            "status": "already_running",
            "task_id": task_queue.is_running(dataset_id, "image_analysis"),
            "message": "이미 분석이 진행 중입니다."
        }
    
    # 6) 백그라운드에서 실행
    task_queue.submit_task(
        _run_image_analysis_task,
        task_id,
        dataset_id,
        ds.dvc_path
    )
    
    return {
        "status": "queued",
        "task_id": task_id,
        "message": "분석 작업이 시작되었습니다.",
        "estimated_seconds": estimated_time,
        "estimated_formatted": TimeEstimator.format_time(estimated_time),
    }


@router.post("/async/{dataset_id}/clustering")
def eda_clustering_async(
    dataset_id: str, 
    force: bool = Query(False, description="강제 재분석 여부"),
    db: Session = Depends(get_db)
):
    """
    클러스터링 분석을 비동기로 실행합니다 (중복 실행 방지).
    
    Args:
        force: True면 캐시 무시하고 재분석
    """
    # 1) 데이터셋 확인
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    if ds.type.lower() != "zip":
        raise HTTPException(status_code=400, detail="클러스터링은 ZIP 데이터셋에만 사용 가능합니다.")
    
    task_queue = get_task_queue()
    
    # 2) 이미 실행 중인지 확인
    existing_task_id = task_queue.is_running(dataset_id, "clustering")
    if existing_task_id:
        return {
            "status": "already_running",
            "task_id": existing_task_id,
            "message": "이미 클러스터링이 진행 중입니다."
        }
    
    # 3) 캐시 확인 (force가 아닐 때만)
    if not force:
        cached = db.query(EDAResult).filter(EDAResult.dataset_id == dataset_id).first()
        if cached and cached.stats and cached.stats.get("clustering"):
            return {
                "status": "completed",
                "cached": True,
                "message": "이미 클러스터링 결과가 존재합니다."
            }
    
    # 4) 새 작업 생성
    task_id = str(uuid.uuid4())
    
    # 이미지 파일 수 조회
    dataset_dir = ds.dvc_path
    raw_zip = None
    for f in os.listdir(dataset_dir):
        if f.lower().endswith(".zip"):
            raw_zip = os.path.join(dataset_dir, f)
            break
    
    extracted_dir = raw_zip + "_extracted" if raw_zip else None
    estimated_time = None
    total_files = 0
    
    if extracted_dir and os.path.isdir(extracted_dir):
        from app.services.eda_service import collect_image_files
        image_files = collect_image_files(extracted_dir)
        total_files = len(image_files)
        estimated_time = TimeEstimator.estimate_time("clustering", total_files)
    
    task = AnalysisTask(
        id=task_id,
        dataset_id=dataset_id,
        task_type="clustering",
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
    if not task_queue.start_task(task_id, dataset_id, "clustering"):
        return {
            "status": "already_running",
            "task_id": task_queue.is_running(dataset_id, "clustering"),
            "message": "이미 클러스터링이 진행 중입니다."
        }
    
    # 6) 백그라운드에서 실행
    task_queue.submit_task(
        _run_clustering_task,
        task_id,
        dataset_id,
        ds.dvc_path
    )
    
    return {
        "status": "queued",
        "task_id": task_id,
        "message": "클러스터링 작업이 시작되었습니다.",
        "estimated_seconds": estimated_time,
        "estimated_formatted": TimeEstimator.format_time(estimated_time),
    }


# ============================================================
# 백그라운드 작업 실행 함수
# ============================================================

def _run_image_analysis_task(task_id: str, dataset_id: str, dvc_path: str):
    """백그라운드에서 이미지 속성 분석 실행"""
    import time
    from app.services.eda_service import run_image_attributes_with_progress, collect_image_files
    from app.services.progress_tracker import ProgressTracker
    
    db = SessionLocal()
    task_queue = get_task_queue()
    
    try:
        # 상태 업데이트: 시작
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if task:
            task.status = "in_progress"
            task.started_at = datetime.utcnow()
            task.message = "분석 시작..."
            task.progress = 0.05
            db.commit()
        
        # ZIP 파일 경로 찾기
        raw_zip = None
        for f in os.listdir(dvc_path):
            if f.lower().endswith(".zip"):
                raw_zip = os.path.join(dvc_path, f)
                break
        
        if not raw_zip:
            raise RuntimeError("ZIP 파일을 찾을 수 없습니다.")
        
        extracted_dir = raw_zip + "_extracted"
        if not os.path.isdir(extracted_dir):
            raise RuntimeError("추출된 디렉토리를 찾을 수 없습니다.")
        
        # 이미지 파일 수 확인
        image_files = collect_image_files(extracted_dir)
        total_files = len(image_files)
        
        # ProgressTracker 생성
        tracker = ProgressTracker(total_files, "image_analysis")
        
        # DB 업데이트 빈도 제한 (최소 3초 간격)
        last_db_update = [0.0]  # 리스트로 감싸서 closure에서 수정 가능하게
        MIN_UPDATE_INTERVAL = 3.0
        
        # 진행률 콜백 (DB 업데이트 빈도 제한)
        def progress_callback(progress: float, message: str):
            nonlocal task
            current_time = time.time()
            
            # 최소 간격이 지났거나 완료 시에만 DB 업데이트
            if current_time - last_db_update[0] < MIN_UPDATE_INTERVAL and progress < 1.0:
                return
            
            last_db_update[0] = current_time
            
            try:
                task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
                if task:
                    status = tracker.get_status()
                    task.progress = progress
                    task.message = message
                    task.task_metadata = {
                        "total_files": total_files,
                        "processed": status["processed"],
                        "eta_seconds": status["eta_seconds"],
                        "eta_formatted": status["eta_formatted"],
                        "elapsed_seconds": status["elapsed_seconds"],
                    }
                    db.commit()
            except Exception as e:
                db.rollback()
                print(f"⚠️ progress_callback DB 오류: {e}")
        
        # 분석 실행
        result = run_image_attributes_with_progress(
            extracted_dir, 
            progress_callback=progress_callback,
            tracker=tracker
        )
        
        if not result:
            raise RuntimeError("분석 가능한 이미지가 없습니다.")
        
        # 결과 저장
        existing = db.query(EDAResult).filter(EDAResult.dataset_id == dataset_id).first()
        if existing and existing.stats:
            existing.stats["image_analysis"] = result
            flag_modified(existing, "stats")
        else:
            # EDAResult가 없으면 생성
            eda_result = EDAResult(
                id=str(uuid.uuid4()),
                dataset_id=dataset_id,
                stats={"image_analysis": result},
            )
            db.add(eda_result)
        
        # 완료
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if task:
            final_status = tracker.finish()
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            task.progress = 1.0
            task.message = "완료"
            task.task_metadata = {
                "total_files": total_files,
                "processed": total_files,
                "elapsed_seconds": final_status["elapsed_seconds"],
            }
        
        db.commit()
        print(f"✅ 이미지 분석 완료: task_id={task_id}")
        
    except Exception as e:
        # 실패 처리
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if task:
            task.status = "failed"
            task.completed_at = datetime.utcnow()
            task.error = str(e)
            task.message = "실패"
            db.commit()
        print(f"⚠️ 이미지 분석 실패: task_id={task_id}, error={e}")
        
    finally:
        task_queue.finish_task(dataset_id, "image_analysis")
        db.close()


def _run_clustering_task(task_id: str, dataset_id: str, dvc_path: str):
    """백그라운드에서 클러스터링 실행"""
    import time
    from app.services.eda_service import run_image_clustering_with_progress, collect_image_files
    from app.services.progress_tracker import ProgressTracker
    
    db = SessionLocal()
    task_queue = get_task_queue()
    
    try:
        # 상태 업데이트: 시작
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if task:
            task.status = "in_progress"
            task.started_at = datetime.utcnow()
            task.message = "클러스터링 시작..."
            task.progress = 0.05
            db.commit()
        
        # ZIP 파일 경로 찾기
        raw_zip = None
        for f in os.listdir(dvc_path):
            if f.lower().endswith(".zip"):
                raw_zip = os.path.join(dvc_path, f)
                break
        
        if not raw_zip:
            raise RuntimeError("ZIP 파일을 찾을 수 없습니다.")
        
        extracted_dir = raw_zip + "_extracted"
        if not os.path.isdir(extracted_dir):
            raise RuntimeError("추출된 디렉토리를 찾을 수 없습니다.")
        
        # 이미지 파일 수 확인
        image_files = collect_image_files(extracted_dir)
        total_files = len(image_files)
        
        # ProgressTracker 생성
        tracker = ProgressTracker(total_files, "clustering")
        
        # DB 업데이트 빈도 제한 (최소 3초 간격)
        last_db_update = [0.0]
        MIN_UPDATE_INTERVAL = 3.0
        
        # 진행률 콜백 (DB 업데이트 빈도 제한)
        def progress_callback(progress: float, message: str):
            nonlocal task
            current_time = time.time()
            
            # 최소 간격이 지났거나 완료 시에만 DB 업데이트
            if current_time - last_db_update[0] < MIN_UPDATE_INTERVAL and progress < 1.0:
                return
            
            last_db_update[0] = current_time
            
            try:
                task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
                if task:
                    status = tracker.get_status()
                    task.progress = progress
                    task.message = message
                    task.task_metadata = {
                        "total_files": total_files,
                        "processed": status["processed"],
                        "eta_seconds": status["eta_seconds"],
                        "eta_formatted": status["eta_formatted"],
                        "elapsed_seconds": status["elapsed_seconds"],
                    }
                    db.commit()
            except Exception as e:
                db.rollback()
                print(f"⚠️ progress_callback DB 오류: {e}")
        
        # 클러스터링 실행
        result = run_image_clustering_with_progress(
            extracted_dir, 
            progress_callback=progress_callback,
            tracker=tracker
        )
        
        if not result:
            raise RuntimeError("클러스터링 실행 실패")
        
        if "error" in result:
            raise RuntimeError(result["error"])
        
        # 결과 저장
        existing = db.query(EDAResult).filter(EDAResult.dataset_id == dataset_id).first()
        if existing and existing.stats:
            existing.stats["clustering"] = result
            flag_modified(existing, "stats")
        else:
            eda_result = EDAResult(
                id=str(uuid.uuid4()),
                dataset_id=dataset_id,
                stats={"clustering": result},
            )
            db.add(eda_result)
        
        # 완료
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if task:
            final_status = tracker.finish()
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            task.progress = 1.0
            task.message = "완료"
            task.task_metadata = {
                "total_files": total_files,
                "processed": total_files,
                "elapsed_seconds": final_status["elapsed_seconds"],
            }
        
        db.commit()
        print(f"✅ 클러스터링 완료: task_id={task_id}")
        
    except Exception as e:
        task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
        if task:
            task.status = "failed"
            task.completed_at = datetime.utcnow()
            task.error = str(e)
            task.message = "실패"
            db.commit()
        print(f"⚠️ 클러스터링 실패: task_id={task_id}, error={e}")
        
    finally:
        task_queue.finish_task(dataset_id, "clustering")
        db.close()
