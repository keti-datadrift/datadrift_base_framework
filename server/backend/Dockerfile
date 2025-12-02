# syntax=docker/dockerfile:1

# ============================================
# Stage 1: ddoc-plugin-vision wheel 빌드
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /build

# 빌드 도구 설치
RUN pip install --no-cache-dir build wheel

# ddoc-plugin-vision 소스 복사 (ddoc submodule에서)
COPY ./ddoc/plugins/ddoc-plugin-vision /build/ddoc-plugin-vision

# wheel 생성
RUN cd /build/ddoc-plugin-vision && \
    python -m build --wheel --outdir /build/wheels


# ============================================
# Stage 2: 런타임 이미지
# ============================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# git 설치 (clip 패키지 설치에 필요)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# ddoc-plugin-vision wheel 복사
COPY --from=builder /build/wheels/*.whl /tmp/wheels/

# Python 의존성 설치
COPY ./backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir /tmp/wheels/*.whl && \
    rm -rf /tmp/wheels

# 앱 코드 복사
COPY ./backend/app ./app

# 데이터 저장 디렉토리 생성
RUN mkdir -p /app/dvc_storage

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
