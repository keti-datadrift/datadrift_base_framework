<!-- 00c5051e-111e-46dd-95bc-6b256aba33eb 79d7c096-96a4-4e6b-bf45-9d293f61ca69 -->
# ddoc 워크스페이스 연동 계획

**작성일**: 2024.12.04

**방식**: 싱글 서비스 (1개 ddoc-workspace 컨테이너가 모든 워크스페이스 관리)

---

## 1. 아키텍처 개요

```
Frontend (React)  ──▶  Backend (FastAPI)  ──▶  ddoc-workspace (FastAPI)
    :3000                  :8000                      :5001
                              │                          │
                              └──────────────────────────┘
                                        │
                              ┌─────────┴─────────┐
                              ▼                   ▼
                         /workspaces/        MLflow Server
                                                :5050
```

---

## 2. 신규 파일 구조

```
server/
├── ddoc-workspace/                    # [신규] 워크스페이스 서비스
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                    # FastAPI 엔트리포인트
│       ├── routers/
│       │   ├── workspace.py           # 워크스페이스 CRUD
│       │   ├── analysis.py            # ddoc-plugin-vision 연동
│       │   ├── sampling.py            # [신규] 샘플링 기능
│       │   ├── snapshot.py            # SnapshotService 연동
│       │   └── experiment.py          # MLflowExperimentService 연동
│       ├── services/
│       │   └── sampling_service.py    # [신규] 샘플링 로직
│       └── schemas.py
│
├── frontend/src/components/
│   ├── WorkspaceStudio.jsx            # [신규] 워크스페이스 메인 UI
│   └── workspace/                     # [신규]
│       ├── DataExplorer.jsx           # 데이터 탐색/미리보기
│       ├── DataSampler.jsx            # 샘플링 UI
│       ├── AnalysisPanel.jsx          # 분석 결과 표시
│       ├── ExperimentPanel.jsx        # 학습 실험 관리
│       └── SnapshotTimeline.jsx       # 스냅샷 히스토리
│
└── docker-compose.yml                 # ddoc-workspace, mlflow 추가
```

---

## 3. Phase 1: 기반 인프라 구축

### 3.1 docker-compose.yml 확장

`server/docker-compose.yml`에 추가:

```yaml
ddoc-workspace:
  build: ./ddoc-workspace
  ports:
    - "5001:5000"
  volumes:
    - ./workspaces:/workspaces
    - ./mlruns:/mlruns
    - ./dvc_storage:/dvc_storage
  environment:
    - MLFLOW_TRACKING_URI=http://mlflow:5050
  depends_on:
    - mlflow

mlflow:
  image: ghcr.io/mlflow/mlflow:latest
  ports:
    - "5050:5050"
  volumes:
    - ./mlruns:/mlruns
  command: mlflow server --host 0.0.0.0 --port 5050 --backend-store-uri sqlite:///mlruns/mlflow.db
```

### 3.2 ddoc-workspace 컨테이너 생성

`server/ddoc-workspace/Dockerfile`:

- Python 3.11 베이스
- ddoc 코어 + ddoc-plugin-vision 설치
- FastAPI 서버 실행

### 3.3 Workspace API 기본 구조

`server/ddoc-workspace/app/main.py`:

- FastAPI 앱 초기화
- 라우터 등록 (workspace, analysis, sampling, snapshot, experiment)
- CORS 설정

---

## 4. Phase 2: 워크스페이스 관리 API (ddoc 연동)

### 4.1 워크스페이스 CRUD

`server/ddoc-workspace/app/routers/workspace.py`:

| 엔드포인트 | 연동 대상 | 설명 |

|-----------|----------|------|

| `POST /workspace/create` | `WorkspaceService.init_workspace()` | 드리프트 분석 데이터셋으로 워크스페이스 생성 |

| `GET /workspace/{id}/status` | `WorkspaceService.verify_workspace()` | 워크스페이스 상태 조회 |

| `GET /workspaces` | - | 워크스페이스 목록 |

| `DELETE /workspace/{id}` | - | 워크스페이스 삭제 |

### 4.2 스냅샷 API

`server/ddoc-workspace/app/routers/snapshot.py`:

| 엔드포인트 | 연동 대상 | 설명 |

|-----------|----------|------|

| `POST /workspace/{id}/snapshot` | `SnapshotService.create_snapshot()` | 스냅샷 생성 |

| `GET /workspace/{id}/snapshots` | `SnapshotService.list_snapshots()` | 스냅샷 목록 |

| `POST /workspace/{id}/snapshot/{sid}/restore` | `SnapshotService.restore_snapshot()` | 스냅샷 복원 |

| `GET /workspace/{id}/lineage` | `SnapshotService.get_lineage_graph()` | 계보 그래프 |

---

## 5. Phase 3: 분석 기능 연동

### 5.1 Analysis API

`server/ddoc-workspace/app/routers/analysis.py`:

| 엔드포인트 | 연동 대상 | 설명 |

|-----------|----------|------|

| `POST /workspace/{id}/analyze/embedding` | `ddoc_plugin_vision.embedding_analyzer` | 임베딩 분석 실행 |

| `POST /workspace/{id}/analyze/attributes` | `ddoc_plugin_vision.attribute_analyzer` | 속성 분석 실행 |

| `GET /workspace/{id}/analysis/results` | 캐시에서 로드 | 분석 결과 조회 |

기존 `ddoc_plugin_vision` 모듈 활용:

- `server/ddoc/plugins/ddoc-plugin-vision/ddoc_plugin_vision/data_utils/embedding_analyzer.py`
- `server/ddoc/plugins/ddoc-plugin-vision/ddoc_plugin_vision/data_utils/attribute_analyzer.py`

---

## 6. Phase 4: 샘플링 기능 (신규 구현)

### 6.1 Sampling Service

`server/ddoc-workspace/app/services/sampling_service.py`:

```python
class SamplingService:
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.data_dir = self.workspace_path / "data"
    
    # 데이터 탐색
    def list_items(self, split, class_filter, limit, offset) -> List[DataItem]
    def get_item_preview(self, item_id) -> ImagePreview
    def get_statistics(self) -> DatasetStats
    
    # 데이터 수정
    def add_items(self, items: List[str], target_split: str) -> Result
    def remove_items(self, item_ids: List[str]) -> Result
    def move_items(self, item_ids: List[str], target_split: str) -> Result
    def relabel_items(self, item_ids: List[str], new_label: str) -> Result
    
    # 샘플링 전략
    def create_sample(self, strategy: str, params: dict) -> SampleResult
    # - random: 무작위 n개
    # - stratified: 클래스 비율 유지
    # - threshold: 드리프트 점수 기반 필터링
    
    # 내보내기
    def export_dataset(self, format: str, output_path: str) -> ExportResult
    # - yolo: YOLO 포맷 (images/ + labels/)
    # - coco: COCO JSON 포맷
    # - voc: Pascal VOC XML 포맷
```

### 6.2 Sampling API

`server/ddoc-workspace/app/routers/sampling.py`:

| 엔드포인트 | 설명 |

|-----------|------|

| `GET /workspace/{id}/data/items` | 데이터 아이템 목록 (페이지네이션) |

| `GET /workspace/{id}/data/item/{item_id}/preview` | 이미지 미리보기 |

| `GET /workspace/{id}/data/stats` | 데이터셋 통계 |

| `POST /workspace/{id}/data/add` | 아이템 추가 |

| `POST /workspace/{id}/data/remove` | 아이템 삭제 |

| `POST /workspace/{id}/data/move` | 아이템 이동 (split 간) |

| `POST /workspace/{id}/data/relabel` | 라벨 변경 |

| `POST /workspace/{id}/data/sample` | 샘플 데이터셋 생성 |

| `POST /workspace/{id}/data/export` | 데이터셋 내보내기 |

| `GET /workspace/{id}/data/export/formats` | 지원 포맷 목록 |

---

## 7. Phase 5: 학습 실험 연동

### 7.1 Experiment API

`server/ddoc-workspace/app/routers/experiment.py`:

| 엔드포인트 | 연동 대상 | 설명 |

|-----------|----------|------|

| `POST /workspace/{id}/code/upload` | - | 트레이너 코드 업로드 |

| `GET /workspace/{id}/code/templates` | - | 코드 템플릿 제공 |

| `POST /workspace/{id}/experiment/run` | `MLflowExperimentService.run_experiment()` | 실험 실행 |

| `GET /workspace/{id}/experiments` | `MLflowExperimentService.get_experiments_by_dataset()` | 실험 목록 |

| `GET /workspace/{id}/experiment/{eid}` | MLflow API | 실험 상세 |

기존 연동:

- `server/ddoc/ddoc/core/mlflow_experiment_service.py`

---

## 8. Phase 6: 프론트엔드 UI

### 8.1 WorkspaceStudio 메인

`server/frontend/src/components/WorkspaceStudio.jsx`:

- 드리프트 분석 결과에서 진입
- base/target 워크스페이스 탭 전환
- 5개 서브탭: 데이터 탐색, 분석, 샘플링, 실험, 스냅샷

### 8.2 서브 컴포넌트

| 컴포넌트 | 주요 기능 |

|---------|----------|

| `DataExplorer.jsx` | 이미지 그리드, 필터링, 상세보기 |

| `DataSampler.jsx` | 선택/삭제 UI, 샘플링 설정, 내보내기 |

| `AnalysisPanel.jsx` | 분석 실행 버튼, 결과 차트 표시 |

| `ExperimentPanel.jsx` | 코드 업로드, 실험 실행, MLflow 링크 |

| `SnapshotTimeline.jsx` | 타임라인 UI, 복원 버튼 |

### 8.3 DriftStudio 확장

`server/frontend/src/components/DriftStudio.jsx`:

- 드리프트 분석 완료 후 "워크스페이스 생성" 버튼 추가
- WorkspaceStudio로 네비게이션

---

## 9. Backend 프록시 설정

`server/backend/app/routers/workspace.py` (신규):

- ddoc-workspace 서비스로 프록시
- 또는 프론트엔드에서 직접 ddoc-workspace 호출

---

## 10. 구현 순서 요약

| 단계 | 작업 | 예상 기간 |

|------|------|----------|

| Phase 1 | Docker 인프라, ddoc-workspace 컨테이너 기본 | 2-3일 |

| Phase 2 | 워크스페이스/스냅샷 API (ddoc 연동) | 2-3일 |

| Phase 3 | 분석 기능 API (ddoc-plugin-vision 연동) | 2일 |

| Phase 4 | 샘플링 기능 (신규 구현) | 4-5일 |

| Phase 5 | 학습 실험 API (MLflow 연동) | 3일 |

| Phase 6 | 프론트엔드 UI | 5-7일 |

| 테스트 | 통합 테스트 및 버그 수정 | 2-3일 |

**총 예상**: 3-4주

### To-dos

- [ ] Phase 1: docker-compose.yml 확장 (ddoc-workspace, mlflow 서비스 추가)
- [ ] Phase 1: ddoc-workspace Dockerfile 및 requirements.txt 작성
- [ ] Phase 1: ddoc-workspace FastAPI 기본 구조 (main.py, schemas.py)
- [ ] Phase 2: 워크스페이스 CRUD API (WorkspaceService 연동)
- [ ] Phase 2: 스냅샷 API (SnapshotService 연동)
- [ ] Phase 3: 분석 API (ddoc-plugin-vision embedding/attribute analyzer 연동)
- [ ] Phase 4: SamplingService 신규 구현 (탐색, 수정, 샘플링 전략, 내보내기)
- [ ] Phase 4: 샘플링 API 엔드포인트 구현
- [ ] Phase 5: 학습 실험 API (MLflowExperimentService 연동, 코드 업로드)
- [ ] Phase 6: WorkspaceStudio.jsx 메인 컴포넌트
- [ ] Phase 6: 서브 컴포넌트 (DataExplorer, DataSampler, AnalysisPanel, ExperimentPanel, SnapshotTimeline)
- [ ] Phase 6: DriftStudio.jsx 확장 (워크스페이스 생성 버튼)
- [ ] 통합 테스트 및 버그 수정