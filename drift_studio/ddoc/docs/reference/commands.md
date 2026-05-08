# 명령어 레퍼런스

ddoc의 모든 CLI 명령어에 대한 상세한 레퍼런스입니다.

## 프로젝트 관리

### `ddoc init <path>`

새로운 ddoc 프로젝트를 초기화합니다.

**사용법:**
```bash
ddoc init myproject              # 새 프로젝트 생성
ddoc init .                      # 현재 디렉토리 초기화
ddoc init sandbox/experiment     # 특정 경로에 생성
ddoc init . --force              # 기존 디렉토리 강제 초기화
```

**옵션:**
- `--force, -f`: 기존 디렉토리가 있어도 강제 초기화

**동작:**
- 프로젝트 디렉토리 구조 생성
- Git 저장소 초기화
- DVC 초기화
- 설정 파일 생성

### `ddoc add`

파일을 워크스페이스에 추가합니다.

**사용법:**
```bash
ddoc add --data <path>           # 데이터 추가
ddoc add --code <path>           # 코드 추가
ddoc add --notebook <path>       # 노트북 추가
ddoc add --code <path> --trainer <name>  # Trainer 코드 추가
```

**옵션:**
- `--data`: 데이터 디렉토리 또는 ZIP 파일 추가 (DVC 추적)
- `--code`: 코드 파일 추가 (Git 추적)
- `--notebook`: 노트북 파일 추가
- `--trainer`: Trainer 이름 지정 (코드만 해당)

**예시:**
```bash
ddoc add --data datasets/train.zip       # ZIP 자동 압축 해제
ddoc add --data datasets/images/         # 디렉토리 복사
ddoc add --code scripts/train.py
ddoc add --code train.py --trainer yolo
```

## 스냅샷 관리

### `ddoc snapshot`

모든 스냅샷 관리 기능을 통합한 단일 명령입니다.

**기본 사용 (목록 조회):**
```bash
ddoc snapshot                            # 스냅샷 목록 (기본)
ddoc snapshot --list                     # 스냅샷 목록
ddoc snapshot --oneline                  # 간단한 포맷
ddoc snapshot -n 10                      # 최근 10개만
```

**스냅샷 생성:**
```bash
ddoc snapshot create -m "message"               # 스냅샷 생성
ddoc snapshot create -m "message" -a alias      # Alias와 함께 생성
ddoc snapshot create -m "msg" --no-auto-commit  # Git/DVC 자동 커밋 비활성화
```

**스냅샷 상세 조회:**
```bash
ddoc snapshot v01                        # v01 상세 정보
ddoc snapshot baseline                   # Alias로 조회
```

**스냅샷 복원:**
```bash
ddoc snapshot checkout v01              # 버전으로 복원
ddoc snapshot checkout baseline                # Alias로 복원 (축약형)
ddoc snapshot checkout v01 --force      # 강제 복원
```

**스냅샷 비교:**
```bash
ddoc snapshot --diff v01 v02             # 두 버전 비교
ddoc snapshot --diff baseline production # Alias로 비교
```

**계보 그래프:**
```bash
ddoc snapshot --graph                    # 스냅샷 관계도 표시
```

**스냅샷 삭제:**
```bash
ddoc snapshot --delete v01               # 스냅샷 삭제 (확인 필요)
ddoc snapshot --delete v01 --force       # 강제 삭제
```

**Alias 관리:**
```bash
ddoc snapshot --set-alias v03 best_model # Alias 설정
ddoc snapshot --unalias best_model       # Alias 제거
ddoc snapshot --show-aliases             # 모든 alias 조회
```

**스냅샷 설명 수정:**
```bash
ddoc snapshot --rename v01 "new description"
```

**무결성 검증:**
```bash
ddoc snapshot --verify v01               # v01 검증
ddoc snapshot --verify-all               # 모든 스냅샷 검증
```

**정리:**
```bash
ddoc snapshot --prune                    # 고아 스냅샷 식별
```

**주요 옵션:**
- `-m, --message TEXT`: 스냅샷 생성 메시지
- `-a, --alias TEXT`: 스냅샷 alias
- `-l, --list`: 목록 조회
- `checkout VERSION`: 스냅샷 복원 (서브커맨드 — 예: `ddoc snapshot checkout v01`)
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

## 데이터 분석

### `ddoc analyze eda`

EDA(탐색적 데이터 분석)을 수행합니다.

**사용법:**
```bash
ddoc analyze eda                        # 현재 워크스페이스 분석
ddoc analyze eda <snapshot_id>          # 특정 스냅샷 분석
ddoc analyze eda --save-snapshot        # 분석 후 자동 스냅샷 생성
```

**기능:**
- 데이터 속성 분석
- 임베딩 생성
- 클러스터링
- 시각화

### `ddoc analyze drift`

두 스냅샷 간 데이터 드리프트를 분석합니다.

**사용법:**
```bash
ddoc analyze drift <version1> <version2>
```

**예시:**
```bash
ddoc analyze drift baseline production
ddoc analyze drift v01 v05
```

**분석 항목:**
- 속성 드리프트 (KL Divergence 기반)
- 임베딩 드리프트 (MMD)
- 파일 변경사항

## 실험 관리

### `ddoc exp train`

Trainer를 사용하여 모델을 학습합니다.

**사용법:**
```bash
ddoc exp train <trainer_name> --dataset <dataset_name> [--model <model>]
```

**옵션:**
- `--dataset, -d`: 데이터셋 이름 (필수)
- `--model, -m`: 모델 이름 또는 경로 (선택)

**예시:**
```bash
ddoc exp train yolo --dataset yolo_reference
ddoc exp train yolo --dataset yolo_reference --model yolov8n.pt
ddoc exp train yolo --dataset yolo_reference --model models/custom.pt
```

### `ddoc exp eval`

학습된 모델을 평가합니다.

**사용법:**
```bash
ddoc exp eval <trainer_name> --dataset <dataset_name> --model <model_path>
```

**예시:**
```bash
ddoc exp eval yolo --dataset yolo_reference --model experiments/exp_*/weights/best.pt
ddoc exp eval yolo --dataset yolo_reference --model best.pt
```

### `ddoc exp best`

특정 데이터셋의 최고 성능 실험을 찾습니다.

**사용법:**
```bash
ddoc exp best <dataset> [--metric <metric_name>]
```

**예시:**
```bash
ddoc exp best yolo_reference
ddoc exp best yolo_reference --metric mAP50
ddoc exp best yolo_reference --metric precision
```

## 레거시 명령어 (Deprecated)

다음 명령어들은 v2.0.3에서 deprecated되었습니다:

- `ddoc commit` → `ddoc snapshot create -m`
- `ddoc checkout` → `ddoc snapshot checkout`
- `ddoc log` → `ddoc snapshot --list`
- `ddoc diff` → `ddoc snapshot --diff`
- `ddoc exp run` → `ddoc exp train`
- `ddoc exp list` → MLflow UI 사용
- `ddoc exp show` → MLflow UI 사용
- `ddoc exp compare` → MLflow UI 사용
- `ddoc exp status` → MLflow UI 사용

## 도움말

모든 명령어에 대한 도움말은 다음으로 확인할 수 있습니다:

```bash
ddoc --help
ddoc <command> --help
```

## 관련 문서

- [워크스페이스 관리](../guides/workspace.md)
- [스냅샷 관리](../guides/snapshots.md)
- [Trainer 시스템](../guides/trainer.md)
- [데이터 분석](../guides/analysis.md)
- [실험 관리](../guides/experiments.md)

