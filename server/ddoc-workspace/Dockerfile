# syntax=docker/dockerfile:1

# ============================================
# Stage 1: ddoc 및 플러그인 wheel 빌드
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /build

# 빌드 도구 설치
RUN pip install --no-cache-dir build wheel

# ddoc core 소스 복사 및 wheel 생성
COPY ./ddoc /build/ddoc
RUN cd /build/ddoc && \
    python -m build --wheel --outdir /build/wheels

# ddoc-plugin-vision wheel 생성
RUN cd /build/ddoc/plugins/ddoc-plugin-vision && \
    python -m build --wheel --outdir /build/wheels

# ddoc-plugin-yolo wheel 생성
RUN cd /build/ddoc/plugins/ddoc-plugin-yolo && \
    python -m build --wheel --outdir /build/wheels


# ============================================
# Stage 2: 런타임 이미지
# ============================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# 시스템 의존성 설치
# git, curl: clip 패키지 및 dvc에 필요
# libgl1, libglib2.0-0, libsm6, libxext6, libxrender-dev: OpenCV/FiftyOne에 필요
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        curl \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev && \
    rm -rf /var/lib/apt/lists/*

# ddoc wheel 파일 복사
COPY --from=builder /build/wheels/*.whl /tmp/wheels/

# Python 의존성 설치
COPY ./ddoc-workspace/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir /tmp/wheels/*.whl && \
    rm -rf /tmp/wheels

# 앱 코드 복사
COPY ./ddoc-workspace/app ./app

# 데이터 저장 디렉토리 생성
RUN mkdir -p /workspaces /mlruns /dvc_storage

EXPOSE 5000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
