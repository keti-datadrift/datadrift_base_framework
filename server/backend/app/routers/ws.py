"""
WebSocket 라우터 - 실시간 작업 진행률 전송

DB 연결 최적화:
- 세션을 루프 밖에서 생성하여 연결 풀 부하 감소
- 폴링 간격을 적절히 조절
"""

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database import SessionLocal
from app.models import AnalysisTask

router = APIRouter(tags=["websocket"])


def _get_task_status(db, task_id: str) -> dict:
    """작업 상태를 조회하여 딕셔너리로 반환"""
    # 세션 만료된 객체 갱신을 위해 expire_all
    db.expire_all()
    
    task = db.query(AnalysisTask).filter(AnalysisTask.id == task_id).first()
    
    if not task:
        return None
    
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


@router.websocket("/ws/task/{task_id}")
async def task_progress_websocket(websocket: WebSocket, task_id: str):
    """
    작업 진행률을 실시간으로 전송하는 WebSocket 엔드포인트
    
    - 세션을 연결 시 한 번만 생성
    - 2초마다 상태 업데이트
    """
    await websocket.accept()
    
    # DB 세션을 루프 밖에서 한 번만 생성
    db = SessionLocal()
    
    try:
        while True:
            # 1. DB 조회 (별도 try-except)
            try:
                status_data = _get_task_status(db, task_id)
            except Exception as e:
                db.rollback()
                print(f"⚠️ WebSocket DB 조회 오류: {e}")
                await asyncio.sleep(2)
                continue
            
            # 2. WebSocket 전송 (실패 시 루프 탈출)
            try:
                if not status_data:
                    await websocket.send_json({
                        "error": "Task not found",
                        "task_id": task_id
                    })
                    break
                
                await websocket.send_json(status_data)
                
                # 완료 또는 실패 상태면 연결 종료
                if status_data["status"] in ["completed", "failed"]:
                    break
                    
            except Exception as e:
                # WebSocket 전송 실패 = 연결 끊김 → 루프 탈출
                print(f"📡 WebSocket 전송 실패 (연결 종료): {task_id}")
                break
            
            # 2초 대기
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        print(f"📡 WebSocket 연결 종료: task_id={task_id}")
    except Exception as e:
        print(f"⚠️ WebSocket 오류: {e}")
    finally:
        # 세션 정리
        db.close()
        try:
            await websocket.close()
        except:
            pass


@router.websocket("/ws/dataset/{dataset_id}")
async def dataset_tasks_websocket(websocket: WebSocket, dataset_id: str):
    """
    특정 데이터셋의 모든 진행 중인 작업 상태를 전송하는 WebSocket
    
    - 세션을 연결 시 한 번만 생성
    - 3초마다 상태 업데이트
    """
    await websocket.accept()
    
    # DB 세션을 루프 밖에서 한 번만 생성
    db = SessionLocal()
    
    try:
        while True:
            # 1. DB 조회 (별도 try-except)
            try:
                db.expire_all()
                
                tasks = db.query(AnalysisTask).filter(
                    AnalysisTask.dataset_id == dataset_id,
                    AnalysisTask.status.in_(["pending", "in_progress"])
                ).all()
                
                tasks_data = [
                    {
                        "task_id": t.id,
                        "task_type": t.task_type,
                        "status": t.status,
                        "progress": t.progress,
                        "message": t.message,
                        "metadata": t.task_metadata,
                    }
                    for t in tasks
                ]
            except Exception as e:
                db.rollback()
                print(f"⚠️ Dataset WebSocket DB 조회 오류: {e}")
                await asyncio.sleep(3)
                continue
            
            # 2. WebSocket 전송 (실패 시 루프 탈출)
            try:
                await websocket.send_json({
                    "dataset_id": dataset_id,
                    "running_tasks": tasks_data,
                    "has_running_tasks": len(tasks_data) > 0,
                })
            except Exception as e:
                # WebSocket 전송 실패 = 연결 끊김 → 루프 탈출
                print(f"📡 Dataset WebSocket 전송 실패 (연결 종료): {dataset_id}")
                break
            
            # 3초마다 업데이트
            await asyncio.sleep(3)
            
    except WebSocketDisconnect:
        print(f"📡 Dataset WebSocket 연결 종료: dataset_id={dataset_id}")
    except Exception as e:
        print(f"⚠️ Dataset WebSocket 오류: {e}")
    finally:
        db.close()
        try:
            await websocket.close()
        except:
            pass
