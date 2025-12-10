# syntax=docker/dockerfile:1

# ============================================
# Stage 1: ddoc-plugin-vision wheel 빌드
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /build

# pip 타임아웃 및 재시도 설정 (네트워크 안정성 향상)
ENV PIP_DEFAULT_TIMEOUT=300
ENV PIP_RETRIES=5

# 빌드 도구 및 setuptools 설치
RUN pip install --no-cache-dir build wheel setuptools>=61.0

# PyPI 미러 설정 (Kakao - 한국에서 빠름)
RUN pip config set global.index-url https://mirror.kakao.com/pypi/simple && \
    pip config set global.trusted-host mirror.kakao.com

# ddoc-plugin-vision 소스 복사 (ddoc submodule에서)
COPY ./ddoc/plugins/ddoc-plugin-vision /build/ddoc-plugin-vision

# wheel 생성
RUN cd /build/ddoc-plugin-vision && \
    python -m build --wheel --outdir /build/wheels --no-isolation


# ============================================
# Stage 2: 런타임 이미지
# ============================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# pip 타임아웃 및 재시도 설정
ENV PIP_DEFAULT_TIMEOUT=300
ENV PIP_RETRIES=5

# git 설치 (clip 패키지 설치에 필요)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# pip 업그레이드 및 설정
RUN pip install --upgrade pip && \
    pip config set global.timeout 300 && \
    pip config set global.retries 5 && \
    pip config set global.default-timeout 300

# PyPI 미러 설정 (Kakao - 한국에서 빠름)
RUN pip config set global.index-url https://mirror.kakao.com/pypi/simple && \
    pip config set global.trusted-host mirror.kakao.com

# ddoc-plugin-vision wheel 복사
COPY --from=builder /build/wheels/*.whl /tmp/wheels/

# Python 의존성 설치 (재시도 로직 포함)
COPY ./backend/requirements.txt .
RUN for i in 1 2 3; do \
        pip install --no-cache-dir --timeout=300 --retries=5 -r requirements.txt && \
        break || (echo "⚠️  Attempt $i failed, retrying in 10s..." && sleep 10); \
    done && \
    pip install --no-cache-dir /tmp/wheels/*.whl && \
    rm -rf /tmp/wheels

# 앱 코드 복사
COPY ./backend/app ./app

# 데이터 저장 디렉토리 생성
RUN mkdir -p /app/dvc_storage

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
