# Trainer 기반 실험 시스템 가이드

## 개요

ddoc v2.0.3부터 도입된 Trainer 기반 실험 시스템은 사용자가 작성한 학습/평가 코드를 표준화된 인터페이스로 실행할 수 있게 해줍니다.

## 핵심 개념

### Trainer

Trainer는 `code/trainers/{trainer_name}/` 디렉토리에 위치한 학습/평가 코드입니다. 각 Trainer는 다음 구조를 따라야 합니다:

```
code/trainers/{trainer_name}/
├── train.py      # 필수: 학습 함수
├── eval.py       # 필수: 평가 함수
└── config.yaml   # 선택: 기본 설정
```

### 인터페이스 규약

#### train() 함수

```python
from pathlib import Path
from typing import Dict, Any

def train(
    dataset_path: Path,
    output_dir: Path,
    **kwargs
) -> Dict[str, Any]:
    """
    학습 함수
    
    Args:
        dataset_path: 데이터셋 경로 (Path 객체)
        output_dir: 실험 결과 저장 경로 (Path 객체)
        **kwargs: 추가 파라미터 (config.yaml 또는 CLI에서 전달)
    
    Returns:
        {
            "model_path": str,      # 학습된 모델 경로
            "metrics": dict,        # 메트릭 딕셔너리 (예: {"mAP50": 0.85})
            "artifacts": list       # 아티팩트 경로 리스트
        }
    """
    # 학습 로직 구현
    pass
```

#### evaluate() 함수

```python
from pathlib import Path
from typing import Dict, Any

def evaluate(
    model_path: Path,
    dataset_path: Path,
    output_dir: Path,
    **kwargs
) -> Dict[str, Any]:
    """
    평가 함수
    
    Args:
        model_path: 학습된 모델 경로
        dataset_path: 평가용 데이터셋 경로
        output_dir: 평가 결과 저장 경로
        **kwargs: 추가 파라미터
    
    Returns:
        {
            "metrics": dict,        # 평가 메트릭
            "artifacts": list       # 평가 결과 아티팩트
        }
    """
    # 평가 로직 구현
    pass
```

## 워크플로우

### 1. Trainer 코드 작성

예를 들어, YOLO 모델을 위한 Trainer를 작성한다면:

**code/trainers/yolo/train.py:**
```python
from pathlib import Path
from typing import Dict, Any
from ultralytics import YOLO

def train(
    dataset_path: Path,
    output_dir: Path,
    model: str = "yolov8n.pt",
    epochs: int = 100,
    batch: int = 16,
    **kwargs
) -> Dict[str, Any]:
    # YOLO 학습 로직
    yolo_model = YOLO(model)
    results = yolo_model.train(
        data=str(dataset_path / "data.yaml"),
        epochs=epochs,
        batch=batch,
        project=str(output_dir.parent),
        name=output_dir.name,
        **kwargs
    )
    
    # 메트릭 추출
    metrics = {
        "mAP50": results.results_dict.get("metrics/mAP50(B)", 0),
        "mAP50-95": results.results_dict.get("metrics/mAP50-95(B)", 0),
    }
    
    return {
        "model_path": str(output_dir / "weights" / "best.pt"),
        "metrics": metrics,
        "artifacts": [str(output_dir / "results.png")]
    }
```

### 2. Trainer 코드 추가

```bash
# Trainer 코드를 워크스페이스에 추가
ddoc add --code path/to/train.py --trainer yolo
ddoc add --code path/to/eval.py --trainer yolo
ddoc add --code path/to/config.yaml --trainer yolo
```

이렇게 하면 `code/trainers/yolo/` 디렉토리에 자동으로 정리됩니다.

### 3. 학습 실행

```bash
# 기본 설정으로 학습
ddoc exp train yolo --dataset my_dataset

# 모델 지정 (자동 다운로드 → models/)
ddoc exp train yolo --dataset my_dataset --model yolov8n.pt

# 로컬 모델 사용
ddoc exp train yolo --dataset my_dataset --model models/custom.pt
```

### 4. 평가 실행

```bash
# 학습된 모델 평가
ddoc exp eval yolo --dataset my_dataset --model experiments/exp_*/weights/best.pt
```

### 5. 결과 확인

```bash
# MLflow UI로 실험 결과 확인
mlflow ui

# 최고 성능 실험 찾기
ddoc exp best my_dataset --metric mAP50-95
```

## 모델 관리

### models/ 디렉토리

`models/` 디렉토리는 사전학습 모델과 커스텀 모델을 저장하는 곳입니다:

- **자동 다운로드**: 모델 이름만 지정하면 Ultralytics가 `models/`에 자동 다운로드
- **로컬 모델**: 직접 학습한 모델이나 커스텀 모델 저장
- **경로 해석**: `ddoc exp train` 실행 시 자동으로 생성되고 관리됨

### 모델 경로 해석 규칙

1. **모델 이름만 지정** (`yolov8n.pt`):
   - `models/` 디렉토리에서 먼저 검색
   - 없으면 자동 다운로드하여 `models/`에 저장

2. **상대 경로 지정** (`models/custom.pt`):
   - 워크스페이스 루트 기준으로 해석

3. **절대 경로 지정**:
   - 그대로 사용

## config.yaml

Trainer의 기본 설정을 정의하는 파일입니다:

```yaml
# code/trainers/yolo/config.yaml
model: "yolov8n.pt"
epochs: 100
batch: 16
imgsz: 640
device: "cpu"
```

이 설정은 `train()` 함수의 `**kwargs`로 전달됩니다.

## 데이터셋 준비

### YOLO 데이터셋 형식

YOLO Trainer를 사용하려면 데이터셋이 다음 구조를 따라야 합니다:

```
data/
└── dataset_name/
    ├── data.yaml          # 데이터셋 설정
    ├── train/
    │   ├── images/
    │   └── labels/
    ├── valid/
    │   ├── images/
    │   └── labels/
    └── test/
        ├── images/
        └── labels/
```

**data.yaml 예시:**
```yaml
names:
  - object
nc: 1
path: data/dataset_name    # 워크스페이스 루트 기준 상대 경로
train: train/images
val: valid/images
test: test/images
```

**중요**: `path` 필드는 워크스페이스 루트 기준 상대 경로를 사용해야 합니다. 이렇게 하면 서버 환경이나 Docker 컨테이너에서도 동일하게 작동합니다.

## 예제: YOLO Trainer 사용하기

### 1. 워크스페이스 초기화

```bash
ddoc init my_yolo_project
cd my_yolo_project
```

### 2. 데이터 추가

```bash
ddoc add --data /path/to/yolo_dataset.zip
```

### 3. YOLO Trainer 추가

```bash
# YOLO 예제 Trainer 코드 준비 (train.py, eval.py, config.yaml)
ddoc add --code train.py --trainer yolo
ddoc add --code eval.py --trainer yolo
ddoc add --code config.yaml --trainer yolo
```

### 4. 학습 실행

```bash
ddoc exp train yolo --dataset yolo_reference --model yolov8n.pt
```

### 5. 평가 실행

```bash
ddoc exp eval yolo --dataset yolo_reference \
  --model experiments/exp_20241218_120000/weights/best.pt
```

### 6. 결과 확인

```bash
# MLflow UI 실행
mlflow ui

# 최고 실험 찾기
ddoc exp best yolo_reference
```

## 사용자 정의 Trainer 작성

자신만의 Trainer를 만들려면:

1. **train.py 작성**: `train(dataset_path, output_dir, **kwargs)` 함수 구현
2. **eval.py 작성**: `evaluate(model_path, dataset_path, output_dir, **kwargs)` 함수 구현
3. **config.yaml 작성** (선택): 기본 파라미터 정의
4. **Trainer 추가**: `ddoc add --code ... --trainer custom`
5. **실험 실행**: `ddoc exp train custom --dataset ...`

## 베스트 프랙티스

### 1. Trainer 코드는 환경 독립적으로 작성

- 절대 경로 사용 금지
- 상대 경로 사용 권장
- 환경 변수나 설정 파일로 경로 관리

### 2. data.yaml은 상대 경로 사용

```yaml
path: data/dataset_name  # ✅ 좋은 예
path: /absolute/path     # ❌ 나쁜 예
path: .                  # ⚠️ 주의 필요 (YOLO가 현재 작업 디렉토리 기준으로 해석)
```

### 3. 모델은 models/ 디렉토리에 정리

- 사전학습 모델: `models/`에 저장
- 학습된 모델: `experiments/`에 저장
- 커스텀 모델: `models/`에 저장

### 4. 실험 결과는 MLflow로 관리

- 모든 실험은 자동으로 MLflow에 로깅됨
- MLflow UI로 실험 비교 및 분석
- `ddoc exp best`로 최고 실험 찾기

## 문제 해결

### Trainer를 찾을 수 없음

```
❌ Trainer 'yolo' not found in code/trainers
```

**해결책:**
- `code/trainers/yolo/` 디렉토리가 존재하는지 확인
- `train.py` 또는 `eval.py` 파일이 있는지 확인
- `ddoc add --code ... --trainer yolo` 명령으로 추가

### 모델을 찾을 수 없음

```
❌ Model not found: yolov8n.pt
```

**해결책:**
- `models/` 디렉토리가 생성되었는지 확인
- 모델 이름이 올바른지 확인 (예: `yolov8n.pt`, `yolov8s.pt`)
- 인터넷 연결 확인 (자동 다운로드 필요)

### data.yaml 경로 오류

```
Dataset 'data/dataset_name/data.yaml' images not found
```

**해결책:**
- `data.yaml`의 `path` 필드가 워크스페이스 루트 기준 상대 경로인지 확인
- `path: data/dataset_name` 형식 사용 권장

## 참고 자료

- [ddoc 문서 인덱스](../README.md)
- [워크스페이스 관리](workspace.md)
- [실험 관리](experiments.md)
- [YOLO 공식 문서](https://docs.ultralytics.com/)
- [MLflow 문서](https://mlflow.org/docs/latest/index.html)

