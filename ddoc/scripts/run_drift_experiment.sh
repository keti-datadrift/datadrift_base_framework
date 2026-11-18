#!/bin/bash
#
# Drift-Driven Training Experiment Pipeline
#
# 이 스크립트는 드리프트 점수와 모델 성능 간 상관관계를 검증하는
# 전체 실험 파이프라인을 실행합니다.
#
# Round-5 update — v1 명령어를 v2 로 마이그레이션:
#   `ddoc drift-compare`  → `ddoc analyze drift`
#   `ddoc train`          → `ddoc exp train`     ([exp] extras 필요)
#
# Prerequisites:
#   pip install -e ".[exp]"                       # mlflow
#   pip install -e plugins/ddoc-plugin-yolo       # YOLO trainer plugin
#   datasets/{yolo_reference,yolo_current,yolo_target} 디렉터리 준비
#
# Note: 아래 ``--output analysis/...`` flag 는 v2 의 analyze drift 가
# 미지원 (output 경로는 snapshot id 기반 자동 산출). 실제 사용 시
# remove 또는 ``--data-path-ref/--data-path-cur`` path-mode 로 호출.
#
# 실험 순서:
# 1. 드리프트 분석 (Target vs Reference/Current)
# 2. 모델 학습 (Reference/Current 데이터셋)
# 3. 결과 비교 및 분석
#

set -e  # 에러 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 프로젝트 루트로 이동
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# 가상환경 확인
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo -e "${YELLOW}⚠️  Warning: Virtual environment not activated${NC}"
    echo -e "${YELLOW}   Activating venv...${NC}"
    source venv/bin/activate
fi

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Drift-Driven Training Experiment Pipeline            ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# 데이터셋 확인
echo -e "${BLUE}📦 Checking datasets...${NC}"
for dataset in yolo_reference yolo_current yolo_target; do
    if [ ! -d "datasets/$dataset" ]; then
        echo -e "${RED}❌ Error: datasets/$dataset not found${NC}"
        echo -e "${YELLOW}   Please run: python scripts/split_yolo_dataset.py${NC}"
        exit 1
    fi
    echo -e "${GREEN}   ✓ $dataset${NC}"
done
echo ""

# Phase 1: 드리프트 분석
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Phase 1: Drift Analysis${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}🔍 Analyzing drift: Target vs Reference...${NC}"
ddoc analyze drift yolo_target yolo_reference --output analysis/drift_target_vs_ref
echo ""

echo -e "${YELLOW}🔍 Analyzing drift: Target vs Current...${NC}"
ddoc analyze drift yolo_target yolo_current --output analysis/drift_target_vs_cur
echo ""

# 드리프트 결과 요약
echo -e "${GREEN}✅ Drift analysis completed${NC}"
echo ""

# Phase 2: 모델 학습
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Phase 2: Model Training${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}🚀 Training model on Reference dataset (epochs=5)...${NC}"
ddoc exp train yolo_reference --epochs 5 --batch 8 --device cpu --name exp_ref
echo ""

echo -e "${YELLOW}🚀 Training model on Current dataset (epochs=5)...${NC}"
ddoc exp train yolo_current --epochs 5 --batch 8 --device cpu --name exp_cur
echo ""

echo -e "${GREEN}✅ Model training completed${NC}"
echo ""

# Phase 3: 결과 비교
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Phase 3: Results Analysis${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}📊 Drift Scores:${NC}"
echo ""

# Target vs Reference 드리프트 점수
if [ -f "analysis/drift_target_vs_ref/drift_report.json" ]; then
    echo -e "${GREEN}Target vs Reference:${NC}"
    cat analysis/drift_target_vs_ref/drift_report.json | grep -A 5 '"drift_scores"' || echo "  (see analysis/drift_target_vs_ref/drift_report.json)"
    echo ""
fi

# Target vs Current 드리프트 점수
if [ -f "analysis/drift_target_vs_cur/drift_report.json" ]; then
    echo -e "${GREEN}Target vs Current:${NC}"
    cat analysis/drift_target_vs_cur/drift_report.json | grep -A 5 '"drift_scores"' || echo "  (see analysis/drift_target_vs_cur/drift_report.json)"
    echo ""
fi

echo -e "${YELLOW}📈 Model Performance:${NC}"
echo ""

# Reference 모델 성능
if [ -f "runs/exp_ref/results.csv" ]; then
    echo -e "${GREEN}Reference Model:${NC}"
    tail -1 runs/exp_ref/results.csv || echo "  (see runs/exp_ref/results.csv)"
    echo ""
fi

# Current 모델 성능
if [ -f "runs/exp_cur/results.csv" ]; then
    echo -e "${GREEN}Current Model:${NC}"
    tail -1 runs/exp_cur/results.csv || echo "  (see runs/exp_cur/results.csv)"
    echo ""
fi

# 실험 목록 확인
echo -e "${YELLOW}🔬 Registered Experiments:${NC}"
ddoc exp list
echo ""

echo -e "${GREEN}✅ Experiment pipeline completed!${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Next Steps:${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "1. Compare experiments:"
echo -e "   ${YELLOW}ddoc exp compare exp_ref exp_cur${NC}"
echo ""
echo -e "2. View detailed drift reports:"
echo -e "   ${YELLOW}analysis/drift_target_vs_ref/${NC}"
echo -e "   ${YELLOW}analysis/drift_target_vs_cur/${NC}"
echo ""
echo -e "3. View training results:"
echo -e "   ${YELLOW}runs/exp_ref/${NC}"
echo -e "   ${YELLOW}runs/exp_cur/${NC}"
echo ""
echo -e "4. Generate correlation analysis:"
echo -e "   ${YELLOW}python scripts/analyze_drift_performance_correlation.py${NC}"
echo ""

