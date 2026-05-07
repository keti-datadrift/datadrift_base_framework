# syntax=docker/dockerfile:1

# ============================================
# Stage 1: ddoc core + plugin wheel 빌드
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /build

# 빌드 도구 설치
RUN pip install --no-cache-dir build wheel

# ddoc core wheel 생성 (workspace 통합에 필요)
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
# PyTorch CPU-only first (avoids NVIDIA CUDA deps on ARM64)
COPY ./backend/requirements.txt .
RUN pip install --no-cache-dir --timeout 180 \
        torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir --timeout 180 -r requirements.txt \
    && pip install --no-cache-dir /tmp/wheels/*.whl \
    && rm -rf /tmp/wheels

# 앱 코드 복사
COPY ./backend/app ./app

# 데이터 저장 디렉토리 생성
RUN mkdir -p /app/dvc_storage /workspaces /mlruns

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
