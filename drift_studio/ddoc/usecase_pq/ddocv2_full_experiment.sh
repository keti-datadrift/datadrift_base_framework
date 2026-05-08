#!/bin/bash

################################################################################
# ddoc Full Experiment Pipeline - Drift Analysis & Model Performance
# 
# Usage: ./ddocv2_full_experiment.sh
#
# 전체 실험 파이프라인:
# 1. ref-target 드리프트 분석
# 2. cur-target 드리프트 분석  
# 3. ref 모델 학습
# 4. cur 모델 학습
# 5. 성능 비교 분석
################################################################################

set -e  # 에러 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 프로젝트 루트 디렉토리 — 스크립트 위치 기준 자동 산출.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 헬퍼 함수
print_header() {
    echo -e "${BLUE}================================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================================================${NC}"
}

print_step() {
    echo -e "${CYAN}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 사용법 출력
print_usage() {
    echo "Usage: $0"
    echo ""
    echo "Full experiment pipeline for drift analysis and model performance comparison:"
    echo "  1. Reference vs Target drift analysis"
    echo "  2. Current vs Target drift analysis"
    echo "  3. Reference model training"
    echo "  4. Current model training"
    echo "  5. Performance comparison analysis"
    echo ""
    echo "Prerequisites:"
    echo "  - yolo_reference, yolo_current, yolo_target datasets must exist"
    echo "  - Virtual environment must be activated"
    echo ""
}

# 인자 확인
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    print_usage
    exit 0
fi

print_header "🚀 DDOC Full Experiment Pipeline"
print_step "Starting comprehensive drift analysis and model performance experiment"

################################################################################
# 1. 환경 확인
################################################################################
print_header "1️⃣ Environment Check"

print_step "Checking virtual environment..."
if [[ "$VIRTUAL_ENV" != "" ]]; then
    print_success "Virtual environment activated: $VIRTUAL_ENV"
else
    print_warning "No virtual environment detected. Please activate venv first."
    print_step "Activating virtual environment..."
    source venv/bin/activate
    print_success "Virtual environment activated"
fi

print_step "Checking required datasets..."
for dataset in yolo_reference yolo_current yolo_target; do
    if [[ -d "datasets/$dataset" ]]; then
        print_success "Dataset found: $dataset"
    else
        print_error "Required dataset not found: $dataset"
        exit 1
    fi
done

################################################################################
# 2. Reference vs Target Drift Analysis
################################################################################
print_header "2️⃣ Reference vs Target Drift Analysis"

print_step "Running drift analysis: yolo_reference vs yolo_target"
./ddocv2_test_dataprocess.sh yolo_reference yolo_target

if [[ $? -eq 0 ]]; then
    print_success "Reference vs Target drift analysis completed"
else
    print_error "Reference vs Target drift analysis failed"
    exit 1
fi

################################################################################
# 3. Current vs Target Drift Analysis
################################################################################
print_header "3️⃣ Current vs Target Drift Analysis"

print_step "Running drift analysis: yolo_current vs yolo_target"
./ddocv2_test_dataprocess.sh yolo_current yolo_target

if [[ $? -eq 0 ]]; then
    print_success "Current vs Target drift analysis completed"
else
    print_error "Current vs Target drift analysis failed"
    exit 1
fi

################################################################################
# 4. Model Training (Reference & Current)
################################################################################
print_header "4️⃣ Model Training"

print_step "Running model training: yolo_reference & yolo_current"
./ddocv2_test_modelprocess.sh yolo_reference yolo_current

if [[ $? -eq 0 ]]; then
    print_success "Model training completed"
else
    print_error "Model training failed"
    exit 1
fi

################################################################################
# 5. Results Summary
################################################################################
print_header "5️⃣ Experiment Results Summary"

print_step "Checking drift analysis results..."

# Reference vs Target drift results
if [[ -f "analyses/drift_analysis_yolo_reference_yolo_target/drift_metadata.json" ]]; then
    print_success "Reference vs Target drift analysis results found"
    echo "📊 Reference vs Target drift scores:"
    python3 -c "
import json
with open('analyses/drift_analysis_yolo_reference_yolo_target/drift_metadata.json', 'r') as f:
    data = json.load(f)
    print(f'  Overall Drift Score: {data.get(\"overall_drift_score\", \"N/A\")}')
    print(f'  Attribute Drift: {data.get(\"attribute_drift_score\", \"N/A\")}')
    print(f'  Embedding Drift: {data.get(\"embedding_drift_score\", \"N/A\")}')
"
else
    print_warning "Reference vs Target drift results not found"
fi

# Current vs Target drift results
if [[ -f "analyses/drift_analysis_yolo_current_yolo_target/drift_metadata.json" ]]; then
    print_success "Current vs Target drift analysis results found"
    echo "📊 Current vs Target drift scores:"
    python3 -c "
import json
with open('analyses/drift_analysis_yolo_current_yolo_target/drift_metadata.json', 'r') as f:
    data = json.load(f)
    print(f'  Overall Drift Score: {data.get(\"overall_drift_score\", \"N/A\")}')
    print(f'  Attribute Drift: {data.get(\"attribute_drift_score\", \"N/A\")}')
    print(f'  Embedding Drift: {data.get(\"embedding_drift_score\", \"N/A\")}')
"
else
    print_warning "Current vs Target drift results not found"
fi

print_step "Checking experiment results..."
if [[ -d "experiments" ]]; then
    print_success "Experiment results found"
    echo "📈 Training experiments:"
    ls -la experiments/ | grep -E "(exp_|yolo_)" | head -5
else
    print_warning "No experiment results found"
fi

################################################################################
# 6. Performance Analysis
################################################################################
print_header "6️⃣ Performance Analysis"

print_step "Analyzing drift scores and model performance correlation..."

# 간단한 성능 분석 스크립트
python3 -c "
import json
import os

print('🔍 Drift Analysis Summary:')
print('=' * 50)

# Reference vs Target
ref_target_file = 'analyses/drift_analysis_yolo_reference_yolo_target/drift_metadata.json'
if os.path.exists(ref_target_file):
    with open(ref_target_file, 'r') as f:
        ref_data = json.load(f)
    print(f'Reference vs Target:')
    print(f'  Overall Drift: {ref_data.get(\"overall_drift_score\", \"N/A\")}')
    print(f'  Attribute Drift: {ref_data.get(\"attribute_drift_score\", \"N/A\")}')
    print(f'  Embedding Drift: {ref_data.get(\"embedding_drift_score\", \"N/A\")}')
else:
    print('Reference vs Target: Not found')

print()

# Current vs Target  
cur_target_file = 'analyses/drift_analysis_yolo_current_yolo_target/drift_metadata.json'
if os.path.exists(cur_target_file):
    with open(cur_target_file, 'r') as f:
        cur_data = json.load(f)
    print(f'Current vs Target:')
    print(f'  Overall Drift: {cur_data.get(\"overall_drift_score\", \"N/A\")}')
    print(f'  Attribute Drift: {cur_data.get(\"attribute_drift_score\", \"N/A\")}')
    print(f'  Embedding Drift: {cur_data.get(\"embedding_drift_score\", \"N/A\")}')
else:
    print('Current vs Target: Not found')

print()
print('📊 Analysis Complete!')
print('Next steps:')
print('  1. Compare drift scores between ref-target and cur-target')
print('  2. Train models on ref and cur datasets')
print('  3. Evaluate both models on target dataset')
print('  4. Analyze correlation between drift scores and model performance')
"

print_success "Full experiment pipeline completed successfully!"

print_header "🎉 Experiment Complete"
echo "📋 Summary:"
echo "  ✅ Reference vs Target drift analysis completed"
echo "  ✅ Current vs Target drift analysis completed"  
echo "  ✅ Model training completed"
echo "  ✅ Results analysis completed"
echo ""
echo "🔍 Next steps for inference performance comparison:"
echo "  1. Implement inference module for target dataset evaluation"
echo "  2. Compare model performance on target dataset"
echo "  3. Analyze correlation between drift scores and performance"
echo ""
echo "📁 Results location:"
echo "  - Drift analysis: analyses/"
echo "  - Training results: experiments/"
echo "  - Lineage tracking: lineage.json"
