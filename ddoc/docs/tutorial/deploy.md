# `ddoc serve` — production deploy

Round-18 — `ddoc serve` 를 실 운영에 띄우기 위한 패턴. dev 모드 (Round
14) 의 `ddoc serve --port 8765` 위에 TLS / 리버스 프록시 / Docker /
systemd 를 더해서 그대로 ship 가능한 구성으로.

기본 보안 모델:

* `DDOC_API_KEY` 환경변수로 X-API-Key 헤더 검사 활성화
* 비루프백 바인딩 시 반드시 API 키 + TLS
* `/healthz`, `/` 는 인증 우회 (모니터/health-check 친화)
* 외부 노출 시 reverse proxy 뒤로 (TLS / rate-limit / IP allowlist)

---

## 1. 가장 단순 — uvicorn TLS 직접

`uvicorn` 옵션을 통해 TLS 가능 (작은 internal 환경에 적합):

```bash
DDOC_API_KEY=<long-random-string> \
  uvicorn ddoc.server.app:create_app \
    --factory \
    --host 0.0.0.0 --port 8443 \
    --ssl-certfile /etc/ssl/ddoc/cert.pem \
    --ssl-keyfile  /etc/ssl/ddoc/key.pem
```

> `ddoc serve` 는 uvicorn 을 부모 프로세스로 spawn 하지만 TLS 직접
> 옵션을 노출하지 않음 — 운영에선 위처럼 uvicorn 직접 호출이
> 명시적이고 디버깅하기 좋음.

자체 서명 인증서 빠른 생성:

```bash
openssl req -x509 -newkey rsa:4096 -days 365 -nodes \
  -subj "/CN=ddoc.local" \
  -keyout /etc/ssl/ddoc/key.pem -out /etc/ssl/ddoc/cert.pem
```

---

## 2. nginx 리버스 프록시 뒤

권장 운영 형태 — TLS termination + 로깅 + rate limit + 보안 헤더를
nginx 가 담당, ddoc 은 localhost 에서 plain HTTP.

```nginx
# /etc/nginx/sites-available/ddoc.conf

upstream ddoc_serve {
    server 127.0.0.1:8765;
    keepalive 8;
}

server {
    listen 443 ssl http2;
    server_name ddoc.your-org.example.com;

    ssl_certificate     /etc/letsencrypt/live/ddoc.your-org.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ddoc.your-org.example.com/privkey.pem;
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_prefer_server_ciphers off;

    # Recommended baseline headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Optional IP allowlist (uncomment for closed deployments)
    # allow 10.0.0.0/8;
    # allow 192.168.0.0/16;
    # deny all;

    # SSE friendly: disable buffering for /analyze/drift/stream and /recipe/run/stream
    location ~ ^/(analyze/drift|recipe/run)/stream$ {
        proxy_pass http://ddoc_serve;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_read_timeout 1h;       # long-running drift / recipe runs
        proxy_set_header X-Real-IP        $remote_addr;
        proxy_set_header X-Forwarded-For  $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://ddoc_serve;
        proxy_http_version 1.1;
        proxy_set_header X-Real-IP        $remote_addr;
        proxy_set_header X-Forwarded-For  $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 10m;
    }
}

server {
    listen 80;
    server_name ddoc.your-org.example.com;
    return 301 https://$host$request_uri;
}
```

ddoc 자체는 그대로 localhost-only:

```bash
DDOC_API_KEY=<long-random> ddoc serve --host 127.0.0.1 --port 8765
```

---

## 3. Caddy (자동 HTTPS, 더 단순)

```caddyfile
ddoc.your-org.example.com {
    reverse_proxy 127.0.0.1:8765 {
        # SSE: long-poll friendly
        flush_interval -1
        transport http {
            read_timeout 1h
        }
    }

    encode gzip
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}
```

---

## 4. Dockerfile

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.14-slim

# System deps for weasyprint (PDF rendering); optional — drop if you
# don't render PDFs server-side.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libcairo2 libpango-1.0-0 libpangoft2-1.0-0 fonts-noto-cjk \
 && rm -rf /var/lib/apt/lists/*

# Install ddoc + the modality plugins your team uses. Trim as needed.
RUN pip install --no-cache-dir 'ddoc[ingest,test]' \
                              'ddoc-plugin-timeseries' \
                              'ddoc-plugin-audio'

# Don't run as root.
RUN useradd --system --create-home --uid 1000 ddoc
USER ddoc
WORKDIR /home/ddoc

EXPOSE 8765
CMD ["ddoc", "serve", "--host", "0.0.0.0", "--port", "8765"]
```

`docker-compose.yml` (TLS 는 nginx 컨테이너가 담당):

```yaml
version: "3"
services:
  ddoc:
    build: .
    image: ddoc-serve:latest
    environment:
      DDOC_API_KEY: ${DDOC_API_KEY}
    expose:
      - "8765"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/healthz', timeout=2)"]
      interval: 30s
      timeout: 5s
      retries: 3
  nginx:
    image: nginx:alpine
    ports: ["443:443", "80:80"]
    volumes:
      - ./nginx/ddoc.conf:/etc/nginx/conf.d/ddoc.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on: [ddoc]
    restart: unless-stopped
```

---

## 5. systemd (Docker 없이)

```ini
# /etc/systemd/system/ddoc-serve.service
[Unit]
Description=ddoc serve — REST + GUI facade
After=network.target

[Service]
Type=simple
User=ddoc
Group=ddoc
WorkingDirectory=/var/lib/ddoc
EnvironmentFile=/etc/default/ddoc-serve
ExecStart=/opt/ddoc-venv/bin/ddoc serve --host 127.0.0.1 --port 8765
Restart=on-failure
RestartSec=5s
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ReadWritePaths=/var/lib/ddoc

[Install]
WantedBy=multi-user.target
```

`/etc/default/ddoc-serve`:

```ini
DDOC_API_KEY=<long-random-string>
# Increase if recipes / drift analyses are slow
DDOC_SERVE_DEFAULT_TIMEOUT_SEC=1800
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ddoc-serve
sudo systemctl status ddoc-serve
```

---

## 6. 보안 체크리스트

- [ ] `DDOC_API_KEY` 가 길고(32자+) 랜덤(`openssl rand -hex 32`)
- [ ] 외부 노출 시 반드시 reverse proxy 뒤 + TLS 1.2/1.3
- [ ] proxy 단에 IP allowlist (가능하면) + rate limit
- [ ] SSE endpoint (`/analyze/drift/stream`, `/recipe/run/stream`) 를
      위해 `proxy_buffering off` + 큰 read_timeout
- [ ] 컨테이너 / 서비스 비루트 사용자
- [ ] `/healthz` / `/` 는 unauthenticated 라는 점 인지 (모니터링
      친화 — 민감 정보 노출 X 확인)
- [ ] 배포 후 smoke: `curl https://ddoc.../healthz` →
      `{"status":"healthy",...}`, 인증 보호 endpoint 는 401 반환
- [ ] ddoc CLI subprocess timeout (`DDOC_SERVE_DEFAULT_TIMEOUT_SEC`)
      을 운영 워크로드에 맞춤
- [ ] log rotation — uvicorn / nginx access log 가 무한 누적되지
      않도록

---

## 7. 운영 monitoring

`ddoc serve` 는 `/healthz` 를 JSON 으로 노출:

```json
{"status":"healthy","ddoc_version":"...","plugin_count":4,"auth_enabled":true,"bind":"127.0.0.1:8765"}
```

* uptime / readiness probe: `GET /healthz` → 200
* version drift 추적: `ddoc_version` 과 `plugin_count`
* alert 규칙: 5xx 비율 > 1% 또는 `auth_enabled == false` (의도와 다른
  경우)

---

## 후속 (Round 19+)

* OAuth / 사용자 계정 (per-user API key 가 아니라 SSO)
* role-based access control (recipe 별 권한, plugin 별 권한)
* metrics endpoint (Prometheus `/metrics` plugin)
* multi-replica deployment (recipe execution 의 idempotency 검토)
