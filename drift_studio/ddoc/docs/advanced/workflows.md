# 고급 워크플로우

고급 사용법 및 베스트 프랙티스를 설명합니다.

## 브랜치를 활용한 병렬 실험

Git 브랜치를 활용하여 여러 실험을 병렬로 진행할 수 있습니다:

```bash
# 메인 브랜치에서 baseline
git checkout main
ddoc snapshot create -m "baseline" -a baseline

# 새 브랜치에서 실험
git checkout -b experiment1
ddoc add --data new_augmented_data/
git add . && git commit -m "Experiment 1 data"
ddoc snapshot create -m "experiment 1" -a exp1

# 다른 브랜치에서 다른 실험
git checkout -b experiment2
ddoc add --data different_preprocessing/
git add . && git commit -m "Experiment 2 data"
ddoc snapshot create -m "experiment 2" -a exp2

# 결과 비교
ddoc snapshot --diff baseline exp1
ddoc snapshot --diff baseline exp2
```

## 캐시를 활용한 빠른 분석

ddoc는 분석 결과를 캐시하여 성능을 최적화합니다:

```bash
# 첫 분석 (전체 분석 수행)
ddoc analyze eda

# 데이터 일부 변경 후 재분석 (증분 분석)
ddoc analyze eda  # 변경된 파일만 재분석

# 캐시를 사용한 빠른 drift 분석
ddoc analyze drift v01 v02  # 캐시가 있으면 자동으로 사용
```

## 원격 스토리지 연동

DVC 원격 스토리지를 사용하여 데이터를 공유할 수 있습니다:

```bash
# DVC 원격 스토리지 설정
dvc remote add -d storage s3://mybucket/path

# 데이터 푸시
dvc push

# Git 푸시
git push origin main

# 다른 환경에서 복원
git clone <repo-url>
cd project
dvc pull
ddoc snapshot --restore production
```

## 팀 협업 워크플로우

### 1. 프로젝트 클론

```bash
git clone <repo-url>
cd project
dvc pull
```

### 2. 사용 가능한 스냅샷 확인

```bash
ddoc snapshot
```

### 3. 특정 버전으로 전환

```bash
ddoc snapshot --restore production
```

### 4. 변경사항 작업

```bash
ddoc add --data new_data/
git add . && git commit -m "My changes"
ddoc snapshot create -m "experiment X" -a exp-x
```

### 5. 변경사항 푸시

```bash
git push origin feature-branch
dvc push
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

### 4. 실험 전 스냅샷 생성

```bash
# 실험 전
ddoc snapshot create -m "Before experiment X" -a before_exp_x

# 실험 수행
ddoc exp train yolo --dataset dataset_name

# 결과 확인 후 스냅샷
ddoc snapshot create -m "After experiment X - accuracy: 0.95" -a exp_x
```

### 5. Git 커밋 메시지와 스냅샷 메시지 구분

```bash
# Git: 코드 변경사항
git commit -m "Refactored data preprocessing pipeline"

# ddoc: 전체 프로젝트 상태
ddoc snapshot create -m "Baseline with refactored preprocessing, original dataset"
```

### 6. Trainer 기반 실험 워크플로우

```bash
# 1. 워크스페이스 초기화
ddoc init myproject
cd myproject

# 2. 데이터 추가
ddoc add --data /path/to/dataset.zip

# 3. Trainer 코드 추가
ddoc add --code /path/to/train.py --trainer yolo
ddoc add --code /path/to/eval.py --trainer yolo
ddoc add --code /path/to/config.yaml --trainer yolo

# 4. 학습 실행
ddoc exp train yolo --dataset dataset_name

# 5. 평가 실행
ddoc exp eval yolo --dataset dataset_name --model experiments/exp_*/weights/best.pt

# 6. 최고 실험 찾기
ddoc exp best dataset_name --metric mAP50-95

# 7. MLflow UI로 결과 확인
mlflow ui
```

## 다음 단계

- [문제 해결](troubleshooting.md) - 자주 발생하는 문제 해결
- [워크스페이스 관리](../guides/workspace.md) - 프로젝트 관리 방법
- [스냅샷 관리](../guides/snapshots.md) - 버전 관리 방법

