# ddoc-plugin-reference-engine

레퍼런스 선택 함수 성숙도 사다리(레벨0~4)와 이벤트 온톨로지(개입/레짐 로그)를
`ddoc`에 더하는 플러그인입니다. 통계 로직은 실제 일별 판매 데이터 파일럿에서
검증된 구현을 이식했습니다.

## 기존 플러그인이 다루지 않던 공백을 메움

timeseries/evidently/categorical/keti-temporal 네 플러그인 어디에도 없던
지점을 메웁니다 (직접 소스 조사로 확인 — `dayofweek|yoy|seasonal|STL|
regime|intervention|deferred` grep 결과가 전부 0건):

- **연간 계절성 인지 기준선** — 기존 `ddoc-plugin-timeseries`의
  `seasonal_decompose(period=min(12, len//2))`는 월별용이라 일별 데이터의
  연간 계절성엔 안 맞음. 이 플러그인은 `statsmodels.tsa.seasonal.STL(period=365)`
  사용.
- **전년 대비 이중 기준 + 판정 유보** — 동일 날짜(365일 전)와 동일 요일
  (364일=52주 전) 두 기준이 상충하면 `deferred` 반환. 실제 소매업 대사
  관행에서 가져온 패턴.
- **영구 레짐 재정의 vs 일시적 개입의 구분** — keti-temporal의
  `sudden_shift`는 있는 그대로의 통계 플래그일 뿐, "원래대로 돌아올 변화"와
  "새 정상이 된 변화"를 구분하지 않음. 이 플러그인은 레벨2(regime_log)/
  레벨4(intervention_log)로 명시적으로 나눔.
- **이벤트 온톨로지 자체** — repo 전체에 `intervention|regime|calendar
  |event_log` 개념이 전무했음(grep 0건). `.ddoc/events/`에 신규 도입, 개별
  이상치 자동탐지 → 미승인 후보 등록 → 사람/에이전트 승인 흐름 포함.

## 레벨 정의

| 레벨 | 전략 |
|---|---|
| L0 고정기준선 | 최초 90일 평균을 영원히 기준으로 |
| L1 전년동일병기 | 동일 날짜·동일 요일 병기, 상충 시 `deferred` |
| L2 레짐재정의 | 등록된 영구 재정의 이벤트 이후 기준선을 다시 세움 (보정 기간 중엔 `deferred`) |
| L3 계절분해 | STL로 추세+연간계절성 분해, 잔차로만 비교 |
| L4 개입보정 | L3 위에 등록된 일시적 개입이 있으면 "설명 후보"로 표시(귀속신뢰도 동봉) |

L2와 L4의 차이: **L4는 원래대로 돌아온다는 전제(캠페인), L2는 돌아오지
않는다는 전제(플랫폼 이관)**. 반대로 등록하면 시스템이 영원히 존재하지
않을 원래 기준선을 계속 참조하게 됩니다.

## 이 저장소의 최신 관례에 맞춘 지점

(구버전 `datadrift_base_framework-2025`에서 이식하며 변경한 부분 — 자세한
근거는 코드 주석 및 `reference_engine_impl.py`의 모듈 docstring 참고)

- `eda_run`은 이제 네임스페이스 캐시(`attributes_reference_engine`)만
  쓰면 됨 — `cache_service.find_attribute_caches()`가 알아서 찾음(구버전의
  레거시 키 read-merge-write 우회는 이 저장소에서 불필요, 이미 고쳐져 있음).
- `drift_detect`는 `detector == "reference_engine"`일 때만 반응(브로드캐스트
  + self-filter 관례, keti-temporal/evidently와 동일). `"default"`는 claim하지
  않음 — `ddoc-plugin-timeseries`가 이미 그 자리의 주인.
- `ddoc_supported_detectors` 구현 — `ddoc analyze drift --detector reference_engine`
  이 설치 안 됐을 때 조용히 무시되는 대신 명확한 에러를 냄(Round-13 관례).
- `modality`는 여전히 `"timeseries_reference"`(not `"timeseries"`) —
  `_merge_plugin_results`의 modality-key 충돌(last-write-wins, 미해결 확인됨)을
  피하기 위해 유지.

## 이벤트 온톨로지

`.ddoc/events/intervention_log.yaml`, `.ddoc/events/regime_log.yaml`. 개별
값이 직전 30일 대비 z>5인 날은 `drift_detect` 실행 시 자동으로
`auto_detected_outlier` 후보로 등록됩니다(미승인 상태) — 결과 JSON의
`pending_candidate_events`에서 확인, 승인은 `EventStore.confirm_event(event_id)`.

## 실행

```bash
cd drift_studio/ddoc
source .venv/bin/activate   # 없으면 01_make_venv.sh 먼저
bash 03_install_ddoc.sh     # plugins/ 아래 전부 자동 설치 (이 플러그인 포함)
pytest plugins/ddoc-plugin-reference-engine/tests/

# path 모드 스모크 테스트 (스냅샷/DVC 설정 불필요)
ddoc analyze drift --data-path-ref <dir> --data-path-cur <dir> --detector reference_engine --json
```
