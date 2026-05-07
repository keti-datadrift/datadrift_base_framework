# 핵심 개념

ddoc를 효과적으로 사용하기 위해 알아야 할 핵심 개념들입니다.

## 1. Workspace (워크스페이스)

워크스페이스는 ddoc 프로젝트의 전체 작업 공간입니다. 모든 데이터, 코드, 실험 결과가 워크스페이스 내에서 관리됩니다.

### 워크스페이스 구조

```
project/
├── data/                    # 데이터셋 (DVC로 관리)
├── code/                    # 학습 코드 (Git으로 관리)
│   └── trainers/           # Trainer 코드
│       └── {trainer_name}/
│           ├── train.py    # 학습 함수
│           ├── eval.py     # 평가 함수
│           └── config.yaml # 기본 설정
├── models/                  # 사전학습 모델 저장소
├── notebooks/               # EDA 노트북
├── experiments/             # 실험 결과 (MLflow 구조)
└── .ddoc/                   # ddoc 메타데이터
    ├── snapshots/          # 스냅샷 YAML 파일
    └── cache/              # 분석 캐시
```

### 워크스페이스의 특징

- **통합 관리**: 데이터, 코드, 실험을 하나의 워크스페이스에서 관리
- **자동 스캐폴딩**: `ddoc init`으로 완전한 프로젝트 구조 자동 생성
- **Git/DVC 통합**: 코드는 Git, 데이터는 DVC로 자동 추적

## 2. Snapshot (스냅샷)

스냅샷은 특정 시점의 워크스페이스 전체 상태를 저장한 버전입니다.

### 스냅샷이 포함하는 것

- **데이터 상태**: DVC hash로 데이터 버전 추적
- **코드 상태**: Git commit hash로 코드 버전 추적
- **실험 결과**: 메트릭, 아티팩트, 메타데이터
- **설명 및 메타데이터**: 생성 시간, 설명, alias

### 스냅샷의 특징

- **완전한 재현성**: 스냅샷 하나로 전체 환경 복원 가능
- **자동 버전 번호**: v01, v02, v03... 자동 생성
- **Git-like 워크플로우**: commit, checkout, log, diff 명령 지원

### 스냅샷 사용 예시

```bash
# 스냅샷 생성
ddoc snapshot create -m "baseline model" -a baseline

# 스냅샷 목록 확인
ddoc snapshot

# 스냅샷 복원
ddoc snapshot --restore baseline

# 스냅샷 비교
ddoc snapshot --diff baseline v02
```

## 3. Alias (별칭)

Alias는 스냅샷에 의미있는 이름을 부여하는 기능입니다.

### Alias 사용 예시

```bash
# Alias와 함께 스냅샷 생성
ddoc snapshot create -m "baseline model" -a baseline
ddoc snapshot create -m "best accuracy" -a best_model
ddoc snapshot create -m "production ready" -a production

# Alias로 스냅샷 참조
ddoc snapshot --restore baseline
ddoc snapshot --diff baseline production
```

### Alias의 장점

- **의미있는 이름**: v01, v02 대신 baseline, production 같은 이름 사용
- **쉬운 참조**: 버전 번호를 기억할 필요 없이 alias로 접근
- **프로덕션 관리**: production alias로 배포 버전 관리

## 4. Trainer (트레이너)

Trainer는 표준화된 인터페이스로 모델 학습/평가를 수행하는 코드입니다.

### Trainer 구조

```
code/trainers/{trainer_name}/
├── train.py      # 필수: train(dataset_path, output_dir, **kwargs) 함수
├── eval.py       # 필수: evaluate(model_path, dataset_path, output_dir, **kwargs) 함수
└── config.yaml   # 선택: 기본 학습 파라미터
```

### Trainer의 특징

- **표준화된 인터페이스**: 모든 Trainer가 동일한 함수 시그니처 사용
- **유연한 확장**: 사용자 정의 Trainer 작성 가능
- **자동 추적**: MLflow와 통합하여 실험 자동 추적

## 5. 데이터 해시 (Data Hash)

데이터 해시는 DVC를 통해 계산된 데이터의 고유 식별자입니다.

### 데이터 해시의 역할

- **데이터 버전 추적**: 데이터 변경 시 해시 변경
- **캐시 관리**: 동일한 데이터 해시는 캐시 공유
- **재현성 보장**: 데이터 해시로 정확한 데이터 버전 복원

## 6. 캐시 시스템

ddoc는 분석 결과를 캐시하여 성능을 최적화합니다.

### 캐시의 특징

- **증분 분석**: 변경된 파일만 재분석
- **데이터 해시 기반**: 동일한 데이터 해시는 캐시 공유
- **자동 동기화**: 데이터 변경 시 캐시 자동 동기화

## 다음 단계

이제 핵심 개념을 이해했으니:
- [워크스페이스 관리](../guides/workspace.md) - 프로젝트 관리 방법
- [스냅샷 관리](../guides/snapshots.md) - 버전 관리 방법
- [Trainer 시스템](../guides/trainer.md) - 실험 시스템 사용법

