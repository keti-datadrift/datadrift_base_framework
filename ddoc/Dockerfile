# ddoc — REST + GUI service image built from this repository.
#
# Includes the ddoc core and the lightweight categorical / tabular
# plugins. Plugins with heavy dependencies (vision: torch + CLIP,
# text, audio, timeseries) are left out; add them to the install line
# below if you need them.
#
# Build (from the repository root):
#   docker build -f ddoc/Dockerfile -t ddoc-serve .
# Run:
#   docker run --rm -p 8765:8765 -e DDOC_API_KEY=<secret> ddoc-serve
# Probe:
#   curl http://localhost:8765/healthz

FROM python:3.11-slim

# System libraries weasyprint needs for PDF reports.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY ddoc ./ddoc
COPY plugins/ddoc-plugin-categorical ./plugins/ddoc-plugin-categorical
COPY plugins/ddoc-plugin-tabular ./plugins/ddoc-plugin-tabular

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
        ./ddoc \
        ./plugins/ddoc-plugin-categorical \
        ./plugins/ddoc-plugin-tabular \
 && ddoc --version

# Don't run as root.
RUN useradd --system --create-home --uid 1000 ddoc
USER ddoc
WORKDIR /home/ddoc

ENV PYTHONUNBUFFERED=1
EXPOSE 8765

# Listen on all interfaces so the container is reachable. Set
# DDOC_API_KEY when the port is exposed beyond localhost.
CMD ["ddoc", "serve", "--host", "0.0.0.0", "--port", "8765"]
