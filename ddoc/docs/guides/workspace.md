# 워크스페이스 관리

워크스페이스는 ddoc 프로젝트의 전체 작업 공간입니다. 이 가이드에서는 프로젝트 초기화, 파일 추가 및 관리 방법을 설명합니다.

## 프로젝트 초기화

### `ddoc init <path>`

새로운 ddoc 프로젝트를 초기화합니다.

```bash
ddoc init myproject              # 새 프로젝트 생성
ddoc init .                      # 현재 디렉토리 초기화
ddoc init sandbox/experiment     # 특정 경로에 생성
ddoc init . --force              # 기존 디렉토리 강제 초기화
```

**옵션:**
- `--force, -f`: 기존 디렉토리가 있어도 강제 초기화

### 초기화 시 생성되는 구조

```
project/
├── data/                    # 데이터셋 (DVC로 관리)
├── code/                    # 학습 코드 (Git으로 관리)
│   └── trainers/           # Trainer 코드
├── models/                  # 사전학습 모델 저장소
├── notebooks/               # EDA 노트북
├── experiments/             # 실험 결과 (MLflow 구조)
├── .ddoc/                   # ddoc 메타데이터
│   ├── snapshots/          # 스냅샷 YAML 파일
│   └── cache/              # 분석 캐시
├── .git/                    # Git 저장소 (자동 초기화)
├── .dvc/                    # DVC 설정 (자동 초기화)
└── data.dvc                 # data/ 전체 추적
```

초기화 시 다음이 자동으로 수행됩니다:
- 프로젝트 디렉토리 구조 생성
- Git 저장소 초기화
- DVC 초기화
- 설정 파일 생성

## 파일 추가

### `ddoc add`

파일을 워크스페이스에 추가합니다.

```bash
ddoc add --data <path>           # 데이터 추가
ddoc add --code <path>           # 코드 추가
ddoc add --notebook <path>       # 노트북 추가
```

### 데이터 추가

데이터는 `data/` 디렉토리에 추가되며 DVC로 자동 추적됩니다.

```bash
# 디렉토리 추가
ddoc add --data /path/to/dataset

# ZIP 파일 추가 (자동 압축 해제)
ddoc add --data /path/to/data.zip

# 여러 데이터셋 추가
ddoc add --data /path/to/train_data
ddoc add --data /path/to/test_data
```

**특징:**
- ZIP/TAR.GZ 파일은 자동으로 압축 해제됩니다
- 단일 폴더 아카이브는 자동으로 평탄화됩니다
- DVC로 자동 추적되어 버전 관리됩니다

### 코드 추가

코드는 `code/` 디렉토리에 추가되며 Git으로 자동 추적됩니다.

```bash
# 일반 코드 추가
ddoc add --code /path/to/script.py
ddoc add --code /path/to/models/resnet.py

# Trainer 코드 추가 (권장)
ddoc add --code /path/to/train.py --trainer yolo
ddoc add --code /path/to/eval.py --trainer yolo
ddoc add --code /path/to/config.yaml --trainer yolo
```

**Trainer 코드 구조:**
- `--trainer` 옵션을 사용하면 `code/trainers/{trainer_name}/` 디렉토리에 자동으로 정리됩니다
- Trainer는 `train()` 및 `evaluate()` 함수를 정의해야 합니다
- 자세한 내용은 [Trainer 시스템](trainer.md) 참조

### 노트북 추가

노트북은 `notebooks/` 디렉토리에 추가됩니다.

```bash
ddoc add --notebook /path/to/eda.ipynb
```

## 워크스페이스 구조 이해

### data/ 디렉토리

- 모든 데이터셋이 저장되는 디렉토리
- DVC로 버전 관리됨
- `data.dvc` 파일로 전체 디렉토리 추적

### code/ 디렉토리

- 학습 코드 및 스크립트 저장
- Git으로 버전 관리됨
- `code/trainers/` 하위에 Trainer 코드 저장

### models/ 디렉토리

- 사전학습 모델 및 커스텀 모델 저장
- `ddoc exp train` 실행 시 자동 생성
- Ultralytics가 자동 다운로드하는 모델도 여기에 저장

### experiments/ 디렉토리

- 실험 결과 저장 (MLflow 구조)
- 각 실험은 `exp_YYYYMMDD_HHMMSS` 형식의 디렉토리 생성
- 모델 가중치, 메트릭, 아티팩트 포함

### .ddoc/ 디렉토리

- ddoc 메타데이터 저장
- `.ddoc/snapshots/`: 스냅샷 YAML 파일
- `.ddoc/cache/`: 분석 캐시

## 베스트 프랙티스

### 1. 명확한 디렉토리 구조 유지

```
data/
├── dataset1/
│   ├── train/
│   └── valid/
└── dataset2/
    ├── train/
    └── valid/
```

### 2. Trainer 코드는 trainers/ 디렉토리에 정리

```bash
# Trainer 코드는 --trainer 옵션 사용
ddoc add --code train.py --trainer yolo
# → code/trainers/yolo/train.py로 자동 정리
```

### 3. 정기적인 Git 커밋

```bash
# 코드 변경 후 Git 커밋
git add .
git commit -m "Updated training script"
```

### 4. 스냅샷 생성

```bash
# 중요한 변경사항마다 스냅샷 생성
ddoc snapshot create -m "Added new dataset" -a v1
```

## 다음 단계

- [스냅샷 관리](snapshots.md) - 버전 관리 방법
- [Trainer 시스템](trainer.md) - 실험 시스템 사용법
- [데이터 분석](analysis.md) - EDA 및 Drift 감지

