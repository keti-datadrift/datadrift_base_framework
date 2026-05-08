# `ddoc serve` — REST facade in 2 minutes

Round-14 의 `ddoc serve` 명령어로 ddoc CLI 의 모든 기능을 HTTP 로
호출할 수 있습니다. curl, scripts, 외부 시스템 (keti_veritas 형제,
다른 사이트), 또는 brower 의 Swagger UI 에서 즉시 사용 가능.

## 시작

```bash
# 가벼운 실행 (localhost:8765, 인증 disable)
ddoc serve

# 다른 포트 / 외부 노출 (인증 필수)
DDOC_API_KEY=secret ddoc serve --host 0.0.0.0 --port 9000

# 개발 모드 (코드 변경 시 자동 reload)
ddoc serve --reload --log-level debug
```

브라우저로 `http://127.0.0.1:8765/docs` 열면 Swagger UI 에서 모든
엔드포인트를 직접 테스트할 수 있음.

## curl 예제

### Health & metadata

```bash
curl -s http://localhost:8765/healthz | jq
# → {"status":"healthy","ddoc_version":"2.1.0","plugin_count":4,...}

curl -s http://localhost:8765/version | jq
# → {"ddoc":"2.1.0","hookspec":"1.0.0"}
```

### Plugin 목록 + detector 매트릭스

```bash
curl -s http://localhost:8765/plugins | jq '.plugins'
curl -s http://localhost:8765/plugins/detectors | jq '.registry'
```

### CLI 명령어 introspection (GUI auto-populate 용)

```bash
curl -s http://localhost:8765/commands | jq '.tree.subcommands | keys'
# → ["analyze","examples","exp","export","fetch","plugin","report","serve",...]
```

### Toy 데이터 생성 후 drift 분석

```bash
# 1. 합성 데이터 페어 생성
curl -s -X POST http://localhost:8765/examples/generate \
  -H 'Content-Type: application/json' \
  -d '{"modality":"timeseries","out":"/tmp/demo","scenario":"shifted"}' | jq

# 2. drift 측정
curl -s -X POST http://localhost:8765/analyze/drift \
  -H 'Content-Type: application/json' \
  -d '{
    "data_path_ref": "/tmp/demo/ref",
    "data_path_cur": "/tmp/demo/cur",
    "quiet": true
  }' | jq
# → {"modality":"timeseries","overall_score":0.282,...}
```

### Streaming 진행 (SSE)

```bash
curl -N -X POST http://localhost:8765/analyze/drift/stream \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d '{
    "data_path_ref": "/tmp/demo/ref",
    "data_path_cur": "/tmp/demo/cur",
    "quiet": true
  }'
# event: progress
# data: {"progress":0.05,"stage":"start","message":"drift path mode init"}
# event: progress
# data: {"progress":0.2,"stage":"plugin_call",...}
# event: progress
# data: {"progress":0.9,"stage":"merge",...}
# event: progress
# data: {"progress":1.0,"stage":"complete",...}
# event: result
# data: {"modality":"timeseries","overall_score":0.282,...}
```

### Report 렌더 + 외부 export

```bash
# drift envelope 을 파일로 저장한 후
curl -s -X POST http://localhost:8765/analyze/drift \
  -H 'Content-Type: application/json' \
  -d '{"data_path_ref":"/tmp/demo/ref","data_path_cur":"/tmp/demo/cur","quiet":true}' \
  > /tmp/drift.json

# HTML 리포트
curl -s -X POST http://localhost:8765/report/render \
  -H 'Content-Type: application/json' \
  -d '{"input":"/tmp/drift.json","out":"/tmp/r.html","format":"html","title":"My drift report"}' | jq

# keti_veritas 로 발신
curl -s -X POST http://localhost:8765/export/drift-report \
  -H 'Content-Type: application/json' \
  -d '{
    "input": "/tmp/drift.json",
    "target": "keti_veritas",
    "config": {"base_url": "http://veritas.local:8000", "api_key": "..."}
  }' | jq
```

### 외부 데이터 fetch (file://, s3://, http(s)://, ...)

```bash
# 로컬 디렉터리 복사
curl -s -X POST http://localhost:8765/fetch \
  -H 'Content-Type: application/json' \
  -d '{"source_uri":"file:///mnt/share/audit","dest":"/tmp/audit"}' | jq

# 알려지지 않은 scheme — plugin 없으면 400 + no_adapter_for_scheme
curl -s -X POST http://localhost:8765/fetch \
  -H 'Content-Type: application/json' \
  -d '{"source_uri":"s3://bucket/key","dest":"/tmp/x"}' | jq
```

## 인증

기본은 인증 없음 (localhost-only 가정). 외부 노출 시 반드시
`DDOC_API_KEY` 설정:

```bash
DDOC_API_KEY=mysecret ddoc serve --host 0.0.0.0
```

이후 모든 호출에 `X-API-Key` 헤더 필요:

```bash
curl -H 'X-API-Key: mysecret' http://server.local:8765/plugins
```

`/healthz` 와 `/` 는 auth 우회 (모니터링 용).

## drift_studio backend 와의 차이

| | `ddoc serve` | `drift_studio/backend` |
|---|---|---|
| 기본 포트 | 8765 | 8000 |
| 범위 | ddoc CLI 의 thin facade | dataset / training / field-agent monolith |
| 의존성 | ddoc + uvicorn | + redis, celery, sqlalchemy, evidently, ... |
| 사용 사례 | curl-only / 외부 시스템 / scripted automation | 기존 frontend (React) + 사이트별 운영 |

같은 머신에서 둘 다 실행 가능 (다른 포트). 같은 ddoc CLI 를 공유하므로
결과는 byte-for-byte 동일.

## Round-15 GUI

Round 15 에서 `ddoc serve` 위에 vanilla HTML/JS GUI 를 얹을 예정 —
form builder + 실시간 결과 패널 + "생성된 CLI 명령어" 복사 버튼.
gpu-tunnel 의 `dashboard.py` 패턴 참조.
