# 핵심 개념

ddoc 를 이해하는 데 필요한 개념들을 정리합니다.

## 1. 판정 (Verdict)

`ddoc diff` 는 두 데이터셋을 비교해 세 가지 중 하나로 답합니다.

| 판정 | exit code | 의미 |
|---|:---:|---|
| `OK` | 0 | 의미 있는 분포 변화가 없음 |
| `DRIFT` | 1 | 분포가 변했음 |
| `BLIND` | 2 | 판정할 근거가 없음 (경로 없음, 처리할 엔진 없음, 비교 실패 등) |

`BLIND` 는 "괜찮다" 가 아니라 "모른다" 입니다. 확인할 수 없는 상황을
`OK` 로 덮지 않기 위해 셋째 답을 둡니다.

`DRIFT` 는 다음 중 하나일 때 내려집니다.

- 전체 점수 `overall_score` 가 `--threshold` (기본 0.15) 이상
- 속성 하나의 점수가 `--attr-threshold` (기본 0.25) 이상 —
  평균에 묻히는 강한 국소 변화를 놓치지 않기 위함

severity 는 `high` / `medium` / `low` / `none` 으로 함께 표시됩니다.

## 2. Modality 와 자동 감지

입력 경로를 보고 데이터 종류(modality)를 추정합니다.
이미지 폴더는 `vision`, CSV 는 `csv`, ddoc categorical 레이아웃은
`categorical` 하는 식입니다. 생 CSV 는 내장 비교기로 처리되어 플러그인이
없어도 판정이 나옵니다.

플러그인이 읽는 dataset layout 은 modality 별 `ddoc.yaml` + 데이터 파일
입니다. 자세한 형식은 [toy 데이터 튜토리얼](toy-data.md) 의
`ddoc.yaml 컨벤션` 참고.

## 3. 플러그인과 검출기

ddoc 코어는 가볍고, 실제 분석은 플러그인이 합니다. 플러그인은
[pluggy](https://pluggy.readthedocs.io/) hookspec 을 구현하는 독립 pip
패키지이며 `ddoc` entry-point group 으로 등록됩니다.

주요 hookspec:

| hook | 역할 |
|---|---|
| `drift_detect` | 두 데이터의 drift 점수 계산 |
| `eda_run` | 한 데이터의 탐색적 분석 |
| `ddoc_supported_detectors` | 플러그인이 제공하는 검출기 목록 광고 |
| `report_render` | 결과를 리포트로 렌더 (없으면 내장 렌더러 사용) |
| `export_drift_report` | 결과를 외부 시스템으로 전송 (없으면 내장 file / http 사용) |
| `data_source_read` | 외부 데이터 소스 읽기 (없으면 내장 file 사용) |

`--detector` 로 검출 전략을 고릅니다 (`ddoc plugin detectors` 로 목록 확인).
한 플러그인이 입력을 처리하지 못해 실패해도 다른 플러그인의 결과는
그대로 사용됩니다.

## 4. Envelope

`--json` 출력과 명령 사이의 주고받기는 JSON envelope 한 객체로 합니다.
대표적인 필드는 `status`, `modality`, `overall_score`, `attribute_drifts`
입니다. `ddoc report render` 와 `ddoc export drift-report` 가 이
envelope 를 입력으로 받으므로, 단계별 결과를 파일로 남겨 다음 단계에
넘길 수 있습니다.

## 5. 분석 캐시

플러그인은 같은 데이터를 다시 분석하지 않도록 분석 결과를 캐시에
저장합니다. `ddoc analyze eda --invalidate-cache` 로 캐시를 무시하고
다시 분석할 수 있습니다.

## 6. 레시피

fetch → analyze → report → export 같은 여러 단계를 YAML 파일 하나에
적고 `ddoc recipe run <file>` 로 실행합니다. 변수 치환을 지원하므로
drift 점검 파이프라인 전체가 리뷰 가능한 텍스트가 됩니다.
자세한 내용은 [레시피 튜토리얼](recipe.md).

## 다음 단계

- [빠른 시작](quick-start.md)
- [데이터 분석](../guides/analysis.md)
- [명령어 레퍼런스](../reference/commands.md)
