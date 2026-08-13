# ddoc — lightweight REST service image (R-D3).
#
# Goal: minimal viable ddoc + the plugins keti_veritas needs for R1
# (camera health), R38/R40 (temporal categorical drift). Heavier
# plugins (vision/yolo) NOT included here — they belong in a separate
# image variant or host install.
#
# Build:  docker build -t ddoc-rest .
# Run:    docker run --rm -p 8000:8000 ddoc-rest
# Probe:  curl http://localhost:8000/healthz

FROM python:3.11-slim

# System deps required by weasyprint (cairo/pango) + scikit-learn build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source (build context = drift_studio/ddoc/)
COPY pyproject.toml README.md ./
COPY ddoc ./ddoc
COPY plugins ./plugins

# Install ddoc itself, then the lightweight plugin set.
# We install editable so volume-mounted source overrides take effect at
# dev time. The plugins/ subtree is also editable for the same reason.
# Lightweight plugin set — keti R1/R38/R40 use cases only.
# text/audio/timeseries pull heavy deps (CLIP from git, librosa,
# statsmodels) and live in a separate image variant.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir \
        -e plugins/ddoc-plugin-categorical \
        -e plugins/ddoc-plugin-tabular \
        -e plugins/ddoc-plugin-keti-temporal

# Sanity check at build time
RUN ddoc --version

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

# `ddoc serve` is the REST entry point (Round 14). Listen on all
# interfaces so the container is reachable from the docker network.
ENTRYPOINT ["ddoc", "serve", "--host", "0.0.0.0", "--port", "8000"]
