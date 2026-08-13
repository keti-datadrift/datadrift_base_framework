# Detector cookbook — 어느 detector 가 어떤 신호를 잡는가

`ddoc analyze drift --detector <name>` 옵션이 plugin 마다 받는 값은
다릅니다. 본 문서는 *고를 옵션이 실제로 여러 개 있는* modality
(`categorical`, `image`) 에 집중하고, single-strategy plugin
(`timeseries`, `audio`, `text`) 의 alias 가짓수도 한 번에 정리해
"어느 detector 를 골라야 할지" 를 결정하기 쉽게 만듭니다.

목록을 직접 받아 보려면:

```bash
ddoc plugin detectors
```

## modality 별 detector 요약

| modality | default | 진짜 선택지 | 비고 |
|---|---|---|---|
| `categorical` | `jensen_shannon` | `jensen_shannon` (= `js` = `default`), `overlap` | 분포가 *얼마나 다른지* 는 JSD, *겹치지 않는 비율* 은 overlap |
| `image` | `ensemble` | `ensemble`, `mmd`, `mean_shift`, `wasserstein`, `psi`, `cosine` | 5-metric ensemble = 가중합 / 다른 값은 단일 metric |
| `timeseries` | `attributes` | `attributes` (= `mmd` = `default`) | 모두 동일 — abs Δ on mean / variance / skewness / kurtosis |
| `audio` | `default` | `default` (= `mmd` = `wasserstein`) | 모두 동일 — Wasserstein on rms / zcr / centroid |
| `text` | `default` | `default` 만 | 문장 임베딩 cosine drift |

## 의사 결정 가이드 (3 줄 룰)

1. **분포 dict (color / type / hourly counts ...) 가 있다** → `categorical`,
   default `jensen_shannon`. 클래스 disjoint 가 더 의심스러우면 `overlap`.
2. **이미지 데이터셋** → `image`, default `ensemble` 부터. ensemble 의
   기여도를 envelope 의 `embedding_drift_detailed` 에서 확인 후, 한
   metric 만 보고 싶으면 그 이름을 `--detector` 에 명시.
3. **나머지 (timeseries / audio / text)** → default 그대로. plugin
   설계상 한 strategy 만 의미 있음. detector 옵션은 호환성을 위해서
   alias 만 노출.

## 실측 비교 (auto-generated)

[`_detector_scores.generated.md`](_detector_scores.generated.md) 가
`scripts/render_detector_cookbook.py` 의 출력입니다 — `ddoc
examples generate <modality> --scenario shifted` + `ddoc analyze
drift --detector <name>` 를 실제로 돌려 표를 채웁니다. release
시점에 스크립트를 다시 돌리면 코드 변화가 즉시 반영됩니다.

categorical modality 의 발췌 (shifted scenario):

```
| detector       | overall_score |
| default        | 0.1111        |
| jensen_shannon | 0.1111        |  (default == jensen_shannon)
| overlap        | 0.2488        |  (cookbook 주장: overlap ≥ JSD ✓)
```

다른 modality 까지 포함한 표가 필요하면:

```bash
python -m scripts.render_detector_cookbook --modalities categorical image
```

## 직접 비교해 보기

같은 toy 데이터에 여러 detector 를 적용해 envelope 차이를 확인:

```bash
# Categorical: shifted toy 한 쌍
ddoc examples generate categorical --out /tmp/cat --scenario shifted

for det in default jensen_shannon overlap; do
    echo "── detector=$det ──"
    ddoc analyze drift \
        --data-path-ref /tmp/cat/ref \
        --data-path-cur /tmp/cat/cur \
        --detector $det --json --quiet | python -m json.tool
done
```

`overlap` 은 보통 `jensen_shannon` 보다 큰 값이 나옵니다 — overlap 은
*sharing 비율* 을 직접 보고, JSD 는 정보-이론적으로 normalize 됨.

이미지 data 는 ensemble 의 기여도를 살펴보면 어느 단일 metric 이
fired 됐는지 가늠하기 좋습니다:

```bash
ddoc examples generate vision --out /tmp/vi --scenario shifted

ddoc analyze drift \
    --data-path-ref /tmp/vi/ref \
    --data-path-cur /tmp/vi/cur \
    --detector ensemble --json --quiet | jq '.embedding_drift_detailed'
```

## drift severity 권장 임계값

`overall_score` 가 [0, 1] 정규화 (모든 plugin 공통):

| 값 | 권장 해석 |
|---|---|
| < 0.05 | **noise** — sensors / sample 변동 수준 |
| 0.05 ~ 0.15 | **normal** — 모니터링 |
| 0.15 ~ 0.25 | **warning** — 원인 조사 시작 |
| > 0.25 | **critical** — 재학습 / gate 차단 검토 |

이 임계값은 alpr 의 post-train ddoc gate 의 default
(`ALPR_DDOC_GATE_DRIFT_THRESHOLD=0.25`) 와 일치 — drift 가 critical
구간에 들어가면 모델 deploy 차단.

## plugin 추가 시 detector 등록

새 modality plugin 을 만들 때는 `ddoc.plugins.hookspecs:ddoc_supported_detectors`
hookimpl 을 같이 구현하세요:

```python
@hookimpl
def ddoc_supported_detectors(self) -> Dict[str, Any]:
    return {
        "modality": "my_modality",
        "default": "primary_strategy",
        "supported": ["primary_strategy", "alt_strategy"],
        "notes": "한 줄로 strategy 차이 설명",
    }
```

`ddoc plugin detectors` CLI 는 모든 plugin 의 등록을 자동 합쳐 보여
줍니다. 이 cookbook 의 표 첫 번째 줄도 그 출력에서 채워졌습니다.
