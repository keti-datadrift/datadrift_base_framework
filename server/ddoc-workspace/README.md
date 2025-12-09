# ddoc-workspace

ddoc 워크스페이스 서비스 - 드리프트 분석 후 데이터셋 관리, 분석, 샘플링, 학습 실험을 위한 REST API 서비스

## 기능

- **워크스페이스 관리**: 드리프트 분석 결과에서 base/target 워크스페이스 생성
- **스냅샷**: 데이터 + 코드 상태 저장/복원
- **분석**: ddoc-plugin-vision을 통한 임베딩/속성 분석
- **샘플링**: 데이터 탐색, 추가/삭제, 샘플링, 포맷 변환 내보내기
- **학습 실험**: 트레이너 코드 실행, MLflow 연동

## API 엔드포인트

### 워크스페이스
- `POST /workspace/create` - 워크스페이스 생성
- `GET /workspaces` - 워크스페이스 목록
- `GET /workspace/{id}/status` - 상태 조회
- `DELETE /workspace/{id}` - 삭제

### 스냅샷
- `POST /workspace/{id}/snapshot` - 스냅샷 생성
- `GET /workspace/{id}/snapshots` - 스냅샷 목록
- `POST /workspace/{id}/snapshot/{sid}/restore` - 복원
- `GET /workspace/{id}/lineage` - 계보 그래프

### 분석
- `POST /workspace/{id}/analyze/embedding` - 임베딩 분석
- `POST /workspace/{id}/analyze/attributes` - 속성 분석
- `GET /workspace/{id}/analysis/results` - 결과 조회

### 샘플링
- `GET /workspace/{id}/data/items` - 데이터 목록
- `GET /workspace/{id}/data/stats` - 통계
- `POST /workspace/{id}/data/add` - 추가
- `POST /workspace/{id}/data/remove` - 삭제
- `POST /workspace/{id}/data/sample` - 샘플 생성
- `POST /workspace/{id}/data/export` - 내보내기

### 실험
- `POST /workspace/{id}/code/upload` - 코드 업로드
- `GET /workspace/{id}/code/templates` - 템플릿
- `POST /workspace/{id}/experiment/run` - 실험 실행
- `GET /workspace/{id}/experiments` - 실험 목록

## 실행

### Docker Compose (권장)

```bash
cd server
docker-compose up -d
```

### 로컬 개발

```bash
cd server/ddoc-workspace
pip install -r requirements.txt
uvicorn app.main:app --reload --port 5000
```

## 환경 변수

- `WORKSPACES_ROOT`: 워크스페이스 저장 경로 (기본: `/workspaces`)
- `MLFLOW_TRACKING_URI`: MLflow 서버 URI (기본: `http://mlflow:5050`)
- `DDOC_ROOT`: ddoc 소스 경로 (기본: `/ddoc`)

## 연동

### 프론트엔드
```javascript
const WORKSPACE_API = "http://localhost:5001";
```

### MLflow
- 실험 결과 조회: `http://localhost:5050`

## 데이터셋 포맷 지원

- **입력**: YOLO, COCO, Pascal VOC
- **내보내기**: YOLO, COCO, Pascal VOC
