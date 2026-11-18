# ddoc 테스트 가이드

## 🎯 빠른 테스트 (3단계)

### 1단계: 환경 설정 (최초 1회)
```bash
cd /Users/bhc/dev/drift_v1/ddoc
./ddocv2_setup_environment.sh
```

### 2단계: 데이터 처리 테스트
```bash
source venv/bin/activate
./ddocv2_test_dataprocess.sh test_data test_yolo_sample
```

### 3단계: 모델 학습 테스트
```bash
./ddocv2_test_modelprocess.sh test_data test_yolo_sample
```

## 📋 테스트 스크립트

### 환경 설정 스크립트 (`ddocv2_setup_environment.sh`)
- Python venv 생성
- 모든 의존성 설치 (pluggy, typer, numpy, pandas, ultralytics, etc.)
- ddoc 및 플러그인 설치
- 설치 검증

### 데이터 처리 스크립트 (`ddocv2_test_dataprocess.sh`)
- 환경 확인
- 데이터셋 등록
- EDA (Exploratory Data Analysis)
- 드리프트 분석
- 결과 확인

### 모델 처리 스크립트 (`ddocv2_test_modelprocess.sh`)
- 실험 설정 확인
- Reference 모델 학습
- Current 모델 학습
- 실험 결과 비교

## ✅ 테스트 결과 확인

### 데이터 처리 결과
```bash
# 데이터셋 목록
ddoc dataset list

# 분석 메트릭 확인
cat analysis/test_data/metrics.json | python -m json.tool
cat analysis/test_yolo_sample/metrics.json | python -m json.tool

# 드리프트 분석 결과 확인
cat analysis/drift_test_data_vs_test_yolo_sample/metrics.json | python -m json.tool
```

### 모델 처리 결과
```bash
# 실험 목록
ddoc exp list

# 실험 상세 정보
ddoc exp show exp_ref
ddoc exp show exp_cur

# 실험 비교
ddoc exp compare exp_ref exp_cur
```

## 🧪 수동 테스트 절차

### 1. 데이터셋 관리 테스트 (새로운 Git/DVC 스타일 워크플로우)
```bash
# 데이터셋 추가 (staging)
ddoc dataset add test_data datasets/test_data
ddoc dataset add test_yolo_sample datasets/test_yolo_sample

# 변경사항 확인
ddoc dataset status

# 커밋하여 버전 생성
ddoc dataset commit -m "Initial datasets" -t v1.0

# 데이터셋 목록 확인
ddoc dataset list

# 버전 태그 관리
ddoc dataset tag list test_data
ddoc dataset tag rename test_data v1.0 -a baseline

# 타임라인 확인
ddoc dataset timeline test_data

# 데이터 수정 후 새 버전 생성
# ... 파일 수정 ...
ddoc dataset add test_data
ddoc dataset status
ddoc dataset commit -m "Updated images" -t v1.1
```

### 2. EDA 분석 테스트
```bash
# test_data 분석
ddoc analyze test_data

# test_yolo_sample 분석
ddoc analyze test_yolo_sample

# 결과 확인
ls analysis/test_data/
ls analysis/test_yolo_sample/
```

### 3. 드리프트 감지 테스트
```bash
# 이종 데이터셋 간 드리프트 비교
ddoc drift-compare test_data test_yolo_sample --output analysis/drift_comparison

# 결과 확인
ls analysis/drift_comparison/
cat analysis/drift_comparison/metrics.json | python -m json.tool
```

### 4. YOLO 학습 테스트
```bash
# YOLO 모델 학습
ddoc train test_yolo --epochs 2 --batch 4 --device cpu --name test_experiment

# 실험 결과 확인
ddoc exp list
ddoc exp show test_experiment
```

## 📊 테스트 데이터셋

### test_data
- **파일 수**: 97개 이미지
- **내용**: 랜덤 이미지 (다양한 콘텐츠)
- **형식**: .jpg, .png (hwp, xls 등은 자동 제외)
- **용도**: 일반적인 이미지 분석 테스트

### test_yolo_sample
- **파일 수**: 100개 이미지
- **내용**: 차량 번호판 (특화된 콘텐츠)
- **형식**: .jpg
- **용도**: YOLO 학습 및 특화된 드리프트 분석

### test_yolo
- **구조**: YOLO 형식 (train/images, valid/images, test/images)
- **라벨**: 객체 검출 라벨 포함
- **용도**: 실제 YOLO 학습 테스트

## 🎯 성공 기준

다음 명령어들이 모두 작동하면 테스트 성공:

```bash
ddoc --help                    # ✓ 명령어 도움말
ddoc dataset list              # ✓ 데이터셋 목록
ddoc analyze test_data         # ✓ EDA 분석
ddoc drift-compare test_data test_yolo_sample  # ✓ 드리프트 감지
ddoc train test_yolo --epochs 1  # ✓ YOLO 학습
ddoc exp list                  # ✓ 실험 목록
```

## 🚨 문제 해결

### 문제 1: `ddoc plugins-info` 명령어가 없다는 에러

**증상**:
```bash
ddoc: error: argument command: invalid choice: 'plugins-info'
```

**해결 방법**:
```bash
# ddoc 패키지 재설치
pip install -e . --force-reinstall --no-deps

# 플러그인 재설치
cd plugins/ddoc-plugin-vision && pip install -e . --force-reinstall --no-deps && cd ../..
cd plugins/ddoc-plugin-yolo && pip install -e . --force-reinstall --no-deps && cd ../..
```

### 문제 2: 가상환경 활성화 실패

**증상**: `source venv/bin/activate` 실행 시 에러

**해결 방법**:
```bash
# 가상환경 재생성
rm -rf venv
./ddocv2_setup_environment.sh
```

### 문제 3: 데이터셋 파일을 찾을 수 없음

**증상**: `데이터셋 파일을 찾을 수 없습니다!`

**해결 방법**:
```bash
# 데이터셋 디렉토리 확인
ls datasets/
ls datasets/test_data/
ls datasets/test_yolo_sample/

# 이미지 파일 확인
find datasets/ -name "*.jpg" -o -name "*.png" | head -10
```

### 문제 4: YOLO 학습 실패

**증상**: `Dataset 'data.yaml' images not found`

**해결 방법**:
```bash
# YOLO 형식 데이터셋 사용
ddoc train test_yolo --epochs 1  # test_yolo_sample 대신 test_yolo 사용
```

### 문제 5: AttributeError: 'list' object has no attribute 'get'

**증상**: 학습 중 `res.get('status')` 에러

**해결 방법**: 이미 수정됨. 최신 코드 사용:
```bash
git pull origin bhc
pip install -e . --force-reinstall --no-deps
```

## 📈 성능 벤치마크

### EDA 분석 성능
- **test_data (97개 이미지)**: ~30초
- **test_yolo_sample (100개 이미지)**: ~35초
- **캐시 활용**: 재분석 시 ~5초

### 드리프트 분석 성능
- **속성 드리프트**: ~10초
- **임베딩 드리프트**: ~20초
- **시각화 생성**: ~15초

### YOLO 학습 성능
- **1 epoch (CPU)**: ~15분
- **1 epoch (GPU)**: ~3분 (예상)
- **메트릭 추출**: ~1초

## 🔄 일상 작업 흐름

### 새 터미널을 열 때마다
```bash
cd /Users/bhc/dev/drift_v1/ddoc
source venv/bin/activate
```

### ddoc 사용하기 (새로운 워크플로우)
```bash
# 데이터셋 관리 (Git 스타일)
ddoc dataset add my_data datasets/my_data     # Stage
ddoc dataset status                            # 확인
ddoc dataset commit -m "Initial" -t v1.0       # Commit

# 데이터 수정 및 새 버전
# ... 파일 수정 ...
ddoc dataset add my_data                       # Stage changes
ddoc dataset commit -m "Update" -t v1.1        # Commit

# 태그 관리
ddoc dataset tag list my_data
ddoc dataset tag rename my_data v1.1 -a latest

# 타임라인 및 체크아웃
ddoc dataset timeline my_data
ddoc dataset checkout my_data v1.0

# 분석
ddoc analyze eda my_data

# 드리프트 감지
ddoc analyze drift baseline_data my_data

# YOLO 학습
ddoc exp run my_experiment my_yolo_data yolo --model yolov8n.pt --epochs 10
```

## 📝 로그 파일 위치

- **학습 로그**: `experiments/exp_*/train_*.log`
- **실험 메타데이터**: `experiments/exp_*/experiment_metadata.json`
- **분석 결과**: `analysis/*/metrics.json`
- **드리프트 결과**: `analysis/drift_*/metrics.json`
- **시각화**: `analysis/*/plots/images/`
