<!-- 5d4b5647-053e-4fa0-b1db-642e42f69578 dabc5525-2d21-42a7-8195-8e8c3898a374 -->
# 분석 작업 큐 시스템 구현 계획

**작성일**: 2024.12.01

**예상 소요**: 2-3일

## 1. 백엔드 - 데이터 모델 확장

### 1.1 AnalysisTask 모델 추가 (`app/models.py`)

```python
class AnalysisTask(Base):
    __tablename__ = "analysis_tasks"
    
    id = Column(String, primary_key=True)
    dataset_id = Column(String, index=True)
    target_id = Column(String, nullable=True)  # drift용
    task_type = Column(String)  # eda, image_analysis, clustering, drift
    status = Column(String, default="pending")  # pending/in_progress/completed/failed
    progress = Column(Float, default=0.0)
    message = Column(String, nullable=True)
    error = Column(String, nullable=True)
    metadata = Column(JSON, nullable=True)  # ETA, 처리 파일 수 등
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
```

---

## 2. 백엔드 - 작업 큐 서비스

### 2.1 TaskQueueService 생성 (`app/services/task_queue.py`)

- ThreadPoolExecutor 기반 (max_workers=2)
- 실행 중인 작업 추적 (dataset_id:task_type -> task_id)
- 중복 실행 방지 로직
- 싱글톤 패턴

### 2.2 TimeEstimator/ProgressTracker 유틸리티 (`app/services/progress_tracker.py`)

- 이력 기반 예상 시간 계산
- 실시간 ETA 계산 (이동 평균)
- 진행률 콜백 지원

---

## 3. 백엔드 - WebSocket 엔드포인트

### 3.1 WebSocket 라우터 생성 (`app/routers/ws.py`)

```python
@router.websocket("/ws/task/{task_id}")
async def task_progress(websocket: WebSocket, task_id: str):
    # 1초마다 작업 상태 전송
    # 완료/실패 시 연결 종료
```

### 3.2 main.py에 WebSocket 라우터 등록

---

## 4. 백엔드 - EDA 라우터 개선 (`app/routers/eda.py`)

### 4.1 새 엔드포인트 추가

- `GET /eda/{dataset_id}/status` - 데이터셋의 분석 상태 조회
- `GET /eda/task/{task_id}` - 특정 작업 상태 조회
- `POST /eda/async/{dataset_id}/image-analysis` - 비동기 이미지 분석
- `POST /eda/async/{dataset_id}/clustering` - 비동기 클러스터링

### 4.2 기존 엔드포인트 개선

- 분석 시작 전 이미 실행 중인 작업 확인
- 캐시된 결과 있으면 즉시 반환

---

## 5. 백엔드 - EDA 서비스 개선 (`app/services/eda_service.py`)

### 5.1 진행률 콜백 지원 추가

```python
def run_image_attributes(
    directory: str, 
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Optional[Dict[str, Any]]:
    # 파일별 처리 시 콜백 호출
```

---

## 6. 백엔드 - Drift 라우터 개선 (`app/routers/drift.py`)

### 6.1 새 엔드포인트 추가

- `POST /drift/async` - 비동기 드리프트 분석
- `GET /drift/task/{task_id}` - 작업 상태 조회

---

## 7. 프론트엔드 - WebSocket 훅 (`src/hooks/useTaskWebSocket.js`)

```javascript
export function useTaskWebSocket(backend, taskId, onProgress, onComplete) {
    // WebSocket 연결 및 상태 관리
    // 재연결 로직
}
```

---

## 8. 프론트엔드 - 프로그레스 바 컴포넌트 (`src/components/AnalysisProgress.jsx`)

- 진행률 바 (애니메이션)
- 처리 파일 수 / 전체 파일 수
- 예상 남은 시간 표시
- 취소 버튼 (선택적)

---

## 9. 프론트엔드 - DatasetGrid 개선 (`src/components/DatasetGrid.jsx`)

### 9.1 분석 상태 표시

- 데이터셋 카드에 "분석 중" 뱃지
- 분석 중인 데이터셋의 EDA/Drift 버튼 비활성화

### 9.2 상태 조회 로직

- 컴포넌트 마운트 시 각 데이터셋 상태 조회
- 주기적 새로고침 (30초)

---

## 10. 프론트엔드 - EDAStudio 개선 (`src/components/EDAStudio.jsx`)

### 10.1 비동기 분석 요청

- 이미지 분석, 클러스터링 버튼 클릭 시 비동기 API 호출
- WebSocket으로 실시간 진행률 수신

### 10.2 프로그레스 바 통합

- 분석 진행 중 AnalysisProgress 컴포넌트 표시

---

## 11. 프론트엔드 - DriftStudio 개선 (`src/components/DriftStudio.jsx`)

### 11.1 비동기 분석 지원

- 드리프트 분석 시 비동기 API 사용
- 실시간 진행률 표시

---

## 파일 변경 요약

| 파일 | 변경 유형 |

|-----|----------|

| `backend/app/models.py` | 수정 - AnalysisTask 추가 |

| `backend/app/services/task_queue.py` | 신규 |

| `backend/app/services/progress_tracker.py` | 신규 |

| `backend/app/routers/ws.py` | 신규 |

| `backend/app/routers/eda.py` | 수정 |

| `backend/app/routers/drift.py` | 수정 |

| `backend/app/services/eda_service.py` | 수정 |

| `backend/app/main.py` | 수정 - WebSocket 라우터 등록 |

| `frontend/src/hooks/useTaskWebSocket.js` | 신규 |

| `frontend/src/components/AnalysisProgress.jsx` | 신규 |

| `frontend/src/components/DatasetGrid.jsx` | 수정 |

| `frontend/src/components/EDAStudio.jsx` | 수정 |

| `frontend/src/components/DriftStudio.jsx` | 수정 |

### To-dos

- [ ] AnalysisTask 모델 추가 (models.py)
- [ ] TaskQueueService 구현 (task_queue.py)
- [ ] TimeEstimator/ProgressTracker 구현 (progress_tracker.py)
- [ ] WebSocket 라우터 생성 및 등록 (ws.py, main.py)
- [ ] EDA 라우터 비동기 엔드포인트 추가 (eda.py)
- [ ] EDA 서비스 진행률 콜백 지원 (eda_service.py)
- [ ] Drift 라우터 비동기 엔드포인트 추가 (drift.py)
- [ ] WebSocket 훅 생성 (useTaskWebSocket.js)
- [ ] AnalysisProgress 컴포넌트 생성
- [ ] DatasetGrid 분석 상태 표시 추가
- [ ] EDAStudio 비동기 분석 통합
- [ ] DriftStudio 비동기 분석 통합