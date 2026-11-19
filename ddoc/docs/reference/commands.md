# 명령어 레퍼런스

모든 명령은 `--help` 로 최신 옵션을 확인할 수 있습니다.
`ddoc showcmd` 는 등록된 명령 트리를 보여줍니다.

## `ddoc diff <ref> <cur>`

두 데이터셋의 한 줄 drift 판정. exit code: `0` OK · `1` DRIFT · `2` BLIND.

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--threshold` | 0.15 | 전체 점수 DRIFT 임계값 |
| `--attr-threshold` | 0.25 | 속성 하나만으로 DRIFT 가 되는 임계값 |
| `--detector` | `default` | 플러그인에 넘길 검출기 (`ddoc plugin detectors`) |
| `--json` | | 판정 JSON 한 객체를 stdout 에 |
| `--verbose` | | 플러그인 진단 메시지 표시 |
| `--report <path>` | | 판정 + 근거 + 처방을 담은 HTML 소견서 저장 |

## `ddoc analyze drift`

플러그인 기반 저수준 drift 분석.

| 옵션 | 설명 |
|---|---|
| `--data-path-ref` / `--data-path-cur` | 기준 / 현재 데이터 경로 (둘 다 필수) |
| `--detector` | 검출 전략 |
| `--with-embeddings` | 임베딩 즉석 계산 (vision / text) |
| `--fusion` | `none` · `weighted` · `max` · `joint` |
| `--fusion-weights` | 예: `image=0.6,text=0.4` |
| `--json` / `--ndjson-progress` / `--quiet` | 출력 형식 제어 |

## `ddoc analyze eda`

| 옵션 | 설명 |
|---|---|
| `--data-path` | 분석할 데이터 경로 (필수) |
| `--invalidate-cache` | 분석 캐시 무시 |
| `--json` / `--ndjson-progress` / `--quiet` | 출력 형식 제어 |

## `ddoc report render`

drift / EDA envelope 를 리포트로 렌더.

| 옵션 | 설명 |
|---|---|
| `-i`, `--input` | envelope JSON 경로 (필수) |
| `-o`, `--out` | 출력 경로 (필수). 형식은 확장자로 추정 |
| `-f`, `--format` | `html` · `pdf` · `md` |
| `--title` | 리포트 제목 |
| `--json` | 결과 envelope 출력 |

## `ddoc export drift-report <input>`

drift 결과를 외부로 전송. 내장 adapter: `http`, `file`.

```bash
ddoc export drift-report drift.json --to file --config '{"out_dir":"/tmp/exports"}'
ddoc export drift-report drift.json --to http --config '{"base_url":"http://my-app.local:8000"}'
```

| 옵션 | 설명 |
|---|---|
| `-t`, `--to` | 대상 adapter (필수) |
| `--config` / `--config-file` | 대상별 설정 (JSON 문자열 / YAML·JSON 파일) |
| `--json` | 결과 envelope 출력 |

## `ddoc fetch <source_uri>`

외부 데이터를 로컬 디렉토리로 가져오기. 내장: `file://` 와 일반 경로.
`s3://`, `gs://`, `http(s)://` 등은 플러그인이 제공합니다.

| 옵션 | 설명 |
|---|---|
| `-d`, `--dest` | 저장할 디렉토리 (필수) |
| `--symlink` | file 소스를 복사 대신 symlink |
| `--config` | adapter 설정 JSON |
| `--json` | 결과 envelope 출력 |

## `ddoc recipe`

| 하위 명령 | 설명 |
|---|---|
| `run <file>` | 레시피의 모든 단계 실행 (`--dry-run`, `--json`) |
| `validate <file>` | 실행 없이 파싱·검증 |
| `kinds` | 레시피에서 쓸 수 있는 단계 종류 목록 |

## `ddoc serve`

모든 명령을 HTTP 로 노출하는 FastAPI 서버 + 브라우저 GUI.

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--host` | 127.0.0.1 | 0.0.0.0 은 `--api-key` 와 TLS 뒤에서만 |
| `--port` | 8765 | |
| `--api-key` | | `X-API-Key` 헤더로 요구할 키 (`DDOC_API_KEY` 환경변수보다 우선) |
| `--log-level` | info | |
| `--reload` | | 개발용 자동 재시작 |

## `ddoc plugin`

| 하위 명령 | 설명 |
|---|---|
| `list` | 설치된 플러그인 목록 |
| `info` | 플러그인 상세 정보 |
| `install` | pip 로 플러그인 설치 |
| `detectors` | 플러그인별 지원 검출기 |

## `ddoc examples`

| 하위 명령 | 설명 |
|---|---|
| `list` | 지원하는 (modality, scenario) 조합 |
| `generate <modality> -o <dir> [-s shifted\|identical]` | `ref/`, `cur/` toy 데이터 생성 |

## `ddoc transform`

플러그인의 `transform_apply` hook 실행.

| 옵션 | 설명 |
|---|---|
| `--input-path` / `--output-path` | 입력 / 출력 경로 (필수) |
| `--transform` | 플러그인이 제공하는 transform 이름 (필수) |
| `--args-json` | transform 인자 JSON |
| `--json` | 결과 envelope 출력 |
