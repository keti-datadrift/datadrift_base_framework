# 데이터 분석

`ddoc diff` 가 한 줄 판정이라면, `ddoc analyze` 는 플러그인 결과를 그대로
보여주는 저수준 명령입니다. 검출기 선택, 여러 modality 결과 합치기,
진행 상황 스트리밍이 필요할 때 씁니다.

## Drift 감지 — `ddoc analyze drift`

```bash
ddoc analyze drift --data-path-ref data/ref --data-path-cur data/cur
ddoc analyze drift --data-path-ref data/ref --data-path-cur data/cur --json --quiet
```

| 옵션 | 설명 |
|---|---|
| `--data-path-ref` / `--data-path-cur` | 기준 / 현재 데이터 경로 (둘 다 필수) |
| `--detector` | 검출 전략. `ddoc plugin detectors` 로 목록 확인 ([cookbook](../tutorial/detectors.md)) |
| `--with-embeddings` | 플러그인이 임베딩을 즉석 계산 (vision / text, CLIP 필요) |
| `--fusion` / `--fusion-weights` | 여러 modality 점수를 하나로 합침 (`none` / `weighted` / `max` / `joint`) |
| `--json` | 결과 envelope 를 stdout 에 JSON 한 객체로 |
| `--ndjson-progress` | 진행 상황을 stderr 에 NDJSON 으로 (오케스트레이터용) |
| `--quiet` | 플러그인 출력 숨김 |

두 경로 중 하나라도 빠지면 `path_mode_incomplete` 오류와 함께 exit code 2
로 끝납니다.

## EDA — `ddoc analyze eda`

```bash
ddoc analyze eda --data-path data/cur
ddoc analyze eda --data-path data/cur --json --quiet
```

| 옵션 | 설명 |
|---|---|
| `--data-path` | 분석할 데이터 경로 (필수) |
| `--invalidate-cache` | 기존 분석 캐시를 무시하고 다시 분석 |
| `--json` / `--ndjson-progress` / `--quiet` | drift 와 동일 |

EDA 는 `eda_run` hook 을 구현한 플러그인이 있어야 동작합니다.
(예: categorical 플러그인은 drift 만 제공합니다.)

## 결과를 리포트로

```bash
ddoc analyze drift --data-path-ref data/ref --data-path-cur data/cur --json --quiet > drift.json
ddoc report render -i drift.json -o drift.html
ddoc report render -i drift.json -o drift.md --format md
```

## 다음 단계

- [detector cookbook](../tutorial/detectors.md)
- [레시피](../tutorial/recipe.md) — analyze → report → export 를 한 파일로
- [명령어 레퍼런스](../reference/commands.md)
