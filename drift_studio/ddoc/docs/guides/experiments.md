# 실험 관리

ddoc는 Trainer 기반 실험 시스템을 통해 모델 학습 및 평가를 관리합니다.

## Trainer 기반 실험 시스템

ddoc v2.0.3부터는 Trainer 기반 실험 시스템을 사용합니다. `code/trainers/` 폴더에 학습/평가 코드를 작성하면, ddoc가 해당 코드를 실행하는 인터페이스를 제공합니다.

자세한 내용은 [Trainer 시스템](trainer.md) 가이드를 참조하세요.

## 기본 명령어

### 학습 실행

```bash
ddoc exp train <trainer_name> --dataset <dataset_name> [--model <model>]
```

**예시:**
```bash
# 기본 모델 사용
ddoc exp train yolo --dataset yolo_reference

# 모델 지정 (자동 다운로드 → models/)
ddoc exp train yolo --dataset yolo_reference --model yolov8n.pt

# 로컬 모델 사용
ddoc exp train yolo --dataset yolo_reference --model models/custom.pt
```

### 평가 실행

```bash
ddoc exp eval <trainer_name> --dataset <dataset_name> --model <model_path>
```

**예시:**
```bash
# 학습 결과 모델 평가
ddoc exp eval yolo --dataset yolo_reference --model experiments/exp_20241218_120000/weights/best.pt

# models/ 디렉토리의 모델 평가 (자동 검색)
ddoc exp eval yolo --dataset yolo_reference --model best.pt
```

### 최고 성능 실험 찾기

```bash
ddoc exp best <dataset> [--metric <metric_name>]
```

**예시:**
```bash
# 기본 메트릭(mAP50-95) 기준 최고 실험
ddoc exp best yolo_reference

# 특정 메트릭 기준 최고 실험
ddoc exp best yolo_reference --metric mAP50
ddoc exp best yolo_reference --metric precision
```

## 실험 결과 확인

### MLflow UI

모든 실험은 자동으로 MLflow에 로깅됩니다:

```bash
mlflow ui
```

브라우저에서 `http://localhost:5000` 접속하여 실험 결과를 시각적으로 확인할 수 있습니다.

### 실험 결과 구조

```
experiments/
└── exp_20241218_120000/    # 실험 ID
    ├── weights/
    │   └── best.pt          # 최고 성능 모델
    ├── results.png          # 학습 곡선
    ├── confusion_matrix.png # 혼동 행렬
    └── ddoc_metadata.json   # ddoc 메타데이터
```

## 모델 관리

### models/ 디렉토리

- 사전학습 모델과 커스텀 모델을 저장하는 디렉토리
- Ultralytics가 자동 다운로드하는 모델도 `models/`에 저장됩니다
- `ddoc exp train` 실행 시 자동으로 생성됩니다

### 모델 경로 해석 규칙

1. **모델 이름만 지정** (`yolov8n.pt`): `models/`에서 찾거나 자동 다운로드
2. **상대 경로 지정** (`models/custom.pt`): 워크스페이스 기준으로 해석
3. **절대 경로 지정**: 그대로 사용

## 베스트 프랙티스

### 1. 실험 전 스냅샷 생성

```bash
# 실험 전
ddoc snapshot create -m "Before experiment X" -a before_exp_x

# 실험 수행
ddoc exp train yolo --dataset dataset_name

# 결과 확인 후 스냅샷
ddoc snapshot create -m "After experiment X - accuracy: 0.95" -a exp_x
```

### 2. MLflow UI 활용

```bash
# 실험 실행 후 MLflow UI로 결과 확인
mlflow ui

# 실험 비교, 메트릭 시각화, 모델 관리
```

### 3. 최고 실험 찾기

```bash
# 여러 실험 실행 후 최고 성능 실험 찾기
ddoc exp best dataset_name --metric mAP50-95
```

## 레거시 명령어 (Deprecated)

다음 명령어들은 v2.0.3에서 deprecated되었습니다:
- `ddoc exp run`: `ddoc exp train`으로 대체
- `ddoc exp list`: MLflow UI 사용 권장
- `ddoc exp show`: MLflow UI 사용 권장
- `ddoc exp compare`: MLflow UI 사용 권장
- `ddoc exp status`: MLflow UI 사용 권장

## 다음 단계

- [Trainer 시스템](trainer.md) - Trainer 작성 및 사용법
- [스냅샷 관리](snapshots.md) - 실험 결과와 함께 스냅샷 관리
- [고급 워크플로우](../advanced/workflows.md) - 고급 실험 워크플로우

