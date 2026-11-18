# `ddoc recipe` — multi-step workflows in one YAML

Round-16 — chain ddoc 의 여러 명령어를 YAML 한 파일로 묶어 한 번에
실행. CI / 스케줄 작업 / "이 4 단계 항상 같이 돌림" 워크플로의 단일
입력. gpu-tunnel `recipes/` 패턴 참조.

## 빠른 시작

세 가지 standalone 샘플 recipe 가 패키지에 동봉:

| recipe | 흐름 | 입력 |
|---|---|---|
| `recipes/timeseries_smoke.yaml` | toy 데이터 *생성* → drift → markdown report → keti-shaped JSON export | 없음 (자체 생성) |
| `recipes/csv_drift.yaml` | drift → markdown report | env: `DATA_PATH_REF`, `DATA_PATH_CUR`, `REPORT_OUT` (이미 disk 에 있는 데이터셋 분석) |
| `recipes/fetch_then_analyze.yaml` | fetch (file/http/s3) → drift → markdown report | env: `SOURCE_REF`, `SOURCE_CUR`, `WORK_ROOT` (외부 source ingest 데모) |

```bash
# 1) 자체 생성형 — 그냥 실행
ddoc recipe run recipes/timeseries_smoke.yaml

# 2) 본인 데이터로
DATA_PATH_REF=/path/to/ref \
DATA_PATH_CUR=/path/to/cur \
REPORT_OUT=/tmp/drift.md \
ddoc recipe run recipes/csv_drift.yaml

# 3) URL/file 에서 ingest 후 분석
SOURCE_REF=file:///abs/ref \
SOURCE_CUR=file:///abs/cur \
WORK_ROOT=/tmp/ddoc_fta \
ddoc recipe run recipes/fetch_then_analyze.yaml
```

검증 + dry-run 도 단일 recipe 별로:

```bash
ddoc recipe validate recipes/timeseries_smoke.yaml
ddoc recipe run recipes/timeseries_smoke.yaml --dry-run
```

> dry-run 은 *env-only* substitution 만 해소합니다. `${steps.X.json.path}`
> 처럼 *이전 step 의 결과* 를 참조하는 recipe (예: `fetch_then_analyze.yaml`)
> 는 dry-run 에서 의도적으로 실패합니다 — runtime 에서만 체인이
> 채워지기 때문.

## 스키마

```yaml
name: <human label, optional>
description: <multi-line, optional>
workspace: <auto-envelope 저장 dir, optional — 기본은 recipe 옆에
            .ddoc-recipe-out/<recipe stem>/>
vars:
  <key>: <value>            # ${vars.<key>} 로 step 안에서 참조
steps:
  - id: <unique per recipe>
    run: <kind>             # 아래 표 참조
    with:                   # ddoc CLI 옵션을 1대1 매핑
      <option>: <value>
    out: <optional explicit output path>
```

### 지원 step kind

| `run` | ddoc CLI 매핑 | 주요 `with` 키 |
|---|---|---|
| `fetch` | `ddoc fetch` | `dest`, `symlink`, `config` |
| `examples.generate` | `ddoc examples generate` | `out`, `scenario` |
| `analyze.eda` | `ddoc analyze eda` | `data_path`, `quiet` 등 |
| `analyze.drift` | `ddoc analyze drift` | `data_path_ref/cur`, `detector`, `fusion`, `quiet` |
| `report.render` | `ddoc report render` | `input`, `out`, `format`, `title` |
| `export.drift_report` | `ddoc export drift-report` | `target`, `config` |

`ddoc recipe kinds` 로 항상 최신 목록 확인 가능.

### 참조 (substitution) 문법

`with` 의 값과 `out` 필드 안에서 다음 placeholder 가 인식됨:

| 형태 | 의미 |
|---|---|
| `${vars.<name>}` | recipe 의 `vars` 섹션 |
| `${env.<NAME>}` | 프로세스 환경변수 |
| `${steps.<id>.output}` | 이전 step 의 산출 path (자동 추론) |
| `${steps.<id>.json}` | 이전 step 의 JSON envelope (객체 그대로) |
| `${steps.<id>.json.<dotted>}` | envelope 안의 dotted path 값 |

전체 문자열이 단일 placeholder 면 타입 보존 (envelope dict 가 그대로
넘어감). 부분 치환은 문자열로 변환.

### Auto envelope persistence

`analyze.drift` 와 `analyze.eda` 같이 stdout 으로 envelope 만 내보내는
step 들은 자동으로 `<workspace>/<step_id>.envelope.json` 에 atomic
저장됨. 따라서 후속 step 이 `${steps.drift.output}` 만으로 결과 파일
경로를 받을 수 있음 (별도 "save to file" step 불필요).

명시적 `out:` 을 step 에 두면 그 경로가 우선.

## 실행 contract

* 첫 실패 step 에서 정지 — error envelope 을 결과의 `error` 필드로
  bubble.
* `--json` 출력은 `{status, recipe, steps: [...]}` 형태로 모든 step
  결과 포함.
* `--dry-run` 은 substitution 까지 다 해소한 argv 만 출력하고 실제
  ddoc 호출은 건너뜀 — recipe 디버깅에 유용.

## YAML 작성 팁

`with` 안에서 `${...}` 를 쓸 때는 인라인 mapping (`{ key: value }`)
대신 block mapping 으로 풀어 쓰는 편이 안전:

```yaml
# ❌ flow-mapping 안의 ${} 는 YAML parser 가 nested map 으로 오해
with: { out: ${vars.x}, scenario: shifted }

# ✅ block mapping 또는 명시적 quote
with:
  out: ${vars.x}
  scenario: shifted

# ✅ 또는
with: { out: "${vars.x}", scenario: shifted }
```

## REST API 와의 관계

레시피는 CLI 우선 — `ddoc recipe run` 이 메인 path. `ddoc serve` 의
신규 GUI 안에서 한 번에 실행하는 multi-step 통합은 Round-17+ 후속.
이미 GUI 의 result viz 패널은 `{status, recipe, steps: [...]}` 형태의
envelope 을 카드 + 단계 목록으로 표시.

## REST endpoints (Round 17)

`ddoc serve` 띄우면 동일한 동작이 HTTP 로 노출됨:

| Method | Path | 설명 |
|---|---|---|
| POST | `/recipe/validate` | 본문 `{yaml: "..."}` 또는 `{path: "..."}`. 파싱 + 구조 검증만. |
| POST | `/recipe/run` | 동기 실행. `dry_run: true` 도 지원. |
| POST | `/recipe/run/stream` | SSE: `event: progress` per step + `event: result` 마지막. |

```bash
# 인라인 YAML 검증
curl -s -X POST http://localhost:8765/recipe/validate \
  -H 'Content-Type: application/json' \
  -d '{"yaml": "name: tiny\nsteps:\n  - id: a\n    run: examples.generate\n    with: { modality: timeseries, out: /tmp/x, scenario: shifted }"}'
# → {"status":"ok","recipe":"tiny","step_count":1,"issues":[]}

# 실제 실행 (서버 측 path)
curl -s -X POST http://localhost:8765/recipe/run \
  -H 'Content-Type: application/json' \
  -d '{"path": "recipes/timeseries_smoke.yaml"}'

# 스트리밍 진행 표시
curl -N -X POST http://localhost:8765/recipe/run/stream \
  -H 'Content-Type: application/json' -H 'Accept: text/event-stream' \
  -d '{"path": "recipes/timeseries_smoke.yaml"}'
```

## Conditional step — `when:` (Round 17)

각 step 에 optional `when:` 표현식을 붙여 조건부 실행:

```yaml
steps:
  - id: drift
    run: analyze.drift
    with: { ... }
  - id: heavy_report
    run: report.render
    when: "${steps.drift.json.overall_score} > 0.25"
    with: { ... }
```

조건이 거짓이면 step 의 결과에 `skipped: true, skipped_reason: "when"`
이 표시됨. 평가기는 안전한 mini-eval — 리터럴 (number / string / bool /
null), 비교 (`==`, `!=`, `<`, `<=`, `>`, `>=`), 불 연산 (`and`, `or`,
`not`), 단항 (+/-), 괄호만 허용. `Name` / `Call` / `Attribute` 같은
임의 평가는 거부 (보안).

## GUI Recipe tab (Round 17)

`ddoc serve` 의 7번째 탭 `Recipe` 에서 :
* YAML 텍스트 편집 (default 로 샘플 시나리오 포함)
* 또는 server-side path 모드
* `dry-run`, `validate only`, `Use streaming` 토글
* SSE 모드 시 step 별 chip (`gen_pair (examples.generate) — ok`,
  `report_md (report.render) — skip·when`) 누적
* 결과 패널이 recipe envelope 을 카드로 시각화 (Round 16 의 viz 와
  연결)

## Parallel block — `parallel:` (Round 18)

독립 step 들을 동시 실행:

```yaml
steps:
  - id: pre
    run: fetch
    with: { source_uri: file:///mnt/share/audit, dest: /tmp/audit }

  - parallel:
      - id: drift_a
        run: analyze.drift
        with: { data_path_ref: /tmp/audit/site_a/ref, data_path_cur: /tmp/audit/site_a/cur, quiet: true }
      - id: drift_b
        run: analyze.drift
        with: { data_path_ref: /tmp/audit/site_b/ref, data_path_cur: /tmp/audit/site_b/cur, quiet: true }

  - id: report
    run: report.render
    with: { input: "${steps.drift_a.output}", out: /tmp/audit/report.html, format: html }
```

* parallel block 의 자식 step 들은 *동일 ctx 스냅샷* (block 직전 상태)
  을 공유 — 형제 step 끼리는 서로 참조 불가.
* block 종료 시 모든 자식의 결과가 ctx 에 merge → 후속 직렬 step 이
  자유롭게 `${steps.<child_id>.json/output}` 참조.
* 어느 자식이 실패해도 나머지는 끝까지 실행 (디버깅 친화). 첫 실패의
  envelope 이 결과의 `error` 필드로 bubble.
* `dry_run` 도 parallel 그대로 처리 (substitution 만 해소된 argv 출력).

## Library (Round 19) — `/recipes` 엔드포인트

`ddoc serve` 가 디렉터리의 YAML 들을 카탈로그로 노출:

```bash
# 디폴트는 패키지에 동봉된 recipes/ — DDOC_RECIPES_DIR env 로 사이트별
# 디렉터리 지정 가능
DDOC_RECIPES_DIR=/srv/ddoc/recipes ddoc serve

# 목록
curl -s localhost:8765/recipes | jq
# → {"library_dir":"/srv/ddoc/recipes","count":3,"recipes":[
#     {"name":"timeseries_smoke","display_name":"timeseries-drift-smoke","step_count":4,...},
#     ...
#   ]}

# 한 건 (YAML + validation issues)
curl -s localhost:8765/recipes/timeseries_smoke | jq
```

URL slug 는 파일 stem (`timeseries_smoke.yaml` → `/recipes/timeseries_smoke`).
recipe 의 `name:` 필드는 `display_name` 으로 별도 보존.

## Library write + versioning (Round 20)

라이브러리는 기본은 read-only. `DDOC_RECIPES_WRITE=1` 환경변수가
설정된 경우만 write 모드 활성화 — 검증 통과 후 atomic 으로 저장하고,
같은 이름이 이미 있으면 덮기 *직전* 의 내용을 자동 스냅샷.

```bash
DDOC_RECIPES_DIR=/srv/ddoc/recipes DDOC_RECIPES_WRITE=1 ddoc serve

# 저장 (검증 통과 → 파일 작성, 기존 있으면 .history/<name>/<UTC ts>.yaml 로 archive)
curl -s -X PUT http://localhost:8765/recipes/demo \
  -H 'Content-Type: application/json' \
  -d '{"yaml":"name: demo\nsteps:\n  - id: g\n    run: examples.generate\n    with: { modality: timeseries, out: /tmp/x, scenario: shifted }\n"}' | jq
# → {"status":"ok","name":"demo","path":"/srv/.../demo.yaml","archived_to":null,...}

# 두 번째 저장 — archived_to 가 채워짐
curl -s -X PUT ... | jq '.archived_to'
# → "/srv/.../.history/demo/20260508T234810Z.yaml"

# 버전 목록
curl -s http://localhost:8765/recipes/demo/versions | jq
# → {"name":"demo","count":1,"versions":[{"timestamp":"20260508T234810Z",...}]}

# 한 시점의 YAML
curl -s http://localhost:8765/recipes/demo/versions/20260508T234810Z | jq -r .yaml
```

규칙:

* write 모드가 꺼진 상태에서 PUT → `403 library_read_only`.
* recipe 이름은 `^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$` regex. `..`, `/`,
  공백 등 path-traversal 위험 문자는 거절.
* validation 실패 (`Recipe.load` 또는 `recipe.validate()` 가 issues
  반환) 시 *파일 미저장* + in-band `{status:"error", error_code:
  "validation_failed", issues:[...]}`.
* archive 디렉터리 (`.history/`) 는 listing API 에서 노출되지 않음 —
  hidden prefix 로 스킵.
* git 백엔드 versioning 은 별도 deploy 옵션 (현재 라운드는 plain
  파일).

## GUI Recipe library dropdown (Round 20)

`ddoc serve` 의 Recipe 탭에 **Load from library** dropdown 추가:

* page 첫 진입 시 `/recipes` 한 번 fetch → option list 채움.
* 선택 시 `/recipes/<name>` 으로 YAML 가져와 textarea 에 prefill.
* `library_read_only: false` 인 경우 (서버가 `DDOC_RECIPES_WRITE=1`
  로 띄워졌을 때) `Save to library` 버튼이 actions row 옆에 노출 —
  현재 textarea 내용을 PUT 으로 저장.
* 저장 성공 시 dropdown 을 자동으로 reload.

## CRUD 마무리: delete / restore / diff (Round 21)

write 모드에서 라이브러리 풀-CRUD 를 노출. 모든 destructive 동작은
삭제/덮기 *직전* 의 콘텐츠를 `.history/<name>/<UTC ts>.yaml` 로 자동
archive — Round 20 의 versioning 위에서 reversibility 를 보장.

```bash
DDOC_RECIPES_DIR=/srv/ddoc/recipes DDOC_RECIPES_WRITE=1 ddoc serve

# Delete — 활성 파일을 .history/ 로 옮기고 active 는 unlink
curl -s -X DELETE http://localhost:8765/recipes/demo | jq
# → {"status":"ok","name":"demo","deleted_path":"/srv/.../demo.yaml",
#    "archived_to":"/srv/.../.history/demo/<ts>.yaml"}

# Restore — 한 시점 snapshot 으로 active 복원 (현재 active 도 archive)
TS=$(curl -s localhost:8765/recipes/demo/versions | jq -r '.versions[0].timestamp')
curl -s -X POST http://localhost:8765/recipes/demo/restore/$TS | jq
# → {"status":"ok","restored_from":"...","archived_to":"...","path":"..."}

# Diff — 두 ref 의 unified-diff. 기본은 HEAD vs 가장 최근 snapshot.
curl -s 'http://localhost:8765/recipes/demo/diff' | jq -r .diff
curl -s 'http://localhost:8765/recipes/demo/diff?from=HEAD&to=20260509T013808Z' | jq -r .diff
```

규칙:

* `DELETE` / `POST .../restore/{ts}` 둘 다 `DDOC_RECIPES_WRITE=1`
  필요. 미설정 → `403 library_read_only`.
* Restore 의 `ts` 는 `.history/<name>/` 에 실제 존재해야 함 →
  `404 version_not_found`.
* Diff 의 `from` / `to` 는 `HEAD` 또는 snapshot 의 timestamp.
  ref 가 second-단위로 충돌하면 archive 가 `<ts>-1.yaml`,
  `<ts>-2.yaml` 식으로 suffix 를 붙여 보존.
* Diff 의 default `to` 는 가장 최근 snapshot. snapshot 이 하나도
  없으면 `{diff:"", note:"no snapshots yet"}`.
* Diff `from==to` (예: `HEAD vs HEAD`) → `{identical:true, diff:""}`.

GUI Recipe 탭의 actions row 에 write 모드일 때만 노출되는 mini-
controls: **Save to library** / **Compare** (HEAD vs latest) /
**Restore latest** / **Delete**. Restore 와 Delete 는 confirm
dialog 로 한번 더 묻고, Delete 는 빨간 outline 으로 시각 구분.

## Write-token gating (Round 22)

write 모드는 단순한 boolean toggle 외에, optional secret 으로
한층 게이트할 수 있음. 이 패턴은 *anonymous read + token-gated
write* 시나리오 (사이트 운영자만 라이브러리 수정 가능, 읽기는 누구나)
에 유용.

```bash
DDOC_RECIPES_DIR=/srv/ddoc/recipes \
DDOC_RECIPES_WRITE=1 \
DDOC_RECIPES_WRITE_TOKEN=$(openssl rand -hex 16) \
ddoc serve

# 토큰 없이 PUT → 401
curl -s -X PUT http://localhost:8765/recipes/foo \
  -H 'Content-Type: application/json' -d '{"yaml":"…"}'
# → {"detail":{"error_code":"invalid_write_token", ...}}

# 토큰 헤더 첨부 → 200
curl -s -X PUT http://localhost:8765/recipes/foo \
  -H 'X-Recipes-Write-Token: <secret>' \
  -H 'Content-Type: application/json' -d '{"yaml":"…"}'
```

규칙:

* 토큰 미설정 (`DDOC_RECIPES_WRITE_TOKEN` env 없음) → 기존과
  동일하게 `DDOC_RECIPES_WRITE=1` 만 통과하면 write 가능.
* 토큰 설정 → write 4 endpoint (`PUT`, `DELETE`,
  `POST .../restore/{ts}`) 에 한해 `X-Recipes-Write-Token` 헤더 검증.
  read 엔드포인트는 영향 없음 (`/recipes`, `/recipes/{name}`,
  `/versions`, `/diff`).
* `GET /recipes` 와 `GET /recipes/{name}` 응답에 새 boolean 필드
  `write_token_required` 가 포함 → GUI 가 input 박스 노출 여부 판단.
* 토큰 검증 실패 → `401 invalid_write_token` envelope.
* `DDOC_API_KEY` (전역 헤더 인증) 와 *and* 관계 — 둘 다 설정되면
  write 요청은 두 헤더 모두 통과해야 함.

GUI 의 Recipe 탭에서는 서버가 토큰을 요구하면 actions row 아래에
**write token** password-style 입력박스가 자동 노출되고, 입력값은
`localStorage` (`ddoc_serve_write_token`) 에 캐시됨.

## Diff UI rendering (Round 22)

`GET /recipes/{name}/diff` 응답을 result panel 이 unified-diff 카드로
색상 강조 렌더:

* `+` 줄 → 녹색 배경
* `-` 줄 → 빨간 배경
* `@@ ... @@` hunk header → 보라색
* `+++` / `---` file header → 파란색

`identical: true` 인 경우 큰 글씨로 "identical" 표시.
snapshot 0 개 → "no snapshots yet" 메시지. 라이브러리 의존성 없는
순수 vanilla.

## Git-backed audit trail (Round 23)

`.history/` archive 위에 *full git history* 까지 옵션으로 켤 수 있음.
켜지면 매 PUT/DELETE/restore 후에 라이브러리 디렉터리에서 자동
`git add -A && git commit` 이 돌면서, 시간순 audit trail 이 보장됨.

```bash
DDOC_RECIPES_DIR=/srv/ddoc/recipes \
DDOC_RECIPES_WRITE=1 \
DDOC_RECIPES_GIT=1 \
ddoc serve
```

규칙:

* 첫 write 시 디렉터리에 `.git` 이 없으면 `git init` + sane default
  identity (`ddoc-serve@localhost`) 자동 부여.
* 응답 envelope 의 `git_commit` 필드에 새 SHA-1 이 노출 (실패/비활성
  시 `null`).
* `GET /git-log?limit=50` 로 최근 commit 목록 ({commit, author, date,
  subject}) 조회 가능. 자세한 diff 는 OS shell 에서 `git -C
  <library_dir> show <sha>` 로 직접.
* git 호출 실패는 *best-effort* — API request 자체는 성공 (파일은
  이미 disk 에 atomic write 됨, `.history/` archive 도 정상 유지). git
  관련 로그만 warning.
* `git_enabled: bool` 가 listing/get 응답에 포함됨 (실제로 `.git` 이
  있고 env 가 켜져 있을 때 `true`).
* `.history/` archive 와 git 은 *상호 보완* — git 이 꺼져 있어도
  `.history/` 로 모든 versioning 동작 그대로.

GUI topbar 에 `git: ON` 배지가 표시 (bootstrap 에서 `/recipes` 한 번
fetch).

## Diff UI word-level highlighting (Round 23)

기존 line-level 색상 위에, 인접한 `-`/`+` 줄 쌍에 대해 토큰 단위
LCS diff 가 추가로 실행되어 *바뀐 단어/공백 토큰만* `<mark>` 으로
강조됨. 라이브러리 의존성 0 (vanilla LCS DP).

* `+` 줄 안의 추가된 단어 → 진녹색 mark
* `-` 줄 안의 제거된 단어 → 진빨강 mark
* 컨텍스트 줄 / hunk header / file header 는 영향 없음

## Write-token rotation API (Round 24)

Round 22 의 단일 env-secret 위에 *multi-token store* 추가 — admin
이 token 을 발급/취소(rotation)할 수 있고, 모든 secret 은 disk 에는
SHA-256 해시로만 저장 (plaintext 는 발급 시 *한 번만* 응답).

```bash
DDOC_RECIPES_DIR=/srv/ddoc/recipes \
DDOC_RECIPES_WRITE=1 \
DDOC_RECIPES_ADMIN_TOKEN=$(openssl rand -hex 16) \
ddoc serve

# 발급 — secret 은 응답에 한 번만 노출
curl -s -X POST http://localhost:8765/tokens \
  -H "X-Recipes-Admin-Token: $ADMIN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"ci-runner"}' | jq
# → {"status":"ok","id":"tok_abcd1234","name":"ci-runner",
#    "scope":"write","secret":"<plaintext, save now>","created_at":"…"}

# 토큰으로 write
curl -s -X PUT http://localhost:8765/recipes/foo \
  -H "X-Recipes-Write-Token: <plaintext>" \
  -H 'Content-Type: application/json' -d '{"yaml":"…"}'

# 목록 (해시 전용, secret 노출 안 됨)
curl -s -H "X-Recipes-Admin-Token: $ADMIN" http://localhost:8765/tokens | jq

# 취소 (soft-delete; 기록은 audit 용으로 보존)
curl -s -X DELETE -H "X-Recipes-Admin-Token: $ADMIN" \
  http://localhost:8765/tokens/tok_abcd1234 | jq
```

규칙:

* **Admin closed-by-default** — `DDOC_RECIPES_ADMIN_TOKEN` 미설정 시
  `/tokens` 엔드포인트는 `403 admin_disabled`. 즉 평소 ddoc serve
  띄움이 실수로 token CRUD 를 노출하지 않음.
* **Validator 우선순위** — write 요청은 *env single-secret OR 토큰
  스토어 활성 hash* 둘 중 하나에 매칭되면 통과 (Round 22 와 backward-
  compatible).
* **Sticky gate** — 한 번이라도 `POST /tokens` 가 호출되어 `.tokens.json`
  파일이 만들어지면, 모든 토큰을 취소해도 *anonymous write 로 돌아가지
  않음*. 다시 쓰려면 새 토큰을 발급해야 함 (실수 fail-open 방지).
* **No plaintext on disk** — 저장은 `{id, name, scope, secret_hash,
  created_at, revoked_at}`. plaintext 는 발급 응답이 유일.
* **GUI** — 별도 관리 패널 없음 (드물게 사용되는 admin 기능).
  `STATE.adminToken` 이 localStorage 에 캐시되고 `authHeaders()` 가
  `X-Recipes-Admin-Token` 자동 첨부 → 브라우저 콘솔에서
  `await fetch('/tokens', ...)` 로도 admin 작업 가능.

## 후속 (Round 25+)

* `with` 안의 표현식 확장 (`${steps.x.json | length}` 같은 filter)
* parallel + recipe library 의 multi-recipe orchestrator
* `git show <sha>` 결과를 GUI 에서 직접 렌더 (현재는 OS shell)
* per-token scope (현재는 'write' / 'admin' 단순 enum)
* token expiry (TTL) — 현재는 manual revoke 만
