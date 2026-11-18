#!/bin/bash

################################################################################
# ddoc 환경 설정 스크립트
# 
# Python venv 생성 및 모든 의존성 설치
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

################################################################################
# 헬퍼 함수
################################################################################

print_header() {
    echo -e "${CYAN}"
    echo "================================================================================"
    echo "$1"
    echo "================================================================================"
    echo -e "${NC}"
}

print_step() {
    echo -e "${GREEN}[✓] $1${NC}"
}

print_info() {
    echo -e "${BLUE}[ℹ] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[⚠] $1${NC}"
}

print_error() {
    echo -e "${RED}[✗] $1${NC}"
}

################################################################################
# Phase 1: 환경 확인
################################################################################

print_header "Phase 1: 환경 확인"

# Python 확인
print_info "Python 버전 확인..."
if ! command -v python3 &> /dev/null; then
    print_error "Python3이 설치되어 있지 않습니다."
    print_error "Python 3.8 이상을 설치해주세요."
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
print_step "Python 확인: $PYTHON_VERSION"

# Git 확인
if ! command -v git &> /dev/null; then
    print_error "Git이 설치되어 있지 않습니다."
    exit 1
fi
print_step "Git 확인됨"

echo ""

################################################################################
# Phase 2: 가상환경 생성
################################################################################

print_header "Phase 2: Python venv 생성"

# 기존 venv 확인
if [ -d "venv" ]; then
    print_warning "기존 가상환경이 발견되었습니다."
    echo -e "${YELLOW}기존 가상환경을 삭제하고 새로 생성하시겠습니까? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_info "기존 가상환경 삭제 중..."
        rm -rf venv
        print_step "기존 가상환경 삭제 완료"
    else
        print_info "기존 가상환경을 유지합니다."
        print_warning "의존성이 누락되었을 수 있으니 재설치를 권장합니다."
    fi
fi

# venv 생성
if [ ! -d "venv" ]; then
    print_info "Python venv 생성 중..."
    python3 -m venv venv
    print_step "가상환경 생성 완료: venv/"
else
    print_step "기존 가상환경 사용: venv/"
fi

echo ""

################################################################################
# Phase 3: 가상환경 활성화
################################################################################

print_header "Phase 3: 가상환경 활성화"

print_info "가상환경 활성화 중..."
source venv/bin/activate

# 활성화 확인
if [ -z "$VIRTUAL_ENV" ]; then
    print_error "가상환경 활성화 실패"
    exit 1
fi

print_step "가상환경 활성화 완료"
print_info "가상환경 경로: $VIRTUAL_ENV"
echo ""

################################################################################
# Phase 4: pip 업그레이드
################################################################################

print_header "Phase 4: pip 업그레이드"

print_info "pip 업그레이드 중..."
pip install --upgrade pip --quiet
pip_version=$(pip --version)
print_step "pip 업그레이드 완료: $pip_version"
echo ""

################################################################################
# Phase 5: 핵심 의존성 설치
################################################################################

print_header "Phase 5: 핵심 의존성 설치 (1/4)"

print_info "핵심 의존성 설치 중..."
print_info "  - pluggy (플러그인 시스템)"
print_info "  - typer (CLI 프레임워크)"
print_info "  - rich (터미널 출력)"
print_info "  - pydantic (데이터 검증)"
print_info "  - pyyaml (YAML 파싱)"

pip install pluggy typer rich pydantic pyyaml --quiet

print_step "핵심 의존성 설치 완료"
echo ""

################################################################################
# Phase 6: 데이터 처리 라이브러리 설치
################################################################################

print_header "Phase 6: 데이터 처리 라이브러리 설치 (2/4)"

print_info "데이터 처리 라이브러리 설치 중..."
print_info "  - numpy"
print_info "  - pandas"
print_info "  - scikit-learn"

pip install numpy pandas scikit-learn --quiet

print_step "데이터 처리 라이브러리 설치 완료"
echo ""

################################################################################
# Phase 7: ddoc 패키지 설치
################################################################################

print_header "Phase 7: ddoc 패키지 설치 (3/4)"

print_info "ddoc 패키지 설치 중..."
pip install -e . --quiet

# 설치 확인
if command -v ddoc &> /dev/null; then
    print_step "ddoc 패키지 설치 완료"
    ddoc_version=$(pip show ddoc | grep Version | cut -d' ' -f2)
    print_info "ddoc 버전: $ddoc_version"
else
    print_error "ddoc 패키지 설치 실패"
    exit 1
fi

echo ""

################################################################################
# Phase 8: 플러그인 설치
################################################################################

print_header "Phase 8: 플러그인 설치 (4/4)"

# Vision 플러그인
print_info "Vision 플러그인 설치 중..."
print_warning "  (torch, clip 등 대용량 패키지 다운로드로 시간 소요 가능)"
cd plugins/ddoc-plugin-vision
pip install -e .
cd ../..
print_step "Vision 플러그인 설치 완료"

# YOLO 플러그인
print_info "YOLO 플러그인 설치 중..."
print_warning "  (ultralytics, opencv 등 대용량 패키지 다운로드로 시간 소요 가능)"
cd plugins/ddoc-plugin-yolo
pip install -e .
cd ../..
print_step "YOLO 플러그인 설치 완료"

echo ""

################################################################################
# Phase 9: 추가 도구 설치
################################################################################

print_header "Phase 9: 추가 도구 설치"

print_info "DVC 설치 중..."
pip install dvc --quiet
print_step "DVC 설치 완료"

echo ""

################################################################################
# Phase 10: 설치 검증
################################################################################

print_header "Phase 10: 설치 검증"

print_info "설치 검증 중..."

# ddoc 명령어 확인
if ! command -v ddoc &> /dev/null; then
    print_error "ddoc 명령어를 찾을 수 없습니다."
    exit 1
fi
print_step "ddoc 명령어 확인"

# DVC 명령어 확인
if ! command -v dvc &> /dev/null; then
    print_warning "dvc 명령어를 찾을 수 없습니다."
else
    print_step "dvc 명령어 확인"
fi

# Python 모듈 확인
print_info "Python 모듈 확인..."
python -c "import pluggy; import typer; import rich; import pydantic" 2>/dev/null
if [ $? -eq 0 ]; then
    print_step "핵심 모듈 임포트 성공"
else
    print_error "핵심 모듈 임포트 실패"
    exit 1
fi

# 플러그인 로드 확인
print_info "플러그인 로드 확인..."
ddoc plugins-info > /dev/null 2>&1
if [ $? -eq 0 ]; then
    print_step "플러그인 로드 성공"
else
    print_error "플러그인 로드 실패"
    print_error "수동으로 'ddoc plugins-info'를 실행하여 확인하세요."
fi

echo ""

################################################################################
# Phase 11: 설치 완료 및 다음 단계
################################################################################

print_header "Phase 11: 설치 완료"

echo -e "${GREEN}✅ 환경 설정이 완료되었습니다!${NC}"
echo ""

print_info "설치된 패키지:"
echo "  - ddoc ($(pip show ddoc | grep Version | cut -d' ' -f2))"
echo "  - ddoc-plugin-vision ($(pip show ddoc-plugin-vision | grep Version | cut -d' ' -f2 2>/dev/null || echo 'N/A'))"
echo "  - ddoc-plugin-yolo ($(pip show ddoc-plugin-yolo | grep Version | cut -d' ' -f2 2>/dev/null || echo 'N/A'))"
echo "  - dvc ($(dvc --version 2>/dev/null | cut -d' ' -f2 || echo 'N/A'))"
echo ""

print_info "가상환경 위치: $VIRTUAL_ENV"
echo ""

print_header "다음 단계"

echo "환경이 성공적으로 설정되었습니다. 다음 명령어로 테스트를 진행하세요:"
echo ""
echo -e "${CYAN}  # 1. 가상환경 활성화 (새 터미널에서)${NC}"
echo "  cd $PROJECT_ROOT"
echo "  source venv/bin/activate"
echo ""
echo -e "${CYAN}  # 2. 테스트 스크립트 실행${NC}"
echo "  ./ddocintegration_test_dataprocess.sh"
echo ""
echo -e "${CYAN}  # 3. 수동 테스트 (선택)${NC}"
echo "  ddoc --help"
echo "  ddoc plugins-info"
echo "  ddoc dataset list"
echo ""

print_info "설치된 환경을 사용하려면 항상 가상환경을 활성화하세요:"
echo "  source venv/bin/activate"
echo ""

################################################################################
# 종료
################################################################################

print_header "환경 설정 스크립트 종료"
print_step "성공적으로 완료되었습니다!"

