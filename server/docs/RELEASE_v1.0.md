# DataDrift 웹 앱 v1.0 개발 내역

**작성일**: 2025년 12월 2일

---

## 개요

ddoc-plugin-vision을 활용한 이미지 데이터셋 분석 웹 애플리케이션의 1차 개발 완료.
EDA/드리프트 분석 기능 강화 및 비동기 작업 처리 시스템 구현.

---

## 주요 기능

### 1. EDA 분석 강화

- **이미지 속성 분석**: 파일 크기, 해상도, 노이즈 레벨, 선명도, 품질 점수
- **CLIP 임베딩**: 이미지 특성 벡터 추출
- **K-means 클러스터링**: 유사 이미지 자동 그룹화
- **시각화**: 분포 히스토그램, 산점도, 파이 차트 (Recharts)

### 2. 드리프트 분석 강화

- **앙상블 메트릭**:
  - KL Divergence (속성별)
  - MMD (Maximum Mean Discrepancy)
  - Wasserstein Distance
  - PSI (Population Stability Index)
- **상태 판정**: NORMAL / WARNING / CRITICAL
- **비교 시각화**: 소스/타겟 분포 오버레이 차트

### 3. 비동기 작업 큐 시스템

- **TaskQueueService**: ThreadPoolExecutor 기반 (max_workers=2)
- **ProgressTracker**: 이력 기반 ETA 계산, 실시간 진행률
- **WebSocket**: `/ws/task/{task_id}` 엔드포인트로 실시간 상태 전송
- **중복 실행 방지**: dataset_id + task_type 기반 락

### 4. 프론트엔드 UI

- **AnalysisProgress**: 진행률 바, 처리 파일 수, 예상 남은 시간
- **ZipUploader**: 드래그 앤 드롭 ZIP 업로드
- **EDAStudio/DriftStudio**: 차트 시각화 통합
- **useTaskWebSocket**: WebSocket 연결 관리 훅

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Backend | FastAPI, SQLAlchemy, WebSocket |
| Frontend | React, Recharts |
| 분석 | ddoc-plugin-vision (CLIP, AttributeAnalyzer) |
| 인프라 | Docker, docker-compose |

---

## 파일 변경 요약

### 신규 파일

| 파일 | 설명 |
|------|------|
| `backend/app/routers/ws.py` | WebSocket 라우터 |
| `backend/app/services/analyzer_init.py` | 분석기 초기화 (싱글톤) |
| `backend/app/services/task_queue.py` | 작업 큐 서비스 |
| `backend/app/services/progress_tracker.py` | 진행률 추적 및 ETA 계산 |
| `frontend/src/components/AnalysisProgress.jsx` | 진행률 UI 컴포넌트 |
| `frontend/src/components/ZipUploader.jsx` | ZIP 업로드 컴포넌트 |
| `frontend/src/hooks/useTaskWebSocket.js` | WebSocket 훅 |

### 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `backend/app/main.py` | WebSocket 라우터 등록 |
| `backend/app/models.py` | AnalysisTask 모델 추가 |
| `backend/app/services/eda_service.py` | 이미지 분석 로직 통합 |
| `backend/app/services/drift_service.py` | 앙상블 드리프트 메트릭 추가 |
| `backend/app/routers/eda.py` | 비동기 분석 API 추가 |
| `backend/app/routers/drift.py` | 비동기 드리프트 API 추가 |
| `frontend/src/components/EDAStudio.jsx` | 차트 시각화 추가 |
| `frontend/src/components/DriftStudio.jsx` | 드리프트 시각화 추가 |
| `frontend/src/components/DatasetGrid.jsx` | 분석 상태 표시 |

### 의존성

- `ddoc` submodule 추가 (`server/ddoc`)
- `backend/requirements.txt` - ddoc-plugin-vision 관련 패키지

---

## API 엔드포인트

### EDA 관련

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/eda/{dataset_id}/status` | 분석 상태 조회 |
| GET | `/eda/task/{task_id}` | 작업 상태 조회 |
| POST | `/eda/async/{dataset_id}/image-analysis` | 비동기 이미지 분석 |
| POST | `/eda/async/{dataset_id}/clustering` | 비동기 클러스터링 |

### 드리프트 관련

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/drift/async` | 비동기 드리프트 분석 |
| GET | `/drift/task/{task_id}` | 작업 상태 조회 |

### WebSocket

| Endpoint | 설명 |
|----------|------|
| `/ws/task/{task_id}` | 실시간 진행률 스트리밍 |

---

## 다음 단계 (TODO)

- [ ] ddoc 워크스페이스 연동
- [ ] 데이터셋 내보내기/가져오기
- [ ] 스냅샷/계보 관리
- [ ] CLI subprocess 호출 래퍼
- [ ] 실험(모델 훈련/평가) 연동
