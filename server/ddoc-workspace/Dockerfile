# syntax=docker/dockerfile:1

# ============================================
# Stage 1: ddoc 및 플러그인 wheel 빌드
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /build

# pip 타임아웃 및 재시도 설정 (네트워크 안정성 향상)
ENV PIP_DEFAULT_TIMEOUT=300
ENV PIP_RETRIES=5

# 빌드 도구 및 setuptools 설치
RUN pip install --no-cache-dir build wheel setuptools>=61.0

# PyPI 미러 설정 (Kakao - 한국에서 빠름)
# ⚠️ Kakao 미러에 일부 패키지(fpdf 등)가 없어 기본 PyPI 사용
# RUN pip config set global.index-url https://mirror.kakao.com/pypi/simple && \
#     pip config set global.trusted-host mirror.kakao.com

# ddoc core 소스 복사 및 wheel 생성
COPY ./ddoc /build/ddoc
RUN cd /build/ddoc && \
    python -m build --wheel --outdir /build/wheels --no-isolation

# ddoc-plugin-vision wheel 생성
RUN cd /build/ddoc/plugins/ddoc-plugin-vision && \
    python -m build --wheel --outdir /build/wheels --no-isolation

# ddoc-plugin-yolo wheel 생성
RUN cd /build/ddoc/plugins/ddoc-plugin-yolo && \
    python -m build --wheel --outdir /build/wheels --no-isolation


# ============================================
# Stage 2: 런타임 이미지
# ============================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# pip 타임아웃 및 재시도 설정
ENV PIP_DEFAULT_TIMEOUT=300
ENV PIP_RETRIES=5

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

# pip 업그레이드 및 설정
RUN pip install --upgrade pip && \
    pip config set global.timeout 300 && \
    pip config set global.retries 5 && \
    pip config set global.default-timeout 300

# PyPI 미러 설정 (Kakao - 한국에서 빠름)
# ⚠️ Kakao 미러에 일부 패키지(fpdf 등)가 없어 기본 PyPI 사용
# RUN pip config set global.index-url https://mirror.kakao.com/pypi/simple && \
#     pip config set global.trusted-host mirror.kakao.com

# ddoc wheel 파일 복사
COPY --from=builder /build/wheels/*.whl /tmp/wheels/

# Python 의존성 설치 (재시도 로직 포함)
COPY ./ddoc-workspace/requirements.txt .
RUN for i in 1 2 3; do \
        pip install --no-cache-dir --timeout=300 --retries=5 -r requirements.txt && \
        break || (echo "⚠️  Attempt $i failed, retrying in 10s..." && sleep 10); \
    done && \
    pip install --no-cache-dir /tmp/wheels/*.whl && \
    rm -rf /tmp/wheels

# 앱 코드 복사
COPY ./ddoc-workspace/app ./app

# 데이터 저장 디렉토리 생성
RUN mkdir -p /workspaces /mlruns /dvc_storage

EXPOSE 5000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
