# ddoc Workspace 대대적 개편 계획

**작성일**: 2025-12-05

---

## Phase 1: 핵심 인프라 및 버그 수정

### 1.1 데이터 이식 버그 수정

**문제**: Docker 볼륨 마운트 경로 불일치로 워크스페이스 생성 시 데이터가 복사되지 않음

**수정 파일**: [`ddoc-workspace/app/routers/workspace.py`](ddoc-workspace/app/routers/workspace.py)

```python
# 경로 변환 로직 추가 (Line 97-106 수정)
def convert_container_path(path_str: str) -> str:
    """컨테이너 간 경로 차이를 변환"""
    mappings = {"/app/dvc_storage": "/dvc_storage"}
    for old, new in mappings.items():
        if path_str.startswith(old):
            return path_str.replace(old, new, 1)
    return path_str

# create_workspace 함수 내 수정
source_path = Path(convert_container_path(request.source_path))
```

### 1.2 워크스페이스 독립 페이지 라우팅

**수정/생성 파일**:

- [`frontend/src/App.jsx`](frontend/src/App.jsx) - 라우터 설정 추가
- `frontend/src/pages/WorkspacePage.jsx` (신규) - 독립 페이지 컴포넌트
```jsx
// App.jsx에 라우트 추가
<Route path="/workspace/:workspaceId" element={<WorkspacePage />} />
```


### 1.3 스냅샷 생성 정책 구현

**스냅샷 생성 정책**:

| 상황 | 생성 | 제어 |

|------|------|------|

| 워크스페이스 최초 생성 | 자동 | 시스템 (baseline) |

| 데이터 물리적 변형 | 필수 | 시스템 강제 |

| 분석/실험 후 | 선택 | 사용자 수동 |

**수정 파일**: [`ddoc-workspace/app/routers/workspace.py`](ddoc-workspace/app/routers/workspace.py)

```python
# create_workspace 함수 끝부분에 추가
from ddoc.core.snapshot_service import get_snapshot_service

# 데이터 복사 성공 후 초기 스냅샷 생성 (baseline)
if data_copied:
    snapshot_service = get_snapshot_service(str(workspace_path))
    snapshot_service.create_snapshot(
        message="초기 워크스페이스 상태 (baseline)",
        alias="init",
        auto_commit=True
    )
    metadata["snapshot_count"] = 1
```

**생성 파일**: `ddoc-workspace/app/routers/data_ops.py` (Phase 2에서 구현)

```python
# 데이터 변형 시 스냅샷 필수 생성
@router.post("/{workspace_id}/data/apply-view")
async def apply_view_changes(workspace_id: str, request: ApplyViewRequest):
    # 1. 데이터 변형 적용
    result = await apply_data_transformation(...)
    
    # 2. 변형 성공 시 스냅샷 필수 생성 (시스템 강제)
    if result["files_modified"] > 0:
        snapshot_service.create_snapshot(
            message=request.snapshot_message,  # 사용자 입력 필수
            alias=request.snapshot_alias,
            auto_commit=True
        )
    
    return result
```

### 1.4 스냅샷 계보 시각화 개선

**수정 파일**: [`frontend/src/components/workspace/SnapshotTimeline.jsx`](frontend/src/components/workspace/SnapshotTimeline.jsx)

- 현재 타임라인을 계보 그래프로 확장
- 분기(branch) 시각화 지원
- 현재 위치 표시 강화

### 1.5 분석 히스토리 UI 추가

**수정 파일**: [`frontend/src/components/workspace/AnalysisPanel.jsx`](frontend/src/components/workspace/AnalysisPanel.jsx)

- 스냅샷 선택 드롭다운 추가
- 분석 히스토리 목록 컴포넌트 추가
- 분석 결과 비교 기능

### 1.6 실험 파라미터 확장

**수정 파일**: [`frontend/src/components/workspace/ExperimentPanel.jsx`](frontend/src/components/workspace/ExperimentPanel.jsx)

추가 파라미터:

- learning_rate, lr_scheduler, warmup_epochs
- augmentation 옵션 (mosaic, mixup, hsv)
- early_stopping, save_best_only
- device 선택

---

## Phase 2: FiftyOne 통합 및 데이터 조작

### 2.1 FiftyOne 컨테이너 설정

**수정 파일**: [`docker-compose.yml`](docker-compose.yml)

```yaml
fiftyone:
  image: voxel51/fiftyone:latest
  container_name: fiftyone-server
  ports:
    - "8159:8159"
  volumes:
    - ./workspaces:/workspaces
    - ./dvc_storage:/dvc_storage
  environment:
    - FIFTYONE_DATABASE_URI=mongodb://mongo:27017
  depends_on:
    - mongo
  command: fiftyone app launch --address 0.0.0.0 --port 8159

mongo:
  image: mongo:6
  container_name: fiftyone-mongo
  volumes:
    - fiftyone_db:/data/db
```

### 2.2 FiftyOne 세션 관리 API

**생성 파일**: `ddoc-workspace/app/routers/fiftyone_ops.py`

엔드포인트:

- `POST /workspace/{id}/fiftyone/load` - 워크스페이스 데이터셋 로드
- `GET /workspace/{id}/fiftyone/views` - 저장된 View 목록
- `POST /workspace/{id}/fiftyone/save-view` - 현재 View 저장

### 2.3 FiftyOne iframe 통합 UI

**수정 파일**: [`frontend/src/components/workspace/DataExplorer.jsx`](frontend/src/components/workspace/DataExplorer.jsx)

- FiftyOne iframe 임베딩
- 워크스페이스 전환 시 데이터셋 로드 API 호출
- View 목록 동기화

### 2.4 Direct Apply + Snapshot API

**생성 파일**: `ddoc-workspace/app/routers/data_ops.py`

```python
@router.post("/{workspace_id}/data/apply-view")
async def apply_view_changes(workspace_id: str, request: ApplyViewRequest):
    """
    FiftyOne View 기반으로 데이터 변경 적용 + 스냅샷 생성
    1. View에 포함되지 않은 샘플 파일 삭제
    2. FiftyOne 데이터셋 업데이트
    3. DVC add + git commit
    4. 스냅샷 생성
    """

class ApplyViewRequest(BaseModel):
    view_name: str
    operation: str  # "keep_only" | "remove"
    snapshot_message: str
    snapshot_alias: Optional[str]
    dry_run: bool = False
```

### 2.5 데이터 조작 UI

**수정 파일**:

- [`frontend/src/components/workspace/DataSampler.jsx`](frontend/src/components/workspace/DataSampler.jsx) 전면 개편

기능:

- View 선택 드롭다운
- 작업 유형 선택 (View만 유지 / View 제거)
- 미리보기 (삭제될 파일 수 등)
- 스냅샷 메시지/별칭 입력
- "변경 적용 & 스냅샷 생성" 버튼

---

## 파일 구조 변경 요약

```
frontend/src/
├── pages/
│   └── WorkspacePage.jsx          # 신규
├── components/
│   ├── workspace/
│   │   ├── SnapshotTimeline.jsx   # 수정 (계보 그래프)
│   │   ├── DataExplorer.jsx       # 수정 (FiftyOne iframe)
│   │   ├── DataSampler.jsx        # 전면 개편
│   │   ├── AnalysisPanel.jsx      # 수정 (히스토리)
│   │   └── ExperimentPanel.jsx    # 수정 (파라미터 확장)

ddoc-workspace/app/
├── routers/
│   ├── workspace.py               # 수정 (경로 변환, 첫 스냅샷)
│   ├── fiftyone_ops.py            # 신규
│   └── data_ops.py                # 신규

docker-compose.yml                  # 수정 (FiftyOne, MongoDB 추가)
```