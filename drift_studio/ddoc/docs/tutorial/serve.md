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

## Browser GUI (Round 15)

`ddoc serve` 가 띄운 그 서버의 루트(`/`) 에 vanilla HTML/JS GUI 가
같이 service 됩니다. 별도 npm / 빌드 단계 없이 wheel 안에 그대로
embed.

```bash
ddoc serve         # http://127.0.0.1:8765
# 그대로 브라우저로 열기
```

### 6 tabs (CLI 1-to-1)

| Tab | 호출 endpoint | 비고 |
|---|---|---|
| Analyze drift | `POST /analyze/drift` (또는 `…/stream`) | "Use streaming" 체크 시 SSE 진행 chip |
| Analyze EDA | `POST /analyze/eda` | snapshot / path / workspace 모드 모두 |
| Examples | `POST /examples/generate` | 4 modality × 2 scenario, 즉시 toy 생성 |
| Report | `POST /report/render` | HTML / PDF / Markdown |
| Export | `POST /export/drift-report` | file / keti_veritas / 플러그인 |
| Fetch | `POST /fetch` | file:// 기본, plugin scheme 지원 |

### 핵심 기능

- **CLI hint panel** (form 우측). 사용자가 form 채우는 동안 동등한
  `ddoc …` 명령어가 실시간으로 표시됨. `Copy` 버튼으로 클립보드에 즉시.
  GUI 가 CLI 를 *대체* 하지 않고 *학습 곡선을 낮춤*.
- **Live validation**. 필수 필드, detector 가 `/plugins/detectors`
  registry 에 있는지, JSON config 가 valid 인지 등 client-side 에서
  먼저 chip 으로 표시.
- **Drift SSE 스트림**. "Use streaming" 체크 시 `POST /analyze/drift/
  stream` 으로 갈아타서 NDJSON progress event 를 chip 으로 흘려보내고,
  마지막 `result` event 가 envelope 채움.
- **Auth**. 서버가 `DDOC_API_KEY` 와 함께 시작되면 헤더에
  `X-API-Key` 입력 필드가 노출됨. 입력값은 localStorage 에 캐싱되어
  새로고침해도 유지.
- **Result panel**. JSON envelope pretty-print + drift / EDA 결과면
  "Download envelope" 버튼.

### 화면 구성

```
┌─ ddoc serve · v2.1.0 · 4 plugins · auth: OFF       Swagger /docs ──┐
├─ [Drift] [EDA] [Examples] [Report] [Export] [Fetch] ───────────────┤
│  ┌─ form (left, 2/3) ──────┐  ┌─ Generated CLI command ─────────┐ │
│  │ data-path-ref: [____]   │  │ ddoc analyze drift \            │ │
│  │ data-path-cur: [____]   │  │   --data-path-ref /tmp/ref \    │ │
│  │ detector: [default▾]    │  │   --data-path-cur /tmp/cur \    │ │
│  │ ☑ quiet  ☐ Use streaming│  │   --detector default --json \   │ │
│  │ [Submit]                │  │   --quiet                       │ │
│  └─────────────────────────┘  │ [Copy]                          │ │
│                               └─────────────────────────────────┘ │
│  ┌─ Result (full width, expand on submit) ────────────────────────┐ │
│  │ HTTP 200 OK  [Download envelope]                               │ │
│  │ progress chips: [start 5%] [plugin_call 20%] [merge 90%] [done]│ │
│  │ {"modality":"timeseries","overall_score":0.282,...}            │ │
│  └────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

### Round-16 추가

- **Result viz** — drift / EDA envelope 이 도착하면 raw JSON 이 아니라
  modality 카드 (overall_score, status, attribute drift bars) 형태로
  먼저 표시됨. raw JSON 은 `<details>` 로 접혀 보존.
- **Multi-modal fusion** — `fused_score` 가 있는 envelope 에는 fusion
  카드가 추가로 표시 (strategy, weights, warnings).
- **Recipe envelope** — `ddoc recipe run --json` 의 결과를 GUI 에 붙여
  넣으면 step 별 상태 카드 표시.
- **한국어 i18n** — 우측 상단 토글 (또는 `?lang=ko` 쿼리). localStorage
  에 캐싱. CLI 옵션명은 (CLI 와 1대1 매핑이라) 영문 유지.

### Round-17+ 후속

- modality 별 결과 시각화 심화 (vision: 썸네일, text: 단어 통계,
  audio: 파형, timeseries: 라인 차트 — 차트 라이브러리 도입 검토)
- GUI 에서 직접 recipe 작성 / 실행 (Round 16 의 `ddoc recipe` 와 결합)
- vis plugin 의 DVC-centric tab 점진 이관

브라우저 우측 위 `Swagger /docs` 링크는 자동 생성된 OpenAPI 문서로
이어집니다 — endpoint signature / Pydantic schema 직접 확인 가능.
