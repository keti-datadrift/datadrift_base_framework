# 빠른 시작

5분 안에 ddoc의 기본 사용법을 익혀보세요.

> 💡 **본인 데이터 없이 먼저 drift 결과만 보고 싶다면**
> [toy-data 튜토리얼](toy-data.md) 부터 — `ddoc examples generate
> timeseries` 한 줄로 합성 데이터셋 만들고 `ddoc analyze drift` 로 즉시
> 검증할 수 있습니다 (project / DVC 설정 불필요).

## 1. 프로젝트 초기화

```bash
# 새 프로젝트 생성
ddoc init myproject
cd myproject
```

이 명령어는 다음을 자동으로 생성합니다:
- 프로젝트 디렉토리 구조 (`data/`, `code/`, `notebooks/`, `experiments/`)
- Git 저장소 초기화
- DVC 초기화
- 설정 파일 생성

## 2. 데이터 추가

```bash
# 데이터 디렉토리 추가
ddoc add --data /path/to/dataset

# ZIP 파일도 자동으로 압축 해제됩니다
ddoc add --data /path/to/data.zip
```

## 3. 코드 추가

```bash
# 일반 코드 추가
ddoc add --code /path/to/script.py

# Trainer 코드 추가 (실험 시스템용)
ddoc add --code /path/to/train.py --trainer yolo
ddoc add --code /path/to/eval.py --trainer yolo
```

## 4. 첫 스냅샷 생성

```bash
# Git 커밋 (코드 버전 관리)
git add .
git commit -m "Initial setup"

# ddoc 스냅샷 생성 (데이터 + 코드 + 실험 상태)
ddoc snapshot create -m "baseline model" -a baseline
```

스냅샷은 다음을 포함합니다:
- 데이터 상태 (DVC hash)
- 코드 상태 (Git commit hash)
- 실험 결과 및 메타데이터

## 5. 데이터 분석

```bash
# EDA (탐색적 데이터 분석)
ddoc analyze eda
```

## 6. 실험 실행

```bash
# Trainer를 사용한 모델 학습
ddoc exp train yolo --dataset dataset_name

# 모델 평가
ddoc exp eval yolo --dataset dataset_name --model experiments/exp_*/weights/best.pt

# 최고 성능 실험 찾기
ddoc exp best dataset_name
```

## 7. 스냅샷 관리

```bash
# 스냅샷 목록 확인
ddoc snapshot

# 스냅샷 비교
ddoc snapshot --diff baseline v02

# 이전 버전으로 복원
ddoc snapshot checkout baseline
```

## 다음 단계

- [핵심 개념](concepts.md) - Workspace, Snapshot, Alias 이해하기
- [워크스페이스 관리](../guides/workspace.md) - 프로젝트 관리 상세 가이드
- [스냅샷 관리](../guides/snapshots.md) - 버전 관리 상세 가이드

