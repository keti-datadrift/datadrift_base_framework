# 스냅샷 관리

스냅샷은 특정 시점의 워크스페이스 전체 상태를 저장한 버전입니다. 이 가이드에서는 스냅샷 생성, 복원, 비교 등 모든 스냅샷 관리 기능을 설명합니다.

## 스냅샷이란?

스냅샷은 다음을 포함합니다:
- **데이터 상태**: DVC hash로 데이터 버전 추적
- **코드 상태**: Git commit hash로 코드 버전 추적
- **실험 결과**: 메트릭, 아티팩트, 메타데이터
- **설명 및 메타데이터**: 생성 시간, 설명, alias

## 스냅샷 명령어

### `ddoc snapshot`

모든 스냅샷 관리 기능을 통합한 단일 명령입니다.

### 스냅샷 목록 조회

```bash
ddoc snapshot                            # 스냅샷 목록 (기본)
ddoc snapshot --list                     # 스냅샷 목록
ddoc snapshot --oneline                  # 간단한 포맷
ddoc snapshot -n 10                      # 최근 10개만
```

### 스냅샷 생성

```bash
ddoc snapshot create -m "message"               # 스냅샷 생성
ddoc snapshot create -m "message" -a alias      # Alias와 함께 생성
ddoc snapshot create -m "msg" --no-auto-commit  # Git/DVC 자동 커밋 비활성화
```

**예시:**
```bash
ddoc snapshot create -m "baseline model"
ddoc snapshot create -m "improved accuracy" -a best_model
ddoc snapshot create -m "production ready" -a production
```

**주의사항:**
- 스냅샷 생성 전 Git 커밋이 필요합니다
- `--no-auto-commit` 옵션을 사용하지 않으면 자동으로 Git/DVC 커밋이 수행됩니다

### 스냅샷 상세 조회

```bash
ddoc snapshot v01                        # v01 상세 정보
ddoc snapshot baseline                   # Alias로 조회
```

### 스냅샷 복원

```bash
ddoc snapshot --restore v01              # 버전으로 복원
ddoc snapshot -r baseline                # Alias로 복원 (축약형)
ddoc snapshot --restore v01 --force      # 강제 복원
```

**복원 시 주의사항:**
- 현재 변경사항이 있으면 먼저 커밋하거나 `--force` 사용
- 복원 시 데이터와 코드가 모두 해당 버전으로 복원됩니다

### 스냅샷 비교

```bash
ddoc snapshot --diff v01 v02             # 두 버전 비교
ddoc snapshot --diff baseline production # Alias로 비교
```

**비교 결과:**
- 데이터 변경사항 (DVC hash 차이, 추가/삭제된 데이터셋)
- 코드 변경사항 (Git diff 통계)
- 실험 메트릭 차이

### 계보 그래프

```bash
ddoc snapshot --graph                    # 스냅샷 관계도 표시
```

### 스냅샷 삭제

```bash
ddoc snapshot --delete v01               # 스냅샷 삭제 (확인 필요)
ddoc snapshot --delete v01 --force       # 강제 삭제
```

### Alias 관리

```bash
ddoc snapshot --set-alias v03 best_model # Alias 설정
ddoc snapshot --unalias best_model       # Alias 제거
ddoc snapshot --show-aliases             # 모든 alias 조회
```

### 스냅샷 설명 수정

```bash
ddoc snapshot --rename v01 "new description"
```

### 무결성 검증

```bash
ddoc snapshot --verify v01               # v01 검증
ddoc snapshot --verify-all               # 모든 스냅샷 검증
```

### 정리

```bash
ddoc snapshot --prune                    # 고아 스냅샷 식별
```

## 주요 옵션

- `-m, --message TEXT`: 스냅샷 생성 메시지
- `-a, --alias TEXT`: 스냅샷 alias
- `-l, --list`: 목록 조회
- `-r, --restore VERSION`: 스냅샷 복원
- `--diff V1 V2`: 두 스냅샷 비교
- `--graph`: 계보 그래프 표시
- `--delete VERSION`: 스냅샷 삭제
- `--set-alias V ALIAS`: Alias 설정
- `--unalias ALIAS`: Alias 제거
- `--verify VERSION`: 무결성 검증
- `--prune`: 고아 스냅샷 식별
- `-f, --force`: 강제 실행
- `--oneline`: 간단한 포맷
- `-n, --limit N`: 개수 제한

## 워크플로우 예시

### 기본 워크플로우

```bash
# 1. 초기 데이터로 baseline 스냅샷 생성
ddoc add --data initial_data/
git add . && git commit -m "Initial setup"
ddoc snapshot create -m "Initial baseline" -a baseline

# 2. 데이터 증강 추가
ddoc add --data augmented_data/
git add . && git commit -m "Added augmentation"
ddoc snapshot create -m "With augmentation" -a augmented

# 3. 스냅샷 목록 확인
ddoc snapshot

# 4. 스냅샷 비교
ddoc snapshot --diff baseline augmented

# 5. 이전 버전으로 복원
ddoc snapshot --restore baseline
```

### 프로덕션 배포 워크플로우

```bash
# 1. 최적의 스냅샷 선택
ddoc snapshot --list
ddoc snapshot v05  # 상세 정보 확인

# 2. Production alias 설정
ddoc snapshot --set-alias v05 production

# 3. Production 스냅샷으로 전환
ddoc snapshot --restore production

# 4. 무결성 검증
ddoc snapshot --verify production
```

## 베스트 프랙티스

### 1. 명확한 스냅샷 메시지

```bash
# 좋은 예
ddoc snapshot create -m "Added 10K augmented images, improved preprocessing"

# 나쁜 예
ddoc snapshot create -m "update"
```

### 2. 의미있는 Alias 사용

```bash
ddoc snapshot create -m "Initial model" -a baseline
ddoc snapshot create -m "Best performing model" -a best_accuracy
ddoc snapshot create -m "Deployed to production" -a production_v1
```

### 3. 정기적인 스냅샷 생성

```bash
# 중요한 변경사항마다 스냅샷 생성
ddoc add --data new_data/
git add . && git commit -m "Added new data batch"
ddoc snapshot create -m "Added 2025-11 data batch"
```

### 4. Git 커밋 메시지와 스냅샷 메시지 구분

```bash
# Git: 코드 변경사항
git commit -m "Refactored data preprocessing pipeline"

# ddoc: 전체 프로젝트 상태
ddoc snapshot create -m "Baseline with refactored preprocessing, original dataset"
```

## 다음 단계

- [워크스페이스 관리](workspace.md) - 프로젝트 관리 방법
- [데이터 분석](analysis.md) - 스냅샷 간 Drift 분석
- [실험 관리](experiments.md) - 실험 실행 및 추적

