# Toy data — 5분 안에 첫 drift 결과 보기

ddoc 를 처음 만지는 사용자가 본인 데이터 없이도 **drift 가 어떻게
계산되고 어떤 envelope 으로 떨어지는지** 5 분 안에 직접 확인할 수
있도록 5 modality (timeseries / audio / text / vision / categorical) 의
합성 toy 데이터셋을 generator 로 제공합니다.

같은 generator 를 pytest 회귀 (`tests/test_plugin_drift_e2e.py`) 도
사용 — 즉 사용자가 `ddoc examples generate` 로 만드는 데이터는 ddoc
자체 테스트가 검증한 것과 byte-for-byte 동일합니다.

## 사용 가능한 modality 와 scenario

```bash
ddoc examples list
```

| modality | data shape | shifted scenario |
|---|---|---|
| `timeseries` | CSV `timestamp,x,y` (200 rows) | x ~ N(0,1) → x ~ N(1.5,1) |
| `audio` | mono WAV, 8 kHz, 1 초 | 440 Hz → 880 Hz (octave) |
| `text` | CSV `id,text` (20 rows) | 짧은 단어 → 긴 문장 |
| `vision` | 5 × 64×64 PNG | 빨간색 → 파란색 |
| `categorical` | `distributions.json` — color/type/hourly counts + confidence stats | keti 차량 fingerprint shape, 4 분포 모두 shift |

각 modality 는 두 scenario 지원:
- `shifted` (default): ref 와 cur 분포가 다름 → drift score > 0
- `identical`: ref 와 cur 가 완전 동일 → drift score ≈ 0 (sanity check)

## 5분 quick start

```bash
# 1. timeseries toy 데이터 생성 (drift 시나리오)
ddoc examples generate timeseries --out /tmp/ex --scenario shifted

# 2. drift 측정 (path mode — project / snapshot 불필요)
ddoc analyze drift \
    --data-path-ref /tmp/ex/ref \
    --data-path-cur /tmp/ex/cur \
    --json --quiet
```

출력 (envelope):
```json
{
  "modality": "timeseries",
  "timestamp": "20260508_092052",
  "overall_score": 0.307
}
```

`overall_score = 0.307` — 분포가 이동했음을 ddoc 가 정량화한 결과.
`identical` scenario 로 다시 돌리면 score ≈ 0 으로 떨어집니다.

## 다른 modality

audio 는 plugin (`ddoc-plugin-audio`) 과 librosa 가 필요합니다:

```bash
pip install ddoc-plugin-audio
ddoc examples generate audio --out /tmp/au --scenario shifted
ddoc analyze drift --data-path-ref /tmp/au/ref --data-path-cur /tmp/au/cur \
    --json --quiet
```

text 는 `ddoc-plugin-text` + nltk 데이터:

```bash
pip install ddoc-plugin-text
python -c "import nltk; nltk.download('punkt_tab'); nltk.download('stopwords')"
ddoc examples generate text --out /tmp/tx --scenario shifted
ddoc analyze drift --data-path-ref /tmp/tx/ref --data-path-cur /tmp/tx/cur \
    --json --quiet
```

vision 은 `ddoc-plugin-vision` + torch + CLIP:

```bash
pip install ddoc-plugin-vision torch torchvision pillow
pip install 'git+https://github.com/openai/CLIP.git'
ddoc examples generate vision --out /tmp/vi --scenario shifted
ddoc analyze drift --data-path-ref /tmp/vi/ref --data-path-cur /tmp/vi/cur \
    --json --quiet
```

categorical 은 *별도 모델 의존 없음* — 분포 dict 만 비교 (jensen-
shannon / overlap). vehicle / IoT / 카메라 분류 데이터에 맞는 modality:

```bash
pip install ddoc-plugin-categorical    # ddoc-full 에 포함
ddoc examples generate categorical --out /tmp/cat --scenario shifted
ddoc analyze drift --data-path-ref /tmp/cat/ref --data-path-cur /tmp/cat/cur \
    --json --quiet
```

생성되는 `distributions.json` 의 shape 는 `keti_veritas` 의
`AnalyticsRepository.build_camera_stats_window()` 출력과 byte-
equivalent — 즉 이 demo 는 keti 의 카메라 fingerprint drift 파이프
라인 회귀 테스트로도 작용합니다.

## Tabular EDA report 렌더 (별도 path)

`ddoc-plugin-tabular` (Round 27-B) 는 *drift 검출* 이 아니라 *EDA
envelope 의 PDF/HTML 렌더* 를 담당합니다. 이미 만들어진 envelope
JSON (예: `drift_studio/backend` 가 emit 하는 EDA dict) 을 받아
컬럼별 summary / missing-rate 표를 포함한 보고서로 출력합니다.

```bash
# 1. 샘플 envelope 작성 (실제로는 backend 가 emit; 여기선 손으로)
cat > /tmp/eda.json <<'EOF'
{
  "modality": "tabular",
  "name": "iris.csv",
  "rows": 150,
  "cols": 5,
  "missing": {"sepal_len": 0.0, "petal_len": 0.0},
  "summary": {
    "sepal_len": {"count": 150, "mean": 5.84, "std": 0.83,
                   "min": 4.3, "50%": 5.8, "max": 7.9},
    "petal_len": {"count": 150, "mean": 3.76, "std": 1.76,
                   "min": 1.0, "50%": 4.35, "max": 6.9}
  }
}
EOF

# 2. 렌더 (HTML)
ddoc report render -i /tmp/eda.json -o /tmp/iris.html --format html
# 또는 PDF (weasyprint 필요)
ddoc report render -i /tmp/eda.json -o /tmp/iris.pdf --format pdf
```

ddoc serve 띄워둔 상태라면 inline-envelope mode 로도 가능 (Round 25):

```bash
curl -s -X POST http://localhost:8765/report/render \
  -H 'Content-Type: application/json' \
  -d "{\"envelope\": $(cat /tmp/eda.json), \"format\": \"html\"}" \
  > /tmp/iris.html
```

## ddoc.yaml 컨벤션

각 generator 가 작성하는 dataset 디렉터리에는 ddoc plugin 이 modality
를 인식하기 위한 `ddoc.yaml` 이 함께 들어갑니다:

```
<dataset_dir>/
├── ddoc.yaml          ← modality 선언
├── data.csv           ← timeseries / text 의 경우
├── tone.wav           ← audio 의 경우
└── img_*.png          ← vision 의 경우
```

modality 별 `ddoc.yaml` 필드:

| modality | 필드 |
|---|---|
| `timeseries` | `modality: timeseries`, `csv_file: data.csv`, `timestamp_column: timestamp`, `numeric_columns: [x, y]` |
| `text` | `modality: text`, `text_column: text`, `id_column: id`, `language: english` |
| `audio` | `modality: audio`, `formats: [.wav]` |
| `image` | `modality: image`, `formats: [.png]` |
| `categorical` | `modality: categorical`, `distributions_file: distributions.json` (plugin 은 단일 평면 layout 만 읽음 — `<dataset_dir>/distributions.json` 직접) |

본인 데이터로 옮길 때는 같은 layout 을 따르면 됩니다 — `ddoc.yaml` 만
정확히 맞추면 plugin 이 자동으로 처리합니다.

## --scenario identical 의 용도

신규 deployment 가 ddoc 를 처음 켰을 때 "drift 가 진짜 0 이 나오는
환경인가?" 를 확인하는 sanity check:

```bash
ddoc examples generate timeseries --out /tmp/sane --scenario identical
ddoc analyze drift --data-path-ref /tmp/sane/ref --data-path-cur /tmp/sane/cur \
    --json --quiet
# → overall_score: 0.0
```

이 단계가 통과하면 plugin 설치 / 환경 변수 / DVC / cache 라우팅이 모두
정상이라는 의미. shifted scenario 로 옮기면 의미 있는 drift score 를
관찰할 수 있습니다.

## 다음 단계

- snapshot mode 워크플로 (Git + DVC 통합): [snapshots](../guides/snapshots.md)
- backend orchestrator 패턴 (`drift_studio` 가 ddoc CLI 를 subprocess
  로 호출): [`_specs/ddoc_orchestrator_pattern.md`](../../../_specs/ddoc_orchestrator_pattern.md)
- modality 별 plugin contract: 각 plugin 의 `README.md`
