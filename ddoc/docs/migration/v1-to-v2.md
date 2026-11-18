# ddoc v2.0.0 마이그레이션 가이드

## 개요

ddoc v2.0.0은 대대적인 구조 개편을 통해 더 직관적이고 강력한 버전 관리 시스템을 제공합니다.

## 주요 변경사항

### 1. 새로운 워크스페이스 구조

**v2.0.0 워크스페이스:**
```
project/
├── data/                    # 모든 데이터셋 (DVC 번들 관리)
├── code/                    # 학습 코드 (Git 관리)
├── notebooks/               # 분석 노트북
├── experiments/             # 실험 결과
├── .ddoc/                   # ddoc 메타데이터
│   ├── snapshots/          # 스냅샷 YAML 파일
│   ├── cache/              # 분석 캐시
│   └── config.yaml         # 설정
├── .git/                    # Git 저장소
├── .dvc/                    # DVC 설정
└── data.dvc                 # data/ 전체 추적
```

### 2. Git-like 워크플로우

**기존 (v1.x):**
```bash
ddoc dataset add my_data ./data
ddoc dataset commit -m "initial"
ddoc dataset tag my_data v1 baseline
```

**새로운 (v2.0.0):**
```bash
ddoc init myproject
ddoc add --data ./data
ddoc commit -m "initial" -a baseline
ddoc checkout baseline
ddoc log
```

### 3. 스냅샷 기반 버전 관리

- **스냅샷**: 데이터, 코드, 실험 결과를 포함한 전체 워크스페이스 상태
- **Alias**: 스냅샷에 의미있는 이름 부여 (예: baseline, production)
- **자동 버전 번호**: v01, v02, v03... 자동 생성

## 명령어 비교

### 프로젝트 초기화

| v1.x | v2.0.0 | 설명 |
|------|------|------|
| `ddoc init` | `ddoc init <path>` | 프로젝트 구조 자동 생성 |

### 데이터/코드 추가

| v1.x | v2.0.0 | 설명 |
|------|------|------|
| `ddoc dataset add <name> <path>` | `ddoc add --data <path>` | 데이터 추가 |
| `ddoc code register <path>` | `ddoc add --code <path>` | 코드 추가 |
| - | `ddoc add --notebook <path>` | 노트북 추가 (신규) |

### 버전 관리

| v1.x | v2.0.0 | 설명 |
|------|------|------|
| `ddoc dataset commit -m "msg"` | `ddoc commit -m "msg"` | 스냅샷 생성 |
| `ddoc dataset tag <ds> <ver> <alias>` | `ddoc commit -m "msg" -a <alias>` | Alias와 함께 생성 |
| `ddoc dataset checkout <ds> <ver>` | `ddoc checkout <version>` | 스냅샷 복원 |
| `ddoc dataset list` | `ddoc log` | 히스토리 조회 |
| `ddoc dataset status` | `ddoc status` | 현재 상태 조회 |

### 새로운 명령어

| 명령어 | 설명 |
|--------|------|
| `ddoc alias <version> <name>` | Alias 관리 |
| `ddoc diff <v1> <v2>` | 스냅샷 비교 |
| `ddoc log --oneline` | 간단한 히스토리 |

## 마이그레이션 단계

### 1. 기존 프로젝트 백업

```bash
# 기존 프로젝트 백업
cp -r my_project my_project_backup
```

### 2. 새로운 v2.0.0 워크스페이스 생성

```bash
# 새 프로젝트 초기화
ddoc init my_project_v2
cd my_project_v2
```

### 3. 데이터 및 코드 이전

```bash
# 기존 데이터 복사
ddoc add --data ../my_project/datasets/my_data

# 기존 코드 복사
ddoc add --code ../my_project/train.py
ddoc add --code ../my_project/model.py
```

### 4. 첫 스냅샷 생성

```bash
# Git commit 필요
git add .
git commit -m "Migrated from v1.x"

# 스냅샷 생성
ddoc commit -m "Migrated baseline from v1.x" -a baseline
```

### 5. 기존 버전 이력 재생성 (선택)

기존 프로젝트에 여러 버전이 있었다면:

```bash
# 각 버전별로 체크아웃하고 스냅샷 생성
# v1.x에서:
ddoc dataset checkout my_data v1
cp -r datasets/my_data ../my_project_v2/data/

# v2.0.0에서:
cd ../my_project_v2
dvc add data/
git add data.dvc
git commit -m "Version 1"
ddoc commit -m "Historical v1" -a v1

# 반복...
```

## 새로운 워크플로우 예시

### 기본 워크플로우

```bash
# 1. 프로젝트 생성
ddoc init myproject
cd myproject

# 2. 데이터 추가
ddoc add --data ~/datasets/train_images.zip

# 3. 코드 추가
ddoc add --code ~/scripts/train.py

# 4. Git commit
git add .
git commit -m "Initial setup"

# 5. Baseline 스냅샷 생성
ddoc commit -m "baseline model" -a baseline

# 6. 실험 실행
ddoc exp run exp_001

# 7. 데이터 추가/수정
ddoc add --data ~/datasets/augmented/

# 8. Git commit
git add .
git commit -m "Added augmented data"

# 9. 새 스냅샷 생성
ddoc commit -m "with augmentation" -a augmented

# 10. 스냅샷 비교
ddoc diff baseline augmented

# 11. 이전 버전으로 복원
ddoc checkout baseline
```

### 분석 워크플로우

```bash
# EDA 수행
ddoc analyze eda

# 두 스냅샷 간 Drift 분석
ddoc analyze drift baseline augmented

# 실험 비교
ddoc exp compare exp_001 exp_002

# 로그 확인
ddoc log
ddoc log --oneline
```

## 호환성 노트

### 유지되는 기능
- `ddoc analyze eda`
- `ddoc analyze drift`
- `ddoc exp run`
- `ddoc exp list`
- `ddoc exp compare`
- Plugin 시스템

### Deprecated 명령어

다음 명령어들은 v2.0.0에서 제거되거나 deprecated 됩니다:

- `ddoc dataset add` → `ddoc add --data`
- `ddoc dataset commit` → `ddoc commit`
- `ddoc dataset checkout` → `ddoc checkout`
- `ddoc dataset tag` → `ddoc alias`
- `ddoc dataset list` → `ddoc log`
- `ddoc code register` → `ddoc add --code`

## 주요 개선사항

### 1. 단순한 데이터 관리
- 데이터셋별 개별 관리에서 data/ 전체 번들 관리로 전환
- DVC 내부 deduplication으로 저장 공간 효율적

### 2. 명확한 책임 분리
- data/ (DVC 관리)
- code/ (Git 관리)
- experiments/ (추적 제외)
- .ddoc/ (ddoc 전용)

### 3. Git과의 자연스러운 통합
- Git commit 기반 코드 버전 관리
- DVC와 Git의 완전한 연동

### 4. 강력한 재현성
- 스냅샷 하나로 전체 환경 복원
- Git hash + DVC hash로 100% 재현성 보장

### 5. GUI 확장성
- 모든 작업이 CLI로 가능
- 추후 GUI에서 CLI 호출 가능한 구조

## 문제 해결

### Q: 기존 데이터셋 이름을 유지하고 싶습니다.

A: data/ 아래에 동일한 이름으로 디렉토리를 만들면 됩니다:

```bash
ddoc add --data ~/old_project/datasets/my_dataset
# → data/my_dataset/로 복사됨
```

### Q: 여러 데이터셋을 독립적으로 버전 관리하고 싶습니다.

A: v2.0.0은 data/ 전체를 번들로 관리합니다. 하지만 스냅샷별로 다른 데이터셋 조합을 가질 수 있습니다:

```bash
# 스냅샷 v01: test_data만
ddoc add --data test_data/
ddoc commit -m "with test data" -a test_only

# 스냅샷 v02: test_data + yolo_reference
ddoc add --data yolo_reference/
ddoc commit -m "with both datasets" -a both
```

### Q: Git/DVC가 없는 환경에서도 사용할 수 있나요?

A: v2.0.0은 Git과 DVC를 필수로 요구합니다. 설치가 필요합니다:

```bash
# Git 설치
# macOS: brew install git
# Ubuntu: sudo apt install git

# DVC 설치
pip install dvc
```

### Q: 기존에 커밋된 .ddoc/ 디렉토리를 Git에서 제거하고 싶습니다.

A: 스냅샷 메타데이터는 이제 Git에서 제외됩니다. 기존에 커밋된 파일을 제거하려면:

```bash
# 1. .gitignore에 .ddoc/ 추가 확인
echo ".ddoc/" >> .gitignore

# 2. Git 캐시에서 .ddoc/ 제거 (파일은 유지)
git rm -r --cached .ddoc/

# 3. 변경사항 커밋
git commit -m "Remove .ddoc/ from Git tracking (metadata now independent)"
```

**주의**: 이 작업은 Git 히스토리에서 `.ddoc/` 파일을 제거하지만, 실제 파일은 유지됩니다. 스냅샷 정보는 그대로 보존됩니다.

## 추가 리소스

- [v2.0.0 사용자 가이드](./README_v2.md)
- [API 문서](./API.md)
- [예제 프로젝트](../examples/)

## 피드백

v2.0.0에 대한 피드백이나 문제가 있으시면 GitHub Issues에 등록해주세요.

