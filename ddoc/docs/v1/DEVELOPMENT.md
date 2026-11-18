# ddoc 개발 문서

## 🏗️ 아키텍처 개요

ddoc은 플러그인 기반의 확장 가능한 데이터 드리프트 감지 프레임워크입니다. 핵심 엔진과 플러그인 시스템으로 구성되어 다양한 데이터 모달리티와 분석 도구를 지원합니다.

## 📁 프로젝트 구조

```
ddoc/
├── ddoc/                           # 핵심 프레임워크
│   ├── cli/                        # CLI 명령어 (Typer)
│   │   └── commands.py             # 모든 CLI 명령어 정의
│   ├── core/                       # 핵심 엔진
│   │   ├── staging_service.py      # Staging 시스템 (NEW)
│   │   ├── dataset_service.py      # 데이터셋 관리
│   │   ├── version_service.py      # 버전 관리
│   │   ├── metadata_service.py     # 메타데이터 및 Lineage
│   │   └── experiment_service.py   # 실험 관리
│   ├── ops/                        # 분석 연산
│   │   └── core_ops.py             # 핵심 연산 구현
│   └── plugins/                    # 플러그인 시스템
│       └── hookspecs.py            # 훅 스펙 정의
├── plugins/                        # 플러그인 구현
│   ├── ddoc-plugin-vision/         # 비전 분석 플러그인
│   │   ├── ddoc_plugin_vision/
│   │   │   └── vision_impl.py      # 비전 분석 구현
│   │   └── pyproject.toml
│   └── ddoc-plugin-yolo/           # YOLO 학습 플러그인
│       ├── ddoc_plugin_yolo/
│       │   └── yolo_impl.py        # YOLO 학습 구현
│       └── pyproject.toml
├── .ddoc_metadata/                 # 메타데이터 저장소 (NEW)
│   ├── staging.json                # Staging area
│   ├── dataset_versions.json       # 버전 정보
│   ├── dataset_mappings.json       # 데이터셋 매핑
│   └── lineage.json                # Lineage 그래프
├── datasets/                       # DVC 관리 데이터셋
├── analysis/                       # 분석 결과
├── experiments/                    # 실험 결과
└── ddocv2_*.sh                     # 테스트 스크립트
```

## 🔄 새로운 Staging 시스템 아키텍처

### Git/DVC 스타일 워크플로우 (2025-11-04 업데이트)

ddoc은 이제 Git과 유사한 staging → commit 워크플로우를 사용합니다:

#### 1. Staging Area (`.ddoc_metadata/staging.json`)
```json
{
  "staged_datasets": {
    "my_data": {
      "operation": "new",           // "new" | "modified"
      "path": "/path/to/data",
      "formats": [".jpg", ".png"],
      "config": null,
      "current_hash": "abc123...",
      "staged_at": "2025-11-04T10:30:00"
    }
  },
  "last_updated": "2025-11-04T10:30:00"
}
```

#### 2. 워크플로우 단계

**Stage (add)**:
```bash
ddoc dataset add my_data ./data/my_data    # 신규 데이터셋
ddoc dataset add my_data                   # 기존 데이터셋 변경사항
```
- DVC tracking 시작
- 변경사항을 staging area에 기록
- Git commit은 실행하지 않음

**Status**:
```bash
ddoc dataset status
```
- Staged changes (commit 대기 중)
- Unstaged changes (아직 add 안 함)
- Untracked datasets

**Commit**:
```bash
ddoc dataset commit -m "message" -t v1.0
```
- Staged 데이터셋에 대한 버전 생성
- Lineage 그래프 업데이트
- Git commit (선택적)
- Staging area 초기화

**Unstage**:
```bash
ddoc dataset unstage my_data
```
- Staging area에서 제거 (commit 취소)

#### 3. 서비스 레이어 구조

```
StagingService
├── stage_dataset()        # 데이터셋 stage
├── unstage_dataset()      # 데이터셋 unstage
├── get_staged_changes()   # staged 변경사항 조회
└── clear_staging()        # staging area 초기화

DatasetService
├── stage_dataset()        # add 명령 구현
├── commit_staged_datasets()  # commit 명령 구현
└── get_full_status()      # status 명령 구현

VersionService (변경 없음)
└── create_dataset_version()  # 버전 생성

MetadataService (변경 없음)
└── add_dataset()          # Lineage 추가
```

## 🔌 플러그인 시스템

### 핵심 인터페이스

#### 1. 데이터 소스 인터페이스
```python
class DataSource(ABC):
    @abstractmethod
    def load_data(self, path: str) -> Dataset:
        """데이터 로드"""
        pass
```

#### 2. 분석 연산 인터페이스
```python
class AnalysisPlugin(ABC):
    @abstractmethod
    def eda_run(self, input_path: str, modality: str, output_path: str) -> Dict:
        """EDA 분석 실행"""
        pass
    
    @abstractmethod
    def drift_detect(self, ref_path: str, cur_path: str, detector: str, 
                    cfg: Dict, output_path: str) -> Dict:
        """드리프트 감지"""
        pass
```

#### 3. 학습 인터페이스
```python
class TrainingPlugin(ABC):
    @abstractmethod
    def train(self, dataset: str, params: Dict) -> ExperimentResult:
        """모델 학습"""
        pass
    
    @abstractmethod
    def generate_dvc_metadata(self, result: ExperimentResult) -> DVCCompatibleMetadata:
        """DVC 호환 메타데이터 생성"""
        pass
```

### 플러그인 구현 예시

#### Vision Plugin (`ddoc-plugin-vision`)
```python
@hookimpl
def eda_run(self, input_path: str, modality: str, output_path: str) -> Dict:
    """이미지 EDA 분석"""
    # 1. 이미지 파일 검색
    # 2. 속성 분석 (크기, 노이즈, 선명도)
    # 3. 임베딩 추출 (CLIP)
    # 4. 클러스터링 (K-means)
    # 5. 결과 저장
    pass

@hookimpl
def drift_detect(self, ref_path: str, cur_path: str, detector: str, 
                cfg: Dict, output_path: str) -> Dict:
    """드리프트 감지"""
    # 1. 속성 드리프트 (KL Divergence)
    # 2. 임베딩 드리프트 (MMD)
    # 3. 시각화 생성
    # 4. 결과 저장
    pass
```

#### YOLO Plugin (`ddoc-plugin-yolo`)
```python
@hookimpl
def retrain_run(self, train_path: str, trainer: str, params: Dict, 
                model_out: str) -> Dict:
    """YOLO 모델 학습"""
    # 1. data.yaml 생성
    # 2. YOLO 모델 학습
    # 3. 메트릭 추출
    # 4. 결과 저장
    pass
```

## 🔄 데이터 플로우

### 1. 데이터셋 등록
```
사용자 입력 → DatasetTracker → DVC 등록 → Git 커밋
```

### 2. EDA 분석
```
데이터셋 → Vision Plugin → 속성/임베딩 분석 → 결과 저장
```

### 3. 드리프트 감지
```
두 데이터셋 → Vision Plugin → 드리프트 계산 → 시각화 생성
```

### 4. 모델 학습
```
데이터셋 → YOLO Plugin → 모델 학습 → 실험 추적
```

## 🤖 학습 파이프라인 구현

### YOLO 학습 플러그인 (`ddoc-plugin-yolo`)

#### 핵심 기능
- **Ultralytics YOLO 통합**: yolov8n, yolov8s, yolov10n 등 지원
- **자동 data.yaml 생성**: YOLO 형식 데이터셋 자동 설정
- **실험 추적**: 학습 메트릭 자동 수집 및 저장
- **DVC 호환**: 실험 메타데이터를 DVC 형식으로 저장

#### 구현된 메서드

##### 1. `retrain_run` - 모델 학습
```python
@hookimpl
def retrain_run(self, train_path: str, trainer: str, params: Dict, model_out: str) -> Dict:
    """YOLO 모델 학습 실행"""
    # 1. 파라미터 추출 (model, epochs, batch, device 등)
    # 2. data.yaml 자동 생성
    # 3. Ultralytics YOLO 모델 로드
    # 4. 학습 실행 (model.train())
    # 5. 메트릭 추출 (mAP50, precision, recall 등)
    # 6. 실험 메타데이터 저장
    # 7. 결과 반환
```

##### 2. `train` - 표준화된 학습 인터페이스
```python
def train(self, dataset: str, params: Dict) -> ExperimentResult:
    """TrainingPlugin 인터페이스 구현"""
    # 1. 실험 ID 생성
    # 2. 학습 시작 시간 기록
    # 3. YOLO 모델 학습 실행
    # 4. 학습 완료 시간 기록
    # 5. 메트릭 추출 및 저장
    # 6. ExperimentResult 객체 생성
```

##### 3. `generate_dvc_metadata` - DVC 호환 메타데이터
```python
def generate_dvc_metadata(self, result: ExperimentResult) -> DVCCompatibleMetadata:
    """DVC 호환 메타데이터 생성"""
    # 1. 실험 ID, 데이터셋, 플러그인 정보
    # 2. 시작/종료 시간
    # 3. 학습 메트릭 (mAP50, precision, recall)
    # 4. 하이퍼파라미터 (epochs, batch, device)
    # 5. 모델 경로 (weights/best.pt)
```

#### 학습 메트릭 추출
```python
def _extract_metrics(self, results, exp_dir: Path) -> Dict[str, Any]:
    """학습 결과에서 메트릭 추출"""
    metrics = {
        'mAP50': results.metrics.get('metrics/mAP50(B)', 0.0),
        'mAP50-95': results.metrics.get('metrics/mAP50-95(B)', 0.0),
        'precision': results.metrics.get('metrics/precision(B)', 0.0),
        'recall': results.metrics.get('metrics/recall(B)', 0.0),
        'box_loss': results.metrics.get('train/box_loss', 0.0),
        'cls_loss': results.metrics.get('train/cls_loss', 0.0),
        'dfl_loss': results.metrics.get('train/dfl_loss', 0.0),
        'val_box_loss': results.metrics.get('val/box_loss', 0.0),
        'val_cls_loss': results.metrics.get('val/cls_loss', 0.0),
        'val_dfl_loss': results.metrics.get('val/dfl_loss', 0.0)
    }
    return metrics
```

#### 자동 data.yaml 생성
```python
def _create_data_yaml(self, train_path: str, params: Dict[str, Any]) -> str:
    """YOLO 형식 data.yaml 파일 자동 생성"""
    # 1. 데이터셋 경로 확인
    # 2. 클래스 정보 추출 (라벨 파일에서)
    # 3. data.yaml 구조 생성:
    #    - path: 데이터셋 루트 경로
    #    - train: train/images
    #    - val: valid/images  
    #    - test: test/images
    #    - nc: 클래스 수
    #    - names: 클래스 이름 리스트
```

### 실험 추적 시스템

#### ExperimentResult 클래스
```python
@dataclass
class ExperimentResult:
    experiment_id: str
    dataset: str
    plugin: str
    start_time: datetime
    end_time: Optional[datetime]
    metrics: Dict[str, Any]
    params: Dict[str, Any]
    output_dir: str
```

#### 실험 메타데이터 저장
```json
{
  "experiment_id": "exp_001_20251022-150812",
  "dataset": "test_yolo",
  "plugin": "yolo",
  "start_time": "2025-10-22T15:08:12.369534",
  "end_time": "2025-10-22T15:23:45.123456",
  "metrics": {
    "mAP50": 0.94766,
    "mAP50-95": 0.60997,
    "precision": 0.96097,
    "recall": 0.90652,
    "box_loss": 1.34198,
    "cls_loss": 1.45402,
    "dfl_loss": 1.2244
  },
  "params": {
    "model": "yolov8n.pt",
    "epochs": 1,
    "batch": 4,
    "device": "cpu",
    "imgsz": 640
  },
  "output_dir": "experiments/test_fix_yolo"
}
```

### CLI 명령어 통합

#### `ddoc train` 명령어
```python
@app.command()
def train(
    dataset: str = typer.Argument(..., help="Dataset name or path"),
    model: str = typer.Option("yolov8n.pt", "--model", "-m", help="YOLO model"),
    epochs: int = typer.Option(100, "--epochs", "-e", help="Number of epochs"),
    batch: int = typer.Option(16, "--batch", "-b", help="Batch size"),
    device: str = typer.Option("cpu", "--device", "-d", help="Device"),
    exp_name: Optional[str] = typer.Option(None, "--name", "-n", help="Experiment name")
):
    """Train YOLO model on a dataset"""
    # 1. 실험 메타데이터 생성
    # 2. YOLO 플러그인 호출
    # 3. 실험 추적기 저장
    # 4. 메타데이터 연결
```

#### 실험 관리 명령어
```python
@app.command("exp-list")
def exp_list_command():
    """실험 목록 조회"""
    
@app.command("exp-show") 
def exp_show_command(exp_name: str):
    """실험 상세 정보"""
    
@app.command("exp-compare")
def exp_compare_command(exp1: str, exp2: str):
    """실험 비교"""
```

### 학습 파이프라인 워크플로우

#### 1. 데이터셋 준비
```bash
# YOLO 형식 데이터셋 구조
datasets/test_yolo/
├── train/
│   ├── images/          # 학습 이미지
│   └── labels/          # 학습 라벨
├── valid/
│   ├── images/          # 검증 이미지
│   └── labels/          # 검증 라벨
├── test/
│   ├── images/          # 테스트 이미지
│   └── labels/          # 테스트 라벨
└── data.yaml           # 데이터셋 설정
```

#### 2. 모델 학습 실행
```bash
# 기본 학습
ddoc train test_yolo

# 고급 옵션
ddoc train test_yolo --model yolov8s.pt --epochs 50 --batch 16 --device cpu --name my_experiment
```

#### 3. 실험 결과 확인
```bash
# 실험 목록
ddoc exp list

# 실험 상세 정보
ddoc exp show my_experiment

# 실험 비교
ddoc exp compare exp1 exp2
```

#### 4. 결과 파일 구조
```
experiments/my_experiment/
├── weights/
│   ├── best.pt          # 최고 성능 모델
│   └── last.pt          # 마지막 에포크 모델
├── results.csv          # 학습 메트릭 시계열
├── results.png          # 학습 곡선 그래프
├── confusion_matrix.png # 혼동 행렬
├── experiment_metadata.json # 실험 메타데이터
└── args.yaml           # 학습 파라미터
```

### 성능 최적화

#### GPU 가속 지원
```bash
# GPU 사용 (CUDA)
ddoc train test_yolo --device 0

# GPU 사용 (MPS - Apple Silicon)
ddoc train test_yolo --device mps
```

#### 배치 크기 최적화
```bash
# 메모리 효율적인 학습
ddoc train test_yolo --batch 8 --imgsz 416

# 고성능 학습
ddoc train test_yolo --batch 32 --imgsz 640
```

#### 모델 선택
```bash
# 경량 모델 (빠른 학습)
ddoc train test_yolo --model yolov8n.pt

# 중간 모델 (균형)
ddoc train test_yolo --model yolov8s.pt

# 고성능 모델 (정확도 우선)
ddoc train test_yolo --model yolov8m.pt
```

## 📊 메타데이터 관리

### 데이터셋 메타데이터
```json
{
  "name": "test_data",
  "path": "datasets/test_data",
  "version": "latest",
  "files": 97,
  "formats": [".jpg", ".png"],
  "dvc_file": "datasets/test_data.dvc"
}
```

### 실험 메타데이터
```json
{
  "experiment_id": "exp_001",
  "dataset": "test_yolo",
  "plugin": "yolo",
  "start_time": "2025-10-22T15:08:12",
  "end_time": "2025-10-22T15:23:45",
  "metrics": {
    "mAP50": 0.94766,
    "mAP50-95": 0.60997,
    "precision": 0.96097,
    "recall": 0.90652
  },
  "params": {
    "epochs": 1,
    "batch": 4,
    "device": "cpu"
  }
}
```

## 🛠️ 개발 가이드

### 새 플러그인 개발

#### 1. 플러그인 구조 생성
```bash
mkdir plugins/ddoc-plugin-myplugin
cd plugins/ddoc-plugin-myplugin
mkdir ddoc_plugin_myplugin
```

#### 2. setup.py 작성
```python
from setuptools import setup, find_packages

setup(
    name="ddoc-plugin-myplugin",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["ddoc"],
    entry_points={
        "ddoc.plugins": [
            "myplugin = ddoc_plugin_myplugin:MyPlugin",
        ],
    },
)
```

#### 3. 플러그인 구현
```python
from ddoc.plugins import hookimpl
from ddoc.tracking.experiment_interface import TrainingPlugin

class MyPlugin(TrainingPlugin):
    @hookimpl
    def train(self, dataset: str, params: Dict) -> ExperimentResult:
        # 플러그인 로직 구현
        pass
```

### CLI 명령어 추가

#### commands.py에 새 명령어 추가
```python
@app.command()
def my_command(
    input: str = typer.Argument(..., help="Input path"),
    output: str = typer.Option("output", "--output", "-o", help="Output path"),
):
    """My custom command."""
    # 명령어 로직 구현
    pass
```

## 🧪 테스트 및 검증

### 단위 테스트
```bash
# 플러그인 테스트
python -m pytest plugins/ddoc-plugin-vision/tests/

# CLI 테스트
python -m pytest ddoc/cli/tests/
```

### 통합 테스트
```bash
# 전체 파이프라인 테스트
./ddocv2_test_dataprocess.sh test_data test_yolo_sample
./ddocv2_test_modelprocess.sh test_data test_yolo_sample
```

### 성능 벤치마크
```bash
# EDA 분석 성능
time ddoc analyze test_data

# 드리프트 분석 성능
time ddoc drift-compare test_data test_yolo_sample
```

## 📈 다음 단계 계획

### Phase 5: 실험 추적 시스템 강화 🔬

#### 5.1 실험 목록 및 비교 기능
**목표**: 실험 조회, 비교, 상세 정보 확인

**구현할 CLI 명령어**:
```bash
ddoc exp list                    # 실험 목록
ddoc exp show <exp_name>         # 실험 상세 정보
ddoc exp compare <exp1> <exp2>   # 실험 비교
```

**필요 작업**:
- `ExperimentTracker` 확장 (실험 조회, 비교)
- 실험 비교 시각화
- 메트릭 차이점 분석

#### 5.2 실험-데이터 계보 추적
**목표**: 데이터셋 → 분석 → 실험의 전체 계보 시각화

**구현할 CLI 명령어**:
```bash
ddoc lineage show <dataset>      # 데이터셋 계보
ddoc lineage graph              # 전체 계보 그래프
```

**필요 작업**:
- `LineageTracker` 구현
- DAG 그래프 생성 (NetworkX)
- 계보 시각화 (Graphviz)

### Phase 6: DVC 파이프라인 자동화 🔄

#### 6.1 DVC 파이프라인 자동 생성
**목표**: 분석 파이프라인을 DVC 파이프라인으로 자동 변환

**구현할 CLI 명령어**:
```bash
ddoc pipeline generate          # 파이프라인 생성
ddoc pipeline run              # 파이프라인 실행
```

**필요 작업**:
- `dvc.yaml` 자동 생성
- 파이프라인 단계 정의
- 의존성 그래프 생성

#### 6.2 DVC Plots 통합
**목표**: 메트릭 시계열, 실험 비교 차트 자동 생성

**구현할 CLI 명령어**:
```bash
ddoc plots show                # 플롯 생성
ddoc plots compare             # 비교 플롯
```

**필요 작업**:
- 메트릭 TSV/JSON 생성
- DVC Plots 통합
- 시계열 시각화

### Phase 7: 통합 대시보드 📊

#### 7.1 통합 대시보드
**목표**: 모든 분석 결과를 하나의 대시보드로 통합

**구현할 CLI 명령어**:
```bash
ddoc dashboard create          # 대시보드 생성
ddoc dashboard serve          # 대시보드 서버 실행
```

**필요 작업**:
- HTML 대시보드 생성
- 실시간 업데이트
- 인터랙티브 차트

#### 7.2 통합 보고서
**목표**: 분석 결과를 종합한 보고서 생성

**구현할 CLI 명령어**:
```bash
ddoc report generate          # 보고서 생성
ddoc report export <format>   # 보고서 내보내기
```

**필요 작업**:
- HTML/PDF 보고서 생성
- 템플릿 시스템
- 자동화된 인사이트

### Phase 8: 고급 기능 🚀

#### 8.1 다중 모달리티 지원
- **텍스트**: NLP 분석 플러그인
- **비디오**: 비디오 분석 플러그인
- **시계열**: 시계열 분석 플러그인

#### 8.2 클라우드 백엔드 통합
- **S3**: AWS S3 통합
- **GCS**: Google Cloud Storage 통합
- **Azure**: Azure Blob Storage 통합

#### 8.3 분산 처리 지원
- **Dask**: 분산 데이터 처리
- **Ray**: 분산 머신러닝
- **Kubernetes**: 컨테이너 오케스트레이션

## 🔧 설정 및 구성

### 환경 변수
```bash
export DDOC_CACHE_DIR="/path/to/cache"
export DDOC_LOG_LEVEL="INFO"
export DDOC_PLUGIN_PATH="/path/to/plugins"
```

### 설정 파일 (params.yaml)
```yaml
datasets:
  - name: test_data
    path: datasets/test_data
    formats: ['.jpg', '.png']
  
experiments:
  exp_ref:
    model: yolov8n.pt
    dataset: test_data
    epochs: 10
    batch: 16

drift_analysis:
  target_vs_ref:
    reference: test_data
    current: test_yolo_sample
    output: analysis/drift_comparison
```

## 🐛 디버깅 가이드

### 로그 레벨 설정
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 플러그인 로딩 확인
```bash
ddoc plugins-info
```

### 메타데이터 확인
```bash
# 데이터셋 메타데이터
cat .ddoc_metadata/datasets.json

# 실험 메타데이터
cat .ddoc_metadata/experiments.json
```

### DVC 상태 확인
```bash
dvc status
dvc diff
dvc metrics show
```

## 📝 최근 변경사항

### 2025-11-10: Multi-Metric Embedding Drift Detection 구현

#### 주요 개선사항
- **Embedding Drift Detection 고도화**: 단일 MMD 메트릭에서 5가지 메트릭 앙상블 방식으로 개선
- **민감도 향상**: 기존에 감지하지 못했던 미세한 분포 변화 감지 가능 (0.0 → 0.0439)
- **해석 가능성 강화**: 각 메트릭별 기여도를 명시적으로 표시하여 드리프트 원인 분석 용이
- **버전별 캐시 로딩 버그 수정**: 데이터셋 이름 불일치로 인한 캐시 로딩 실패 해결

#### 1. Embedding Drift Multi-Metric Ensemble

**기존 문제점:**
- MMD(Maximum Mean Discrepancy) 하나만 사용
- 정규화로 인해 magnitude 차이 손실
- 분포 형태는 동일하지만 평균 이동이 있는 경우 감지 실패

**개선된 메트릭 조합:**

1. **Multi-scale MMD** (가중치: 0.30)
   - 5가지 gamma 값(0.1, 0.5, 1.0, 2.0, 5.0)으로 다중 스케일 분석
   - 서로 다른 커널 bandwidth에서 분포 차이 감지
   - 평균 및 표준편차로 robust한 평가

2. **Mean Shift** (가중치: 0.25)
   - 정규화 없이 원본 임베딩의 평균 벡터 간 L2 거리 계산
   - Magnitude 차이를 보존하여 실제 이동 감지
   - 차원 수의 제곱근으로 정규화하여 해석 가능성 향상

3. **Wasserstein Distance** (가중치: 0.20)
   - Earth Mover's Distance 기반
   - 1D projection을 통한 효율적 계산
   - 분포 간 최소 이동 비용 측정

4. **Population Stability Index (PSI)** (가중치: 0.15)
   - PCA로 상위 10개 주성분 추출
   - 각 주성분별 PSI 계산 후 평균
   - 금융권에서 널리 사용되는 분포 안정성 지표
   - PSI < 0.1: 안정, 0.1~0.25: 주의, ≥0.25: 불안정

5. **Cosine Distance** (가중치: 0.10)
   - 평균 벡터 간 방향성 변화 측정
   - 1 - cosine similarity
   - 의미적 방향 변화 감지

**구현된 메서드:**

```python
class DDOCVisionPlugin:
    def _calculate_psi(self, baseline, current, bins=10):
        """Population Stability Index 계산"""
        # 히스토그램 기반 분포 차이 측정
        # PSI = Σ (P_current - P_baseline) * log(P_current / P_baseline)
    
    def _calculate_embedding_drift_ensemble(self, X, Y):
        """5가지 메트릭을 조합한 앙상블 드리프트 계산"""
        # 1. Multi-scale MMD
        # 2. Mean Shift (magnitude-preserving)
        # 3. Wasserstein Distance
        # 4. PSI on PCA components
        # 5. Cosine Distance
        # → Weighted ensemble score
```

**출력 예시:**

```
🧠 Embedding Drift (Multi-Metric Analysis):
────────────────────────────────────────────────────────────────
   📊 Metric Breakdown:
      MMD (single-scale):  0.0000
      MMD (multi-scale):   0.0000 ± 0.0000
      Mean Shift:          0.0149  ← 평균 이동 감지!
      Wasserstein Dist:    0.0010
      PSI (avg):           0.0106
      PSI (max):           0.0175
      Cosine Distance:     0.0009
   
   🎯 Normalized Scores:
      mmd_multiscale      : 0.0000 (weight: 0.30)
      mean_shift          : 0.1493 (weight: 0.25)  ← 주요 기여
      wasserstein         : 0.0010 (weight: 0.20)
      psi                 : 0.0423 (weight: 0.15)
      cosine_distance     : 0.0009 (weight: 0.10)
   
   ⚖️  Ensemble Score:      0.0439

📊 Overall Drift Score: 0.0619
   Status: NORMAL
```

**JSON 저장 구조:**

```json
{
  "embedding_drift": 0.0439,
  "embedding_drift_detailed": {
    "mmd": 0.0,
    "mmd_multiscale": 0.0,
    "mmd_std": 0.0,
    "mean_shift": 0.0149,
    "wasserstein": 0.0010,
    "psi": 0.0106,
    "psi_max": 0.0175,
    "cosine_distance": 0.0009,
    "ensemble_score": 0.0439,
    "normalized_scores": {
      "mmd_multiscale": 0.0,
      "mean_shift": 0.1493,
      "wasserstein": 0.0010,
      "psi": 0.0423,
      "cosine_distance": 0.0009
    },
    "weights": {
      "mmd_multiscale": 0.3,
      "mean_shift": 0.25,
      "wasserstein": 0.2,
      "psi": 0.15,
      "cosine_distance": 0.1
    }
  }
}
```

#### 2. 버전별 캐시 로딩 버그 수정

**문제 상황:**
```bash
ddoc analyze drift mixedata --baseline v1.0 --current v1.1
# 출력: ⚠️ Repository cache missing for requested versions
# 원인: 캐시는 .ddoc_cache_store/mixedata/에 있지만
#       데이터셋 경로(datasets/test_data)의 디렉토리명(test_data)으로 검색
```

**근본 원인:**
- `commands.py`의 drift detection에서 `get_cache_repository(data_path)`를 호출
- `dataset_name` 파라미터를 전달하지 않아 경로의 디렉토리명 사용
- 실제 캐시는 데이터셋 등록 이름(`mixedata`)으로 저장됨

**수정 내용:**

```python
# ddoc/cli/commands.py (line 677)
# Before
repo = get_cache_repository(data_path)

# After
repo = get_cache_repository(data_path, dataset_name=dataset1)
```

**효과:**
- 정확한 데이터셋 이름으로 캐시 검색
- 버전별 캐시 로딩 성공률 100%
- "Repository cache missing" 경고 제거

#### 3. 성능 및 신뢰성 개선

**개선 전후 비교:**

| 항목 | 개선 전 | 개선 후 | 개선율 |
|------|---------|---------|--------|
| 임베딩 드리프트 점수 | 0.0000 | 0.0439 | +∞ |
| 전체 드리프트 점수 | 0.0377 | 0.0619 | +64% |
| 캐시 로딩 성공률 | 0% | 100% | +100% |
| 해석 가능한 메트릭 수 | 1개 | 5개 | +400% |

**실제 케이스 분석 (mixedata v1.0 → v1.1):**
- 데이터 변화: 100개 → 94개 이미지 (6개 제거, 6% 감소)
- MMD = 0.0: 분포 형태는 유지됨 (제거된 파일들이 분포 중심부에 위치)
- Mean Shift = 0.0149: 평균 벡터가 미세하게 이동함 (주요 드리프트 원인)
- PSI = 0.0106: 분포 안정성에 약간의 변화
- **결론**: "미세한 변화"로 정확히 평가됨 (NORMAL 상태)

#### 4. 변경된 파일 목록

**핵심 파일:**
- `plugins/ddoc-plugin-vision/ddoc_plugin_vision/vision_impl.py`
  - `_calculate_psi()` 메서드 추가 (PSI 계산)
  - `_calculate_embedding_drift_ensemble()` 메서드 추가 (5가지 메트릭 앙상블)
  - `drift_detect()` 메서드에서 임베딩 드리프트 계산 로직 개선
  - 상세한 메트릭 breakdown 출력 추가

- `ddoc/cli/commands.py`
  - `analyze_drift_command()` 함수에서 `get_cache_repository()` 호출 시 `dataset_name` 파라미터 추가
  - 버전별 캐시 로딩 버그 수정

#### 5. 기술적 특징

**Robustness:**
- 한 메트릭이 실패해도 다른 메트릭으로 보완
- 각 메트릭 계산 시 예외 처리로 안정성 보장
- 정규화 임계값을 경험적으로 설정하여 일관성 유지

**Interpretability:**
- 각 메트릭의 물리적/통계적 의미 명확
- 정규화된 점수와 가중치를 모두 표시
- 어떤 측면에서 드리프트가 발생했는지 명확히 파악 가능

**Extensibility:**
- 새로운 메트릭 추가 용이
- 가중치 조정을 통한 도메인별 최적화 가능
- 메트릭별 임계값 커스터마이징 가능

**Performance:**
- 샘플 수가 1000개 초과 시 자동 서브샘플링
- PCA 차원 축소로 계산 효율성 향상
- 필요한 라이브러리만 지연 로딩 (scipy.stats)

#### 6. 사용 예시

```bash
# 드리프트 분석 실행
cd sandbox/v2
ddoc analyze drift mixedata --baseline v1.0 --current v1.1

# 출력:
# 📦 Using repository baseline cache (version=v1.0)
# 📦 Using repository current cache (version=v1.1)
# 🧠 Embedding Drift (Multi-Metric Analysis):
#    Mean Shift: 0.0149 ← 주요 변화 감지
#    ⚖️ Ensemble Score: 0.0439

# 상세 메트릭 확인
cat analysis/mixedata/drift/metrics.json | python3 -m json.tool
```

#### 7. 향후 개선 계획

**통계적 유의성 검정:**
- Permutation test를 통한 p-value 계산
- 부트스트랩을 통한 신뢰구간 추정
- 다중 검정 보정 (Bonferroni, FDR)

**차원별 드리프트 분석:**
- Kolmogorov-Smirnov test로 각 임베딩 차원별 분포 비교
- 주요 드리프트 발생 차원 식별
- 차원별 기여도 시각화

**적응형 가중치:**
- 데이터셋 특성에 따른 자동 가중치 조정
- 메타러닝을 통한 최적 가중치 학습
- 도메인별 프리셋 제공

**실시간 모니터링:**
- 스트리밍 데이터에 대한 온라인 드리프트 감지
- 슬라이딩 윈도우 기반 연속 모니터링
- 알림 시스템 통합

#### 8. 참고 자료

- **MMD**: Gretton et al., "A Kernel Two-Sample Test" (2012)
- **Wasserstein Distance**: Villani, "Optimal Transport: Old and New" (2009)
- **PSI**: Siddiqi, "Credit Risk Scorecards" (2006)
- **CLIP Embeddings**: Radford et al., "Learning Transferable Visual Models" (2021)

### 2025-11-07: 데이터 무결성 보장 및 성능 최적화

#### 주요 개선사항
- **데이터셋 중복 방지**: 이름과 경로의 중복 등록 방지로 데이터 무결성 강화
- **경로 정규화**: 절대경로 기반 중복 검사 및 상대경로 저장으로 이식성 보장
- **성능 최적화**: CLI 초기 로딩 속도 대폭 개선 (지연 로딩, 캐싱, 조건부 플러그인 로딩)

#### 1. 데이터셋 중복 방지 시스템

**MetadataService 개선**
```python
class MetadataService:
    def _normalize_path(self, path: str) -> str:
        """절대경로로 정규화하여 중복 비교"""
        
    def _to_relative_path(self, path: str) -> str:
        """project_root 기준 상대경로로 저장"""
        
    def check_duplicate_name(self, name: str) -> Optional[Dict[str, Any]]:
        """데이터셋 이름 중복 체크"""
        
    def check_duplicate_path(self, path: str) -> Optional[Dict[str, Any]]:
        """데이터셋 경로 중복 체크 (정규화 후 비교)"""
```

**핵심 기능:**
- 이름 중복: 동일한 데이터셋 이름으로 다른 경로 등록 방지
- 경로 중복: 다른 이름으로 동일한 경로 등록 방지
- 정규화: 상대경로(`./datasets/test`), 절대경로(`/Users/.../datasets/test`) 모두 동일하게 인식
- 심볼릭 링크: `Path.resolve()`로 실제 경로 해결 후 비교
- 이식성: 저장은 상대경로, 비교는 절대경로로 수행

**에러 메시지 개선**
```bash
# 이름 중복 시
❌ Error: Dataset name 'test_data' is already registered.
  Existing path: sandbox/v2/datasets/test_data
  Registered at: 2025-11-07T15:20:22.781289
  
  💡 To modify this dataset, run: ddoc dataset add test_data
  💡 To use a different name, run: ddoc dataset add <new_name> ./path

# 경로 중복 시
❌ Error: This path is already registered as 'test_data'.
  Path: sandbox/v2/datasets/test_data
  Registered at: 2025-11-07T15:20:22.781289
  
  💡 To use the existing dataset, run: ddoc dataset add test_data
  💡 To register a different path, specify a different directory
```

#### 2. 성능 최적화

**2.1 메타데이터 캐싱 (mtime 기반)**

메타데이터 파일을 메모리에 캐싱하여 반복적인 파일 I/O 제거:

```python
class MetadataService:
    def __init__(self):
        # 캐시 변수
        self._dataset_mappings_cache = None
        self._dataset_mappings_mtime = None
        self._lineage_cache = None
        self._lineage_mtime = None
    
    def _load_dataset_mappings(self) -> Dict[str, Any]:
        """mtime 기반 캐싱"""
        current_mtime = self.dataset_mapping_file.stat().st_mtime
        
        # 캐시 히트
        if (self._dataset_mappings_cache is not None and 
            self._dataset_mappings_mtime == current_mtime):
            return self._dataset_mappings_cache
        
        # 캐시 미스 - 파일 로드 및 캐시 업데이트
        mappings = json.load(f)
        self._dataset_mappings_cache = mappings
        self._dataset_mappings_mtime = current_mtime
        return mappings
```

**효과:**
- 동일 명령 내 반복 호출 시 파일 I/O 제거
- mtime 변경 시 자동 캐시 무효화로 일관성 유지

**2.2 지연 로딩 (Lazy Loading)**

필요한 시점에만 모듈과 서비스 로드:

```python
# commands.py - 모듈 레벨 임포트 제거
# Before
from ddoc.core.plugins import get_plugin_manager
from ddoc.ops.core_ops import CoreOpsPlugin

# After - 함수 내부에서 임포트
def get_pmgr():
    global _pmgr
    if _pmgr is None:
        from ddoc.core.plugins import get_plugin_manager
        _pmgr = get_plugin_manager()
    return _pmgr
```

**효과:**
- 모듈 로드 시간 감소
- 사용하지 않는 기능의 초기화 비용 제거

**2.3 조건부 플러그인 로딩**

간단한 명령어는 플러그인 없이 실행:

```python
# main.py
def init_app(debug: bool = False, load_plugins: bool = True):
    load_dotenv()
    logging.basicConfig(...)
    
    # 필요한 경우에만 플러그인 로드
    if load_plugins:
        get_plugin_manager()

@app.callback(invoke_without_command=True)
def _bootstrap(ctx: typer.Context, ...):
    # 서브커맨드가 있을 때만 플러그인 로드
    load_plugins = ctx.invoked_subcommand is not None
    init_app(debug=debug, load_plugins=load_plugins)
```

**효과:**
- `--version`, `--help` 등 간단한 명령어 실행 시간 단축
- 플러그인 로딩 비용 제거

**2.4 Lineage 지연 로딩**

Lineage 그래프를 사용하는 시점에만 로드:

```python
class MetadataService:
    def __init__(self):
        self._lineage_loaded = False  # 로드 여부 추적
        # 초기화 시 lineage 로드하지 않음
    
    def add_dataset(self, ...):
        # 사용 시점에 로드
        if not self._lineage_loaded:
            self._load_lineage()
        # ... 실제 로직
```

**효과:**
- MetadataService 초기화 시간 감소
- Lineage 기능을 사용하지 않는 명령어 성능 향상

#### 3. 성능 측정 결과

**Before (최적화 전):**
```bash
time ddoc --version
# → 약 0.7~1.0초

time ddoc dataset list
# → 약 5~7초
```

**After (최적화 후):**
```bash
time ddoc --version
# → 약 0.16초 (78% 개선)

time ddoc dataset list (첫 실행)
# → 약 5초

time ddoc dataset list (두 번째 실행, 캐시 사용)
# → 약 3초 (40% 개선)
```

#### 4. 변경된 파일 목록

**핵심 파일:**
- `ddoc/core/metadata_service.py`
  - 중복 검사 메서드 추가: `check_duplicate_name()`, `check_duplicate_path()`
  - 경로 정규화: `_normalize_path()`, `_to_relative_path()`
  - mtime 기반 캐싱 구현
  - Lineage 지연 로딩

- `ddoc/core/dataset_service.py`
  - `stage_dataset()`에서 중복 검사 호출
  - 사용자 친화적 에러 메시지

- `ddoc/cli/commands.py`
  - 모듈 레벨 임포트를 함수 내부로 이동
  - 지연 로딩 패턴 적용

- `ddoc/cli/main.py`
  - 조건부 플러그인 로딩 구현
  - `init_app(load_plugins=...)` 매개변수 추가

#### 5. 사용 예시

**중복 방지 테스트:**
```bash
# 데이터셋 등록
ddoc dataset add test_data datasets/test_data
# ✅ 성공

# 같은 이름으로 다른 경로 등록 시도
ddoc dataset add test_data datasets/other_data
# ❌ Error: Dataset name 'test_data' is already registered.

# 다른 이름으로 같은 경로 등록 시도
ddoc dataset add test_data_2 datasets/test_data
# ❌ Error: This path is already registered as 'test_data'.

# 절대경로로 등록 시도 (정규화 테스트)
ddoc dataset add test_data_3 /Users/bhc/dev/drift_v1/ddoc/datasets/test_data
# ❌ Error: This path is already registered as 'test_data'.
```

**성능 개선 확인:**
```bash
# 빠른 명령어 (플러그인 로딩 없음)
time ddoc --version
# → 약 0.16초

time ddoc --help
# → 약 0.2초

# 캐싱 효과 확인
time ddoc dataset list  # 첫 실행
time ddoc dataset list  # 두 번째 실행 (더 빠름)
```

#### 6. 기술적 특징

**데이터 무결성:**
- 절대경로 기반 중복 검사로 다양한 경로 표현 처리
- 상대경로 저장으로 프로젝트 이식성 보장
- ValueError 예외로 명확한 에러 처리

**성능 최적화:**
- mtime 기반 캐싱으로 파일 I/O 최소화
- 지연 로딩으로 불필요한 초기화 제거
- 조건부 플러그인 로딩으로 간단한 명령어 속도 향상
- 메모리 기반 캐시로 빠른 액세스

**코드 품질:**
- 린터 에러 없음
- 타입 힌트 유지
- 문서화된 메서드
- 일관된 에러 메시지

#### 7. 향후 개선 계획

**추가 최적화:**
- 플러그인 lazy 임포트
- 더 세밀한 서비스 지연 로딩
- 캐시 크기 제한 및 LRU 정책

**기능 확장:**
- `--force` 옵션으로 중복 등록 허용
- 데이터셋 이름 변경 기능
- 경로 업데이트 기능

### 2025-10-30: 캐시 무결성/체크아웃/증분분석 개선 및 버전 업그레이드

#### 주요 개선사항
- Vision EDA의 속성/임베딩 분석에 "증분 처리"(incremental) 도입: 추가/수정 파일만 재분석, 삭제 파일은 캐시에서 제거
- 캐시 무결성 검증 강화: 파일 목록 비교 + (속성 분석) 파일 크기 기반 변경 감지, 임베딩은 size/mtime 메타를 활용한 변경 감지
- 캐시 로딩 정책 개선: 부분 업데이트를 위해 검증 없이 직접 로딩 후 변경 집합(new/modified/removed/skipped) 계산
- DVC 체크아웃 개선: `--force` 옵션 지원, 체크아웃 전 캐시 디렉토리 임시 백업 및 체크아웃 후 복원 로직 추가
- .dvcignore 자동화: ddoc 실행 디렉토리(self.project_root)에 `.dvcignore` 생성/내용 추가(기존 파일이면 append)
- Hook 시그니처 확장: `eda_run(..., version: str | None)`로 버전 전달 경로 정식 지원
- CLI 개선: `analyze eda`가 현재 버전을 hook에 전달, 캐시 무효화는 설치된 vision 플러그인 패키지에서만 임포트
- 로깅 강화: 변경 집합 요약(new/modified/removed/skipped)과 캐시 사용/갱신 내역 출력
- 버전 업: `ddoc 1.3.5`, `ddoc-plugin-vision 0.2.0`

#### 변경된 파일 (핵심)
- `plugins/ddoc-plugin-vision/ddoc_plugin_vision/vision_impl.py`
  - 속성/임베딩 단계 모두 증분 처리(new/modified/removed/skipped) 적용
  - 임베딩 캐시에 `file_size`, `file_mtime` 저장 및 비교
  - 캐시를 검증 없이 직접 로드하여 부분 업데이트 수행, 변경 요약 로그 출력
- `plugins/ddoc-plugin-vision/ddoc_plugin_vision/cache_utils/cache_manager.py`
  - `_validate_cache_integrity`: 파일 목록 동일 시에도 (속성 분석) 파일 크기 차이면 캐시 무효화
  - 저장/무효화/정리 로깅 보강
- `ddoc/core/dataset_service.py`
  - DVC checkout: `--force` 지원, 캐시 디렉토리 백업/복원, 체크아웃 후 캐시 상태 로깅
  - `.dvcignore`를 실행 디렉토리에 생성/내용 추가(존재 시 append)
- `ddoc/cli/commands.py`
  - `analyze eda`: 현재 버전 전달, 캐시 무효화는 설치된 `ddoc_plugin_vision`만 허용(로컬 폴백 제거)
- `ddoc/plugins/hookspecs.py`
  - `eda_run` 시그니처에 `version: str | None` 추가
- `plugins/ddoc-plugin-vision/pyproject.toml`: `version = 0.2.0`
- `pyproject.toml`(root): `version = 1.3.5`

#### 사용 시 주의
- Vision 플러그인은 설치된 패키지에서만 임포트합니다. 개발 중 변경사항을 즉시 반영하려면 editable 설치를 권장합니다:
  - `pip uninstall -y ddoc-plugin-vision && pip install -e plugins/ddoc-plugin-vision`
- 증분 분석은 다음 기준으로 동작합니다:
  - 속성 분석: 파일 목록 + 크기(MB ±0.01) 차이로 수정 감지
  - 임베딩 분석: 파일 목록 + `st_size`/`st_mtime` 차이로 수정 감지
  - 변경 없음(캐시 동일) 파일은 "skipped(cached)"로 보고

#### 예시 로그 (임베딩 단계)
```
Changed summary → new: 3, modified: 2, removed: 1, skipped(cached): 71
   new: a.jpg, b.jpg, c.jpg
   modified: d.jpg, e.jpg
   removed: z.jpg
💾 Saving embedding analysis to cache for version: v1.1
💾 Updated embedding cache: 76 files
```

### 2025-10-22: 문서 구조 통합 및 정리

#### 변경사항
- **문서 통합**: 7개의 마크다운 문서를 3개의 핵심 문서로 통합
- **중복 제거**: 중복된 내용 완전 제거
- **구조 개선**: 명확한 역할 분담으로 사용자 경험 향상

#### 삭제된 문서들
- ❌ `QUICKSTART.md` → `README.md`에 통합
- ❌ `README_TESTING.md` → `TESTING.md`에 통합  
- ❌ `TEST_PROCEDURE.md` → `TESTING.md`에 통합
- ❌ `TEST_RESULTS.md` → `TESTING.md`에 통합
- ❌ `TROUBLESHOOTING.md` → `TESTING.md`에 통합
- ❌ `INTEGRATION_REPORT.md` → `DEVELOPMENT.md`에 통합
- ❌ `NEXT_PHASE_PLAN.md` → `DEVELOPMENT.md`에 통합

#### 최종 문서 구조
```
ddoc/
├── README.md          # 메인 문서 (프로젝트 소개 + 빠른 시작)
├── TESTING.md         # 테스트 가이드 (절차 + 결과 + 문제해결)
└── DEVELOPMENT.md     # 개발 문서 (구현 + 다음단계)
```

#### 개선된 점
1. **간결성**: 7개 → 3개 문서로 축소
2. **명확성**: 각 문서의 역할이 명확히 구분
3. **접근성**: 찾기 쉬운 구조로 재편성
4. **일관성**: 통일된 스타일과 구조

### 2025-10-22: 스크립트 분리 및 개선

#### 변경사항
- **스크립트 분리**: `ddocv2_test_dataprocess.sh`와 `ddocv2_test_modelprocess.sh`로 분리
- **디자인 패턴 통일**: 두 스크립트의 로그 출력 및 구조 일치
- **인자 지원**: 두 개의 데이터셋을 인자로 받도록 처리

#### 새로운 스크립트 구조
```bash
# 데이터 처리 (EDA + 드리프트 분석)
./ddocv2_test_dataprocess.sh [dataset1] [dataset2]

# 모델 처리 (학습 + 실험 관리)  
./ddocv2_test_modelprocess.sh [dataset1] [dataset2]
```

### 2025-10-22: YOLO 학습 에러 수정

#### 해결된 문제
- **AttributeError**: `'list' object has no attribute 'get'` 에러 수정
- **플러그인 반환값 처리**: 리스트 반환 시 딕셔너리로 변환하는 로직 추가
- **YOLO 데이터셋 구조**: 올바른 YOLO 형식 데이터셋 사용 확인

#### 수정된 코드
```python
# ddoc/cli/commands.py
# Handle case where plugin manager returns a list of results
if isinstance(res, list):
    # Find the YOLO plugin result (non-error result)
    res = next((r for r in res if r and r.get('status') != 'error'), None)
    if not res:
        res = {"status": "error", "message": "All plugins failed"}
```

### 2025-10-22: Phase 5 완료 - 실험 추적 및 계보 관리 시스템

#### 5.1 실험 추적 시스템 강화
- **새로운 CLI 명령어**: `ddoc exp list`, `ddoc exp show`, `ddoc exp compare` 구현
- **실험 메타데이터 관리**: `ExperimentTracker` 클래스로 실험 정보 추적
- **실험 비교 기능**: 여러 실험 간 성능 및 파라미터 비교 지원

#### 5.2 LineageTracker 구현
- **DAG 기반 계보 추적**: NetworkX를 활용한 방향성 비순환 그래프 구현
- **노드 타입 지원**: dataset, analysis, experiment, drift_analysis 노드 타입
- **관계 추적**: 데이터셋-분석-실험 간 의존성 관계 자동 추적

#### 5.3 계보 시각화 CLI
- **새로운 lineage 명령어**: `ddoc lineage show`, `ddoc lineage graph`, `ddoc lineage impact`
- **의존성 분석**: `ddoc lineage dependencies`, `ddoc lineage dependents`
- **Graphviz 지원**: DOT 형식으로 그래프 시각화 지원
- **영향도 분석**: 노드 변경 시 영향받는 다른 노드들 분석

#### 구현된 주요 기능
```python
# LineageTracker 클래스
class LineageTracker:
    def add_dataset(self, dataset_id, name, metadata)
    def add_analysis(self, analysis_id, name, dataset_id, metadata)
    def add_experiment(self, exp_id, name, dataset_id, metadata)
    def add_drift_analysis(self, drift_id, name, ref_dataset_id, cur_dataset_id, metadata)
    def get_lineage(self, node_id, depth=2)
    def get_impact_analysis(self, node_id)
    def export_graph(self, format='json')
```

#### CLI 명령어 예시
```bash
# 실험 관리
ddoc exp list
ddoc exp show exp_001
ddoc exp compare exp_001 exp_002

# 계보 관리
ddoc lineage show test_yolo
ddoc lineage graph --output lineage.dot --format dot
ddoc lineage impact exp_001
ddoc lineage dependencies test_yolo
ddoc lineage dependents test_yolo
```

### 2025-10-22: 프로젝트 병합 및 데이터셋 정리

#### Git 병합 완료
- **브랜치 통합**: `bhc` 브랜치와 `origin/main` 브랜치 성공적 병합
- **충돌 해결**: `ddoc/cli/commands.py` 파일 충돌 해결 및 기능 통합
- **새로운 플러그인**: `ddoc-plugin-vis` 플러그인 통합

#### 데이터셋 파일 정리
- **Git에서 제거**: 수천 개의 데이터셋 파일들을 Git 추적에서 제거
- **DVC 전용 관리**: 데이터셋 파일들은 이제 DVC로만 관리
- **.gitignore 강화**: 이미지, 라벨, 모델 파일 등 ML 관련 파일들 ignore 규칙 추가

#### 개선된 .gitignore
```gitignore
# Dataset files (tracked by DVC, not Git)
**/datasets/
datasets/
**/*.jpg
**/*.jpeg
**/*.png
**/*.txt
**/*.yaml
**/*.yml
**/*.pt
**/*.pth
**/*.pkl
**/*.npy
**/*.npz
```

### 2025-10-27: Git 독립적 데이터셋 버전 관리 시스템 구축

#### 주요 개선사항
- **Git 의존성 완전 제거**: 데이터셋 버전 관리가 Git 없이도 독립적으로 동작
- **DVC 해시 기반 변경 감지**: `.dvc` 파일의 MD5 해시를 직접 파싱하여 데이터 변경사항 추적
- **자동 버전 증가**: 데이터셋 재등록 시 자동으로 다음 버전 번호 생성 (v1.0 → v1.1 → v1.2...)
- **정책 기반 버전 제어**: Strict/Warning/Auto 모드로 유연한 버전 관리 정책 지원

#### 새로 추가된 서비스

**VersionService (`ddoc/core/version_service.py`)**
```python
class VersionService:
    """Git-free dataset version management using DVC hash tracking"""
    
    def get_dvc_hash(self, dataset_path: str) -> Optional[str]
    def create_dataset_version(self, name: str, version: str, message: str) -> Dict
    def get_dataset_version_history(self, name: str) -> List[Dict]
    def get_dataset_status(self, name: str) -> Dict  # clean/modified/unversioned
    def check_version_state(self, name: str) -> bool  # 정책 기반 체크
    def generate_next_version(self, name: str) -> str  # 자동 버전 증가
    def create_experiment_version(self, dataset_name: str, dataset_version: str, exp_name: str) -> str
    def list_dataset_versions(self, name: str) -> List[Dict]
    def set_dataset_version_alias(self, name: str, version: str, alias: Optional[str]) -> Dict
    def get_dataset_version_by_alias(self, name: str) -> Optional[str]
```

**핵심 기능:**
- DVC 파일에서 MD5 해시 추출 및 비교
- `dataset_versions.json`, `experiment_versions.json` 파일 관리
- 버전 상태 체크 (clean/modified/unversioned)
- 정책 기반 버전 제어 (strict/warning/auto)

#### 업데이트된 서비스

**DatasetService 개선**
- Git 의존성 제거: `create_version()`, `get_version_history()`, `checkout_version()` 메서드 개선
- 자동 버전 생성: `register_dataset()` 시 기존 버전 확인 후 자동 증가
- VersionService 통합: 버전 관리 로직을 VersionService로 위임

**MetadataService 개선**
- 버전된 노드 ID 지원: `{dataset_name}@{version}` 형식으로 노드 식별
- 구식 lineage 시스템 제거: `link_analysis_to_dataset()`, `link_experiment_to_data()` 제거
- NetworkX 그래프 기반 통합: 모든 lineage 작업이 그래프 기반으로 통일

#### CLI 명령어 개선

**새로운 명령어**
```bash
ddoc dataset status <name>  # 데이터셋 버전 상태 확인
```

**개선된 명령어**
- `ddoc analyze eda`: 분석 시작 전 자동 버전 상태 체크
- `ddoc exp run`: 실험 시작 전 자동 버전 상태 체크
- `ddoc dataset version create`: Git 없이 독립적으로 버전 생성
- `ddoc dataset version list`: 버전 및 별칭 목록 조회
- `ddoc dataset version rename`: 특정 버전에 사용자 정의 별칭 부여/삭제
- `ddoc dataset timeline`: 버전·분석·실험 이벤트를 시간순으로 조회

#### 설정 시스템

**params.yaml 통합**
```yaml
version_control:
  policy: strict  # strict/warning/auto
  auto_version_prefix: "auto_"
  version_format: "v{major}.{minor}"
```

#### 데이터 저장 구조

**버전 메타데이터 (`dataset_versions.json`)**
```json
{
  "test_ref": {
    "versions": {
      "v1.0": {
        "hash": "abc123...",
        "timestamp": "2025-10-27T...",
        "message": "Initial version",
        "metadata": {}
      },
      "v1.1": {
        "hash": "def456...",
        "timestamp": "2025-10-27T...",
        "message": "Re-registered dataset (was v1.0)",
        "metadata": {}
      }
    },
    "current_version": "v1.1",
    "latest_hash": "def456..."
  }
}
```

**분석 캐시 저장소 (`.ddoc_cache_store`)**
- 구조: `.ddoc_cache_store/<dataset_name>/<version>/{attribute_analysis,embedding_analysis}.cache`
- `cache_utils.cache_repository.CacheRepository`를 통해 버전별 캐시를 관리
- `eda_run` 실행 시 중앙 저장소에서 해당 버전 캐시를 로컬 `cache/`로 복원하여 증분 분석 및 Warm-start를 유지
- `dataset_service.checkout_version()`은 checkout 전후로 중앙 저장소와 동기화하여 캐시 손실을 방지
- `ddoc analyze drift`는 저장소에 있는 baseline/current 캐시를 사용해 버전 간 드리프트를 계산
- YOLO 플러그인의 `ultralytics` 의존성은 Python 버전에 따라 달라지며, 3.10 미만에서는 `ultralytics<8`이 설치됩니다.

**실험 버전 메타데이터 (`experiment_versions.json`)**
```json
{
  "test_ref@v1.0": {
    "experiments": {
      "exp_1": {
        "exp_name": "my_experiment",
        "timestamp": "2025-10-27T...",
        "metadata": {}
      }
    },
    "counter": 1
  }
}
```

#### Lineage 시스템 통합

**버전별 계보 추적**
- 데이터셋 노드: `test_ref@v1.0`, `test_ref@v1.1`
- 분석 노드: `test_ref@v1.0_analysis_20251027_153000`
- 실험 노드: `my_experiment@exp_1`

**관계 추적**
- `test_ref@v1.0` --[generates]--> `test_ref@v1.0_analysis_...`
- `test_ref@v1.0` --[uses]--> `my_experiment@exp_1`

#### 사용 예시

```bash
# 데이터셋 등록 (자동 v1.0 생성)
ddoc dataset add test_data ./data
# → test_data@v1.0 생성

# 데이터 수정 후 재등록 (자동 v1.1 생성)
ddoc dataset add test_data ./modified_data
# → test_data@v1.1 생성 (자동 증가!)

# 버전 상태 확인
ddoc dataset status test_data
# → clean/modified/unversioned 상태 표시

# 분석 실행 (버전 체크 후 진행)
ddoc analyze eda test_data
# → 버전 상태 체크 → 분석 실행 → lineage 기록

# 실험 실행 (버전 체크 후 진행)
ddoc exp run my_exp test_data yolo
# → 버전 상태 체크 → 실험 실행 → lineage 기록

# 계보 조회
ddoc lineage show test_data@v1.1
# → 해당 버전의 모든 분석/실험 표시
```

#### 기술적 특징

**Git 독립성**
- DVC 파일 직접 파싱으로 Git 없이도 동작
- `.dvc` 파일의 `md5` 필드에서 해시 추출
- Git 태그 대신 JSON 파일로 버전 정보 관리

**성능 최적화**
- 메모리 기반 NetworkX 그래프로 빠른 lineage 조회
- 필요한 시점에만 해시 계산 (버전 명령 실행 시)
- 지연 초기화로 서비스 인스턴스 관리

**에러 처리**
- DVC 파일 없을 때 안전한 처리
- 버전 정책 위반 시 명확한 에러 메시지
- 자동 복구 기능 (auto 모드)

### 2025-10-28: Lineage Overview 명령어 추가

#### 주요 개선사항
- **전체 계보 시각화**: 모든 데이터셋과 관계를 한눈에 볼 수 있는 overview 명령어 추가
- **Rich 라이브러리 활용**: 컬러풀하고 가독성 높은 ASCII 트리 구조 출력
- **노드 타입별 아이콘**: 데이터셋, 분석, 실험, 드리프트 분석을 시각적으로 구분
- **계층적 구조**: 데이터셋을 루트로 하는 트리 형태의 관계 표현

#### 새로 추가된 기능

**MetadataService.get_lineage_overview()**
```python
def get_lineage_overview(self) -> Dict[str, Any]:
    """전체 계보 개요 정보 조회 (트리 구조용)"""
    # 노드 타입별 그룹화
    # 데이터셋별 하위 노드 매핑
    # 관계 정보 수집 및 통계
```

**핵심 기능:**
- 노드 타입별 분류 (dataset, analysis, experiment, drift_analysis)
- 데이터셋별 하위 노드 매핑 (analyses, experiments, drift_analyses)
- 관계 타입별 통계 수집
- 독립 노드 식별 (관계가 없는 노드들)

#### 새로운 CLI 명령어

**`ddoc lineage overview`**
```bash
ddoc lineage overview
```

**출력 구성:**
1. **전체 통계**: 총 노드 수, 관계 수, 타입별 노드 수
2. **트리 구조**: 데이터셋을 루트로 하는 계층적 관계 시각화
3. **관계 타입별 통계**: generates, uses, baseline, target 등
4. **독립 노드**: 관계가 없는 노드들 표시

#### 시각화 특징

**Rich 라이브러리 활용**
- 컬러풀한 출력 (녹색 노드, 회색 ID)
- 굵은 글씨로 섹션 구분
- 이모지 아이콘으로 노드 타입 구분

**ASCII 트리 구조**
- `├──`, `└──` 기호로 트리 표현
- 관계별로 적절한 들여쓰기
- 데이터셋을 중심으로 한 계층적 구조

**노드 타입별 아이콘**
- 📦 **Dataset**: 데이터셋
- 📈 **Analysis**: 분석 결과  
- 🧪 **Experiment**: 실험
- 📊 **Drift Analysis**: 드리프트 분석

#### 사용 예시

```bash
# 전체 계보 개요 조회
ddoc lineage overview

# 예상 출력:
📊 Dataset Lineage Overview

Summary:
  Total Nodes: 4
  Total Relationships: 3
  Datasets: 1
  Analyses: 1
  Experiments: 1
  Drift Analyses: 1

📦 Dataset Lineage Tree:
└── 📦 test_ref (test_ref@v1.0)
    ├── 📈 EDA Analysis (test_ref@v1.0_analysis_20251027_153000)
    ├── 🧪 YOLO Training (my_experiment@exp_1)
    └── 📊 Drift Detection (drift_20251027_154000)

🔗 Relationship Types:
  generates: 1
  uses: 1
  baseline: 1
```

#### 기술적 특징

**데이터 구조**
- 노드 타입별 그룹화로 효율적인 분류
- 데이터셋별 하위 노드 매핑으로 관계 추적
- 관계 타입별 통계로 전체 구조 파악

**성능 최적화**
- 메모리 기반 NetworkX 그래프 활용
- 필요한 정보만 선별적으로 수집
- 지연 초기화로 서비스 인스턴스 관리

**확장성**
- 새로운 노드 타입 추가 용이
- 관계 타입 확장 가능
- 시각화 스타일 커스터마이징 가능

## 🖥️ Shell Prompt Integration

### 개요

ddoc은 shell 프롬프트에 현재 활성화된 데이터셋과 버전 정보를 자동으로 표시하는 기능을 제공합니다. 이 기능은 `virtualenv`나 `git branch`와 유사한 방식으로 동작합니다.

### 주요 기능

#### 1. 자동 데이터셋 감지

`ddoc dataset checkout` 또는 `ddoc dataset add` 명령 실행 시, 현재 작업 디렉토리에 `.ddoc_current` 파일이 자동으로 생성됩니다:

```json
{
  "dataset": "yolotest",
  "version": "v1.0",
  "timestamp": "2025-10-31T15:40:50.904585",
  "project_root": "/Users/bhc/dev/drift_v1/ddoc/sandbox/v2"
}
```

#### 2. Shell Hook 기반 자동 감지

- **zsh**: `chpwd` hook을 사용하여 디렉토리 변경 시 자동으로 `.ddoc_current` 파일을 검색
- **bash**: `PROMPT_COMMAND`를 사용하여 프롬프트 표시 전마다 자동 감지
- 현재 디렉토리부터 홈 디렉토리까지 상위 경로를 순회하며 `.ddoc_current` 파일 검색

#### 3. 프롬프트 통합

프롬프트에 다음과 같이 표시됩니다:

```
[ddoc:yolotest@v1.0] (venv) ┌─(~/dev/drift_v1/ddoc/sandbox/v2)─┐
└─(15:40:15 on main ✹)──>
```

**특징:**
- 기존 venv 프롬프트(`(venv)`) 보존
- 기존 conda 프롬프트 보존 (단, `base` 환경은 표시하지 않음)
- p10k, oh-my-zsh 등 다른 프롬프트 시스템과 충돌 없이 동작
- `precmd` hook에서 다른 프롬프트 생성 함수들이 먼저 실행되도록 순서 보장

### 사용 방법

#### 1. 초기 설정 (최초 1회)

```bash
ddoc init
```

이 명령은 다음 작업을 수행합니다:
- DVC 초기화 (이미 초기화되어 있으면 스킵)
- `.dvcignore` 파일 생성
- `~/.zshrc` 또는 `~/.bashrc`에 shell prompt integration 코드 추가

**중복 체크:**
- 이미 ddoc 코드가 설정되어 있으면 추가하지 않음
- 기존 설정을 덮어쓰지 않음

#### 2. 자동 작동

설정 후에는 자동으로 작동합니다:

```bash
# 데이터셋 버전 체크아웃
ddoc dataset checkout yolotest v1.0
# → .ddoc_current 파일 자동 생성
# → 다음 프롬프트에서 자동 표시

# 데이터셋 추가
ddoc dataset add newdataset ./data
# → .ddoc_current 파일 자동 생성
# → 다음 프롬프트에서 자동 표시
```

#### 3. 수동 재로드

`.zshrc` 또는 `.bashrc`를 수정한 경우:

```bash
source ~/.zshrc  # 또는 source ~/.bashrc
```

### 구현 세부사항

#### Shell Script 구조 (zsh)

```bash
# .ddoc_current 파일 자동 감지 함수
_ddoc_chpwd() {
  local dir="$(pwd)"
  local ddoc_file=""
  # 현재 디렉토리부터 홈 디렉토리까지 검색
  while [ "$dir" != "$HOME" ] && [ "$dir" != "/" ]; do
    if [ -f "$dir/.ddoc_current" ]; then
      ddoc_file="$dir/.ddoc_current"
      break
    fi
    dir="$(dirname "$dir")"
  done
  # 환경 변수 설정
  if [ -n "$ddoc_file" ] && [ -f "$ddoc_file" ]; then
    export DDOC_DATASET=$(python3 -c "import json, sys; print(json.load(open(sys.argv[1])).get(\"dataset\", \"\"))" "$ddoc_file" 2>/dev/null)
    export DDOC_VERSION=$(python3 -c "import json, sys; print(json.load(open(sys.argv[1])).get(\"version\", \"\"))" "$ddoc_file" 2>/dev/null)
  else
    unset DDOC_DATASET
    unset DDOC_VERSION
  fi
}

# 프롬프트 업데이트 함수
_ddoc_precmd() {
  # .ddoc_current 파일 재로드
  _ddoc_chpwd
  
  # 현재 PROMPT 읽기 (다른 hook들이 이미 venv/conda 정보 추가함)
  local current_prompt="$PROMPT"
  
  # 기존 ddoc prefix 제거 (중복 방지)
  current_prompt=$(echo "$current_prompt" | sed -E "s/^\[ddoc:[^]]*\] //")
  
  # ddoc prefix 추가
  if [ -n "$DDOC_DATASET" ] && [ -n "$DDOC_VERSION" ]; then
    PROMPT="[ddoc:$DDOC_DATASET@$DDOC_VERSION] $current_prompt"
  else
    PROMPT="$current_prompt"
  fi
}

# Hook 등록
autoload -Uz add-zsh-hook
add-zsh-hook chpwd _ddoc_chpwd
add-zsh-hook precmd _ddoc_precmd
```

#### Python 코드 (ddoc/cli/commands.py)

**`init` 명령:**
- Shell 자동 감지 (zsh 또는 bash)
- 기존 설정 중복 체크
- `.zshrc` 또는 `.bashrc`에 코드 자동 추가

**`dataset checkout` 및 `dataset add` 명령:**
- 성공 시 자동으로 `.ddoc_current` 파일 생성
- `DatasetService._save_current_checkout_file()` 메서드 사용

### 주의사항

#### 1. venv/conda 프롬프트 보존

- `_ddoc_precmd`는 `precmd` hook의 마지막에 실행되도록 설계됨
- 다른 프롬프트 생성 함수들(p10k, oh-my-zsh 등)이 먼저 실행되어 venv/conda 정보를 포함한 PROMPT 생성
- `_ddoc_precmd`는 기존 PROMPT를 읽어서 ddoc 정보만 앞에 추가

#### 2. conda base 환경 처리

- conda `base` 환경은 프롬프트에 표시하지 않음
- 다른 conda 환경(예: `datadrift`)은 표시됨

#### 3. 중복 방지

- `_ddoc_precmd` 실행 시 기존 `[ddoc:...]` prefix를 제거하여 중복 방지
- `sed` 명령을 사용하여 정규식 패턴 매칭

### 문제 해결

#### 프롬프트에 표시되지 않는 경우

1. `.zshrc` 또는 `.bashrc`를 다시 source:
   ```bash
   source ~/.zshrc
   ```

2. `.ddoc_current` 파일 확인:
   ```bash
   cat .ddoc_current
   ```

3. 환경 변수 확인:
   ```bash
   echo "DDOC_DATASET: $DDOC_DATASET"
   echo "DDOC_VERSION: $DDOC_VERSION"
   ```

4. 함수 수동 실행 테스트:
   ```bash
   _ddoc_chpwd
   _ddoc_precmd
   ```

#### venv/conda 프롬프트가 사라지는 경우

- `ddoc init`을 다시 실행하지 말고, `.zshrc`의 기존 설정을 확인
- `_ddoc_precmd` 함수가 올바르게 현재 PROMPT를 읽어서 사용하는지 확인

### 기술 스택

- **Shell Scripting**: zsh hooks (`chpwd`, `precmd`), bash `PROMPT_COMMAND`
- **Python**: JSON 파일 읽기/쓰기
- **sed**: 정규식 패턴 매칭 및 문자열 치환

### 2025-11-13: MLflow 통합 및 실험 추적 시스템 개선 (v1.3.6)

#### 주요 개선사항
- **MLflow 기반 실험 추적**: Git 없이 실험 관리 가능한 MLflow 통합
- **Ultralytics 네이티브 지원**: YOLO 학습 시 자동 MLflow 로깅
- **데이터 버전 통합**: 모든 실험이 데이터셋 버전에 자동 연결
- **멀티 트랙 지원**: DVC(Git 기반)와 MLflow(Git 불필요) 동시 지원
- **실험 ID 자동 생성**: 타임스탬프 기반 고유 ID 자동 할당

#### 1. MLflowExperimentService 구현

**새로운 핵심 서비스 (`ddoc/core/mlflow_experiment_service.py`)**

```python
class MLflowExperimentService:
    """
    MLflow 기반 실험 서비스 (Ultralytics 네이티브 통합)
    - Git 없이 작동
    - ddoc 데이터 버전과 자동 연동
    - 계보 그래프에 실험 추가
    """
    
    def run_experiment(self, dataset_name, dataset_version, model, params, plugin):
        """MLflow를 사용한 실험 실행"""
        # 1. MLflow experiment 설정
        # 2. ddoc 메타데이터를 MLflow 태그로 설정
        # 3. YOLO 학습 실행 (Ultralytics가 자동으로 MLflow에 로깅)
        # 4. ddoc 메타데이터 저장
        # 5. 계보 그래프에 연결
    
    def get_experiments_by_dataset(self, dataset_name, dataset_version):
        """특정 데이터셋의 모든 실험 조회"""
    
    def compare_experiments(self, exp_ids):
        """여러 실험 비교"""
    
    def get_best_experiment_for_dataset(self, dataset_name, dataset_version, metric):
        """데이터셋 버전의 최고 성능 실험 찾기"""
```

**핵심 기능:**
- **MLflow 설정**: tracking URI 자동 구성, experiment 초기화
- **Ultralytics 통합 활성화**: `settings.update({"mlflow": True})`
- **자동 태깅**: 데이터셋 이름, 버전, 실험 ID를 MLflow 태그로 저장
- **계보 연결**: MetadataService를 통해 NetworkX 그래프에 노드 추가

#### 2. Ultralytics MLflow 네이티브 통합

**자동 로깅 항목 (Ultralytics가 자동으로 MLflow에 기록)**

```python
# 파라미터
- epochs, batch, imgsz, device, model
- optimizer, lr0, momentum
- augmentation settings

# 메트릭 (에포크별)
- metrics/mAP50(B) - mAP@0.5
- metrics/mAP50-95(B) - mAP@0.5:0.95
- metrics/precision(B) - Precision
- metrics/recall(B) - Recall
- train/box_loss, train/cls_loss, train/dfl_loss
- val/box_loss, val/cls_loss, val/dfl_loss
- fitness - 전체 성능 점수

# 아티팩트
- weights/best.pt - 최고 성능 모델
- weights/last.pt - 마지막 에포크 모델
- results.png - 학습 결과 플롯
- confusion_matrix.png - 혼동 행렬
- P_curve.png, R_curve.png, F1_curve.png
- PR_curve.png - Precision-Recall 곡선
```

#### 3. CLI 명령어 개선

**`ddoc exp run` (멀티 트랙)**

```bash
# MLflow 모드 (기본값, Git 불필요)
ddoc exp run source@v1.0 --model yolov8n.pt --epochs 10

# MLflow 명시적 활성화/비활성화
ddoc exp run source@v1.0 --mlflow        # 활성화
ddoc exp run source@v1.0 --no-mlflow     # 비활성화

# DVC 모드 (레거시, Git 필요)
ddoc exp run source@v1.0 --dvc --queue
```

**주요 변경사항:**
- 실험 이름 인자 제거: 자동 생성 `exp_YYYYMMDD_HHMMSS`
- `--mlflow/--no-mlflow` 플래그로 추적 모드 선택
- `--dvc` 플래그로 레거시 DVC 모드 사용
- `plugin` 인자가 Option으로 변경: `--plugin yolo`

**`ddoc exp best` (신규)**

```bash
# mAP50-95 기준 최고 실험
ddoc exp best source@v1.0

# mAP50 기준
ddoc exp best source@v1.0 --metric mAP50

# precision 기준
ddoc exp best target@v2.1 --metric precision
```

**`ddoc exp compare` (개선)**

```bash
# MLflow 실험 비교
ddoc exp compare exp_20251113_104417 exp_20251113_105230 --mlflow

# 레거시 DVC 실험 비교
ddoc exp compare exp1 exp2 exp3
```

#### 4. 데이터 버전 통합

**MLflow 태그를 통한 메타데이터 저장**

```python
mlflow.set_tags({
    "ddoc.dataset_name": "source",
    "ddoc.dataset_version": "v1.0",
    "ddoc.dataset_id": "source@v1.0",
    "ddoc.experiment_id": "exp_20251113_104417",
    "ddoc.plugin": "yolo"
})
```

**계보 그래프 통합**

```python
metadata_service.add_experiment(
    experiment_id="exp_20251113_104417",
    experiment_name="exp_20251113_104417",
    dataset_id="source@v1.0",
    metadata={
        "mlflow_run_id": "abc123...",
        "plugin": "yolo",
        "metrics": {...},
        "tracking_type": "mlflow_ultralytics"
    }
)
```

**MLflow에서 데이터셋 버전별 필터링**

```python
# MLflow UI에서 또는 Python API로
mlflow.search_runs(
    experiment_names=["ddoc"],
    filter_string="tags.`ddoc.dataset_id` = 'source@v1.0'"
)
```

#### 5. 파일 구조

**프로젝트 루트**
```
ddoc/
├── core/
│   ├── experiment_service.py           # 레거시 (DVC 기반)
│   └── mlflow_experiment_service.py    # 신규 (MLflow 기반) ✨
├── cli/
│   └── commands.py                      # MLflow 명령어 통합 ✨
└── pyproject.toml                       # v1.3.6, mlflow 의존성 ✨

프로젝트 워크스페이스/
├── experiments/                         # 실험 결과
│   └── exp_20251113_104417/
│       ├── ddoc_metadata.json          # ddoc 메타데이터
│       └── weights/                     # 학습된 모델
└── mlruns/                              # MLflow 데이터 ✨
    └── 0/                               # ddoc experiment
        └── <run_id>/
            ├── metrics/
            ├── params/
            └── artifacts/
```

#### 6. 사용 워크플로우

**기본 워크플로우**

```bash
# 1. 데이터셋 준비 (Git 불필요)
ddoc dataset add source ./datasets/source
ddoc dataset add target ./datasets/target

# 2. 실험 실행 (MLflow 자동 활성화)
ddoc exp run source@v1.0 --model yolov8n.pt --epochs 10
ddoc exp run source@v1.0 --model yolov8s.pt --epochs 20
ddoc exp run source@v1.0 --model yolov8m.pt --epochs 30

# 3. MLflow UI에서 결과 확인
mlflow ui
# → 브라우저에서 http://localhost:5000 접속

# 4. 최고 실험 찾기
ddoc exp best source@v1.0

# 5. 계보 확인
ddoc lineage show source@v1.0
ddoc lineage visualize --output lineage.png

# 6. 다른 데이터셋 버전으로 실험
ddoc exp run source@v2.0 --model yolov8n.pt --epochs 10
```

**MLflow UI 기능**
- 실험 목록 및 필터링
- 메트릭 비교 및 시각화
- 파라미터 차이 분석
- 모델 아티팩트 다운로드
- Run 상세 정보 조회

#### 7. 아키텍처

**MLflow + ddoc 통합 구조**

```
CLI (ddoc exp run)
      ↓
MLflowExperimentService
  ├─ MLflow 설정 및 초기화
  ├─ Ultralytics 네이티브 통합 활성화
  └─ 데이터 버전과 실험 연결
      ↓                    ↓
Ultralytics YOLO    MetadataService
  - 자동 MLflow       - 계보 그래프
    로깅              - 실험 노드 추가
      ↓
MLflow Tracking Server
  - 메트릭, 파라미터, 아티팩트 저장
  - mlruns/ 디렉토리
```

#### 8. 레거시 지원

**기존 DVC 실험 시스템 (experiment_service.py) 보존**

- Git 기반 DVC experiments는 계속 작동
- `--dvc` 플래그로 명시적 사용
- 향후 하이브리드 모드 통합 가능성 염두

```bash
# DVC 모드 사용 (Git 필요)
ddoc exp run source@v1.0 --dvc

# DVC 큐에 추가
ddoc exp run source@v1.0 --dvc --queue

# DVC dry run
ddoc exp run source@v1.0 --dvc --dry-run
```

#### 9. 변경된 파일 목록

**핵심 파일:**
- `ddoc/core/mlflow_experiment_service.py` (신규) - MLflow 실험 서비스
- `ddoc/cli/commands.py` (수정)
  - `exp_run_command()`: MLflow/DVC 멀티 트랙
  - `exp_best_command()`: 최고 실험 찾기
  - `exp_compare_command()`: MLflow 비교 지원
  - `_run_mlflow_experiment()`: MLflow 실험 실행 헬퍼
  - `_run_dvc_experiment()`: DVC 실험 실행 헬퍼 (레거시)
- `ddoc/core/experiment_service.py` (수정)
  - `run_experiment()` 시그니처 변경: `name`, `params`, `queue`, `dry_run`
- `pyproject.toml` (수정)
  - 버전: `1.3.5` → `1.3.6`
  - 의존성 추가: `mlflow>=2.0.0`

**플러그인:**
- `ddoc-plugin-yolo`: 변경 없음 (Ultralytics가 MLflow 자동 지원)
- `ddoc-plugin-vis`: 변경 없음

#### 10. 기술적 특징

**Git 독립성**
- MLflow 자체 추적 시스템 사용
- `.mlruns/` 디렉토리에 모든 데이터 저장
- Git commit 불필요

**자동화**
- Ultralytics가 모든 메트릭, 파라미터, 아티팩트 자동 로깅
- 수동 로깅 코드 불필요
- 에포크별 메트릭 자동 업데이트

**확장성**
- 새로운 플러그인 추가 용이
- MLflow Model Registry 통합 가능
- 하이퍼파라미터 튜닝 (MLflow + Optuna) 준비

**성능**
- MLflow SQLite 백엔드로 빠른 조회
- 메모리 기반 캐싱
- 비동기 로깅 지원

#### 11. 비교: DVC vs MLflow

| 기능 | DVC Experiments | MLflow |
|------|----------------|--------|
| Git 필요 | ✅ 필수 | ❌ 불필요 |
| 웹 UI | ❌ 없음 | ✅ 강력함 |
| 자동 로깅 | ❌ 수동 | ✅ 자동 (Ultralytics) |
| 모델 관리 | ⚠️ 제한적 | ✅ Model Registry |
| 계보 추적 | ✅ DVC DAG | ✅ ddoc 연동 |
| 하이퍼파라미터 튜닝 | ❌ 없음 | ✅ 가능 |
| 학습 곡선 | 높음 | 낮음 |
| 사용 상황 | Git 워크플로우 선호 | 빠른 프로토타이핑 |

#### 12. 설치 및 업그레이드

**새 설치**
```bash
pip install -e .[yolo]
# MLflow가 자동으로 설치됨
```

**업그레이드**
```bash
cd /path/to/ddoc
git pull
pip install -e .[yolo]
```

**MLflow 확인**
```bash
mlflow --version
python3 -c "import mlflow; print(mlflow.__version__)"
```

#### 13. 문제 해결

**MLflow가 설치되지 않음**
```bash
pip install mlflow>=2.0.0
```

**Ultralytics MLflow 통합 비활성화됨**
```python
from ultralytics import settings
settings.update({"mlflow": True})
```

**실험이 MLflow에 표시되지 않음**
1. MLflow UI 새로고침
2. `mlruns/` 디렉토리 확인: `ls -la mlruns/`
3. MLFLOW_TRACKING_URI 확인: `echo $MLFLOW_TRACKING_URI`

**MLflow UI가 실행되지 않음**
```bash
# 포트 변경
mlflow ui --port 5001

# 원격 접속 허용
mlflow ui --host 0.0.0.0
```

#### 14. 향후 계획

**Phase 1: MLflow 고도화**
- MLflow Model Registry 통합
- 모델 버저닝 및 스테이징
- Production 배포 워크플로우

**Phase 2: 멀티 플러그인 지원**
- Vision 플러그인 MLflow 통합
- NLP 플러그인 MLflow 통합
- 커스텀 메트릭 로깅

**Phase 3: 하이브리드 모드**
- DVC와 MLflow 동시 사용
- Git 기반 코드 버전 + MLflow 실험 추적
- 통합 대시보드

**Phase 4: 자동화**
- 하이퍼파라미터 튜닝 (Optuna 통합)
- AutoML 파이프라인
- 실험 스케줄링

#### 15. 참고 자료

- [MLflow 공식 문서](https://mlflow.org/docs/latest/index.html)
- [Ultralytics MLflow 통합](https://docs.ultralytics.com/integrations/mlflow/)
- [MLflow Tracking API](https://mlflow.org/docs/latest/tracking.html)
- [MLflow Model Registry](https://mlflow.org/docs/latest/model-registry.html)

## 📚 참고 자료

- [Pluggy Documentation](https://pluggy.readthedocs.io/)
- [Typer Documentation](https://typer.tiangolo.com/)
- [DVC Documentation](https://dvc.org/doc)
- [Ultralytics YOLO](https://docs.ultralytics.com/)
- [CLIP Model](https://openai.com/blog/clip/)
- [Zsh Hooks Documentation](https://zsh.sourceforge.io/Doc/Release/Functions.html#Hook-Functions)
- [MLflow Documentation](https://mlflow.org/)
