---
name: FiftyOne 워크스페이스 연동 개선
overview: 단일 FiftyOne 세션을 workspace 컨테이너에서 실행하고, 워크스페이스 전환 시 session.dataset을 동적으로 교체하여 멀티 워크스페이스 지원을 구현합니다. (2025년 12월 9일)
todos:
  - id: docker-config
    content: "docker-compose.yml 수정: fiftyone 컨테이너 command 변경, workspace에 환경변수 및 포트 추가"
    status: pending
  - id: fiftyone-ops
    content: "fiftyone_ops.py 수정: 단일 세션 + dataset 교체 방식 구현"
    status: pending
  - id: nginx-config
    content: "nginx.conf 확인 및 수정: upstream을 workspace 컨테이너로 변경"
    status: pending
  - id: test-switch
    content: 워크스페이스 전환 테스트 및 검증
    status: pending
---

# FiftyOne 워크스페이스 연동 개선

## 문제 상황

- 현재 각 워크스페이스마다 `fo.launch_app()`을 호출하여 포트 8159에서 세션을 시작하려 함
- 워크스페이스 전환 시 포트 충돌 발생 및 세션 관리 실패
- URL이 `http://localhost:8159`로 브라우저의 localhost를 참조하여 Docker 환경에서 작동 안 함

## 해결 방안

단일 FiftyOne 세션을 workspace 컨테이너에서 실행하고, `session.dataset` 속성을 통해 데이터셋을 동적으로 교체

## 구현 계획

### 1. Docker 구성 수정

**파일**: [`docker-compose.yml`](docker-compose.yml)

fiftyone 컨테이너의 앱 실행 중지 (MongoDB만 유지):

```yaml
fiftyone:
  image: voxel51/fiftyone:latest
  container_name: fiftyone-server
  expose:
    - "8159"
  volumes:
    - workspaces_data:/workspaces
    - ./dvc_storage:/dvc_storage
    - fiftyone_data:/root/.fiftyone
  environment:
    - FIFTYONE_DATABASE_URI=mongodb://fiftyone-mongo:27017
    - FIFTYONE_DEFAULT_DATASET_DIR=/workspaces
  depends_on:
    - fiftyone-mongo
  # command 제거 또는 주석 처리
  # command: fiftyone app launch --address 0.0.0.0 --port 8159
  command: ["tail", "-f", "/dev/null"]  # 컨테이너만 유지
  networks:
    - app-network
```

workspace 컨테이너에 FiftyOne 환경 변수 추가:

```yaml
ddoc-workspace:
  # ... 기존 설정 ...
  environment:
    - MLFLOW_TRACKING_URI=http://mlflow:5050
    - WORKSPACES_ROOT=/workspaces
    - FIFTYONE_DATABASE_URI=mongodb://fiftyone-mongo:27017
    - FIFTYONE_DEFAULT_DATASET_DIR=/workspaces
  ports:
    - "8159:8159"  # FiftyOne 포트 노출
```

### 2. FiftyOne 세션 관리 로직 수정

**파일**: [`ddoc-workspace/app/routers/fiftyone_ops.py`](ddoc-workspace/app/routers/fiftyone_ops.py)

주요 변경사항:

```python
# 전역 변수 변경 (17-23번 줄)
WORKSPACES_ROOT = Path(os.getenv("WORKSPACES_ROOT", "/workspaces"))
FIFTYONE_PORT = int(os.getenv("FIFTYONE_PORT", "8159"))
FIFTYONE_ADDRESS = os.getenv("FIFTYONE_ADDRESS", "0.0.0.0")

# 단일 세션으로 변경
_fo_session: Optional[Any] = None
_fo_lock = threading.Lock()
```

`load_workspace_dataset` 함수 수정 (223-291번 줄):

- 기존: 워크스페이스별 세션 딕셔너리
- 변경: 단일 전역 세션, 데이터셋만 교체
```python
def switch_dataset():
    global _fo_session
    with _fo_lock:
        if _fo_session is None:
            # 첫 실행: 세션 생성
            _fo_session = fo.launch_app(
                dataset,
                remote=True,
                address=FIFTYONE_ADDRESS,
                port=FIFTYONE_PORT,
            )
        else:
            # 세션 존재: 데이터셋만 교체
            _fo_session.dataset = dataset
```


URL 반환 수정 (211-220번 줄):

```python
return {
    "url": "/fiftyone/",  # nginx 프록시 경로
    "port": FIFTYONE_PORT,
    "workspace_id": workspace_id,
    "current_dataset": _fo_session.dataset.name if _fo_session else None
}
```

`get_fiftyone_status` 함수 수정 (169-208번 줄):

- 전역 `_fo_session` 사용
- 현재 로드된 데이터셋 정보 반환

`close_fiftyone_session` 함수 수정 (294-308번 줄):

- 전역 세션 종료

### 3. Nginx 설정 확인

**파일**: [`nginx.conf`](nginx.conf)

기존 FiftyOne 프록시 설정 확인 (156-165번 줄):

```nginx
location /fiftyone/ {
    rewrite ^/fiftyone/(.*) /$1 break;
    
    proxy_pass http://ddoc-workspace:8159;  # workspace 컨테이너로 변경
    proxy_http_version 1.1;
    
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

upstream 정의 확인/수정 필요 시:

```nginx
upstream fiftyone {
    server ddoc-workspace:8159;  # workspace 컨테이너를 가리키도록
}
```

### 4. 프론트엔드 URL 처리 확인

**파일**: [`frontend/src/components/workspace/DataExplorer.jsx`](frontend/src/components/workspace/DataExplorer.jsx)

현재 코드 확인:

- 98번 줄: `setFiftyoneUrl(urlRes.data.url)` - API에서 받은 URL 사용
- 185번 줄: `src={fiftyoneUrl}` - iframe에 URL 적용

변경 불필요 (백엔드에서 `/fiftyone/`를 반환하면 자동 적용됨)

### 5. MongoDB 연결 설정

**파일**: [`ddoc-workspace/app/routers/fiftyone_ops.py`](ddoc-workspace/app/routers/fiftyone_ops.py)

`load_fiftyone_dataset` 함수 내부에 MongoDB URI 설정 추가 (89-166번 줄):

```python
def load_fiftyone_dataset(workspace_id: str, data_path: Path, dataset_name: str, force_reload: bool = False):
    try:
        import fiftyone as fo
        
        # MongoDB 연결 설정
        mongo_uri = os.getenv("FIFTYONE_DATABASE_URI", "mongodb://fiftyone-mongo:27017")
        fo.config.database_uri = mongo_uri
        
        # ... 나머지 로직
    except ImportError:
        raise HTTPException(...)
```

## 테스트 시나리오

1. Base 워크스페이스 접근 -> FiftyOne 세션 시작 확인
2. Target 워크스페이스로 전환 -> 데이터셋 교체 확인
3. 다시 Base로 복귀 -> 즉시 전환 확인
4. iframe에서 UI가 정상 작동하는지 확인

## 주요 개선점

- 포트 충돌 제거
- 워크스페이스 전환 시 즉각적인 데이터셋 교체
- nginx 프록시를 통한 안정적인 URL
- 세션 재시작 없이 효율적인 전환