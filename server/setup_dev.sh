#!/bin/bash
# =============================================================================
# 개발 환경 설정 스크립트
# 
# 사용법:
#   ./setup_dev.sh              # 기본 설정 (심볼릭 링크)
#   ./setup_dev.sh --copy       # 파일 복사 방식
#   ./setup_dev.sh --submodule  # Git submodule 방식 (원격 저장소 필요)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DDOC_PLUGIN_SRC="${SCRIPT_DIR}/../../ddoc/plugins/ddoc-plugin-vision"
DDOC_PLUGIN_DST="${SCRIPT_DIR}/ddoc-plugin-vision"

MODE="${1:-symlink}"

echo "🚀 개발 환경 설정 시작..."

# =============================================================================
# 1. ddoc-plugin-vision 설정
# =============================================================================

if [ "$MODE" = "--submodule" ]; then
    echo "📦 Git Submodule 방식으로 설정..."
    echo "   ⚠️  원격 저장소 URL이 필요합니다."
    echo "   다음 명령어를 직접 실행하세요:"
    echo ""
    echo "   cd ${SCRIPT_DIR}"
    echo "   git submodule add <repository-url> ddoc-plugin-vision"
    echo ""
    exit 0

elif [ "$MODE" = "--copy" ]; then
    echo "📋 파일 복사 방식으로 설정..."
    
    if [ ! -d "$DDOC_PLUGIN_SRC" ]; then
        echo "❌ 소스 경로를 찾을 수 없습니다: $DDOC_PLUGIN_SRC"
        exit 1
    fi
    
    rm -rf "$DDOC_PLUGIN_DST"
    cp -r "$DDOC_PLUGIN_SRC" "$DDOC_PLUGIN_DST"
    echo "✅ 복사 완료: $DDOC_PLUGIN_DST"

else
    echo "🔗 심볼릭 링크 방식으로 설정..."
    
    if [ ! -d "$DDOC_PLUGIN_SRC" ]; then
        echo "❌ 소스 경로를 찾을 수 없습니다: $DDOC_PLUGIN_SRC"
        echo "   경로를 확인하거나 --copy 옵션을 사용하세요."
        exit 1
    fi
    
    rm -rf "$DDOC_PLUGIN_DST"
    ln -s "$DDOC_PLUGIN_SRC" "$DDOC_PLUGIN_DST"
    echo "✅ 심볼릭 링크 생성: $DDOC_PLUGIN_DST -> $DDOC_PLUGIN_SRC"
fi

# =============================================================================
# 2. Python 가상환경 및 의존성 설치 (선택)
# =============================================================================

if [ -d "${SCRIPT_DIR}/venv" ]; then
    echo "📌 기존 가상환경 발견: ${SCRIPT_DIR}/venv"
else
    echo "💡 가상환경을 생성하려면:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate"
fi

echo ""
echo "📌 다음 단계:"
echo "   1. 가상환경 활성화: source venv/bin/activate"
echo "   2. 의존성 설치: pip install -r backend/requirements.txt"
echo "   3. ddoc-plugin-vision 설치: pip install -e ddoc-plugin-vision"
echo "   4. 또는 Docker 빌드: docker-compose build"
echo ""
echo "✅ 개발 환경 설정 완료!"


