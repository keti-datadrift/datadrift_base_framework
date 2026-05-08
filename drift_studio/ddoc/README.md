# ddoc - Data Drift Detection & Analysis Framework

> Git-like workflow for MLOps with snapshot-based version management

**ddoc**은 데이터, 코드, 실험을 통합적으로 관리하는 MLOps 도구입니다. Git과 유사한 직관적인 워크플로우로 머신러닝 프로젝트의 완벽한 재현성을 보장합니다.

## ✨ 주요 기능

- 📦 **Workspace Management**: 자동 프로젝트 스캐폴딩
- 📸 **Snapshot System**: Git-like 버전 관리 (데이터 + 코드 + 실험)
- 🔬 **Data Analysis**: EDA 및 Drift 감지
- 🧪 **Experiment Tracking**: Trainer 기반 실험 시스템
- 🔌 **Plugin Architecture**: 확장 가능한 플러그인 시스템

## 🚀 빠른 시작

### 설치

```bash
# 가벼운 코어 — init / add / snapshot / ingest / analyze (path mode)
pip install ddoc

# Use-case 별 extras (Round-2 정리, 2026-05-07)
pip install ddoc[ingest]        # parquet writer (pyarrow)
pip install ddoc[exp]           # exp train / eval / best (mlflow)
pip install ddoc[orchestrator]  # backend subprocess orchestrator alias
pip install ddoc[vision]        # CLIP / torch / image stack
pip install ddoc[yolo]          # ultralytics / opencv
pip install ddoc[vis]           # Streamlit GUI

# 모두
pip install ddoc[all]           # ⚠️ all 의 plugin file:// 경로는 개발자
                                # local checkout 에 묶임 — 일반 사용자는
                                # 위 개별 extras 조합 권장
```

**install matrix** — 어떤 명령어가 어떤 extras 를 요구하는지:

| 명령어 / 사용 사례 | core | ingest | exp | vision/yolo | vis |
|---|:---:|:---:|:---:|:---:|:---:|
| `ddoc init / add / snapshot` | ✓ | | | | |
| `ddoc ingest` (CSV) | ✓ | | | | |
| `ddoc ingest --parquet` | ✓ | ✓ | | | |
| `ddoc analyze drift|eda` (path mode + plugin) | ✓ | | | ✓ | |
| `ddoc exp train / eval / best` | ✓ | | ✓ | ✓ (trainer 의존) | |
| `ddoc vis` (Streamlit GUI) | ✓ | | | | ✓ |
| `drift_studio` backend subprocess orchestrator | ✓ | | | | |

### 5분 튜토리얼

```bash
# 1. 프로젝트 초기화
ddoc init myproject
cd myproject

# 2. 데이터 추가
ddoc add --data ./datasets/train_data

# 3. 첫 스냅샷 생성
git add . && git commit -m "Initial setup"
ddoc snapshot create -m "baseline" -a baseline

# 4. 데이터 분석
ddoc analyze eda

# 5. 실험 실행
ddoc exp train yolo --dataset train_data
```

더 자세한 튜토리얼은 [시작하기 가이드](docs/tutorial/quick-start.md)를 참조하세요.

## 📚 문서

### 시작하기
- **[설치 가이드](docs/tutorial/installation.md)** - 설치 및 요구사항
- **[빠른 시작](docs/tutorial/quick-start.md)** - 5분 튜토리얼
- **[핵심 개념](docs/tutorial/concepts.md)** - Workspace, Snapshot, Alias 이해하기

### 사용자 가이드
- **[워크스페이스 관리](docs/guides/workspace.md)** - 프로젝트 초기화 및 파일 관리
- **[스냅샷 관리](docs/guides/snapshots.md)** - 버전 관리 및 복원
- **[Trainer 시스템](docs/guides/trainer.md)** - Trainer 기반 실험 시스템
- **[데이터 분석](docs/guides/analysis.md)** - EDA 및 Drift 감지
- **[실험 관리](docs/guides/experiments.md)** - 실험 실행 및 추적

### 레퍼런스
- **[명령어 레퍼런스](docs/reference/commands.md)** - 모든 명령어 상세 설명

### 고급 사용법
- **[워크플로우](docs/advanced/workflows.md)** - 고급 워크플로우 및 베스트 프랙티스
- **[문제 해결](docs/advanced/troubleshooting.md)** - 자주 발생하는 문제 해결

### 마이그레이션
- **[v1.x → v2.0 마이그레이션](docs/migration/v1-to-v2.md)** - v1.x에서 업그레이드

전체 문서는 [docs/](docs/) 디렉토리에서 확인하세요.

## 📦 버전

- **v2.0.3** (Current) - [릴리스 노트](docs/releases/v2.0.3.md)
- **v2.0.2** - [릴리스 노트](docs/releases/v2.0.2.md)
- **v2.0.1** - [릴리스 노트](docs/releases/v2.0.1.md)
- **v2.0.0** - [릴리스 노트](docs/releases/v2.0.0.md)
- **v1.3.6** (Legacy) - [릴리스 노트](docs/releases/v1.3.6.md)

[전체 변경 이력](docs/changelog.md) | [릴리스 노트](docs/releases/)

## 🎯 주요 사용 사례

### 데이터 버전 관리
```bash
ddoc init myproject
ddoc add --data ./datasets/train_data
ddoc snapshot create -m "baseline dataset" -a baseline
```

### 실험 추적
```bash
ddoc exp train yolo --dataset train_data --model yolov8n.pt
ddoc exp best train_data  # 최고 성능 실험 찾기
```

### 데이터 드리프트 감지
```bash
ddoc analyze drift baseline production
```

### Multi-site / 사이트-간 통합 (`ingest` + DVC)

Round-2 (2026-05-07) 부터 ddoc 는 **다른 사이트 / 다른 시스템에서 떨군
envelope JSON** 을 직접 받아 분석에 쓸 수 있습니다.

**예시 — keti_veritas 의 audit export 를 ddoc 로 끌어오기:**

```bash
# 사이트에서 keti_veritas 가 envelope JSON 을 떨굼
# (DD_EXPORT_DIR=/mnt/share/site_a/audit)

# ddoc 로 ingest
ddoc ingest \
    --from-dir /mnt/share/site_a/audit \
    --site-id site_a \
    --workspace ~/ddoc-workspace

# 결과:
#   ~/ddoc-workspace/.ddoc/inbox/site_a/decisions/decisions_<ts>.csv
#   ~/ddoc-workspace/.ddoc/inbox/site_a/_manifest.jsonl
#   원본은 .processed/ 로 이동 (재실행 idempotent)

# 머신러닝 친화적 JSON 출력 (스크립트 / 백엔드 orchestrator 용)
ddoc ingest --from-dir /tmp/export --json | jq '.decision_rows'

# DVC 통한 자동 pull (사이트-간 sync)
ddoc ingest --from-dir audit/ --dvc-pull --site-id site_b
```

**Envelope contract** — protocol 1.1 (keti_veritas 의
`app/services/audit/envelope.py` 와 mirror). frozen dataclass:

```jsonc
{
  "protocol_version": "1.1",
  "source": {"app_id": "...", "app_type": "...", "instance_id": null},
  "payload_kinds": ["decision_batch"] | ["drift_report"],
  "decision_batch": [{"id":"...", "decision_type":"...", ...}, ...],
  "drift_report": {...},
  "sent_at": "2026-05-07T00:00:00Z"
}
```

**On-disk inbox layout:**

```
<workspace>/.ddoc/inbox/<site_id>/
├── decisions/decisions_<UTC ts>.csv      (or .parquet w/ --parquet)
├── drift_reports/drift_<UTC ts>_<src>.json
├── _manifest.jsonl                       (one line per ingest run)
└── .processed/<original_envelope>.json
```

### DVC remote layout (multi-site sync)

`drift_studio` backend (orchestrator) 는 시작 시점에 `DVC_REMOTE_URL` +
`DVC_SITE_ID` 환경변수가 있으면 자동으로 default remote 를 설정합니다.
권장 layout:

```
<DVC_REMOTE_URL>/
├── site_a/
│   ├── datasets/    # raw / curated input data
│   ├── models/      # trained model artifacts
│   └── audit/       # keti_veritas envelope JSON exports
└── site_b/
    └── ...
```

`s3://`, `gs://`, `azure://`, `ssh://`, 또는 로컬 마운트 NAS 경로 모두
지원. `ddoc ingest --dvc-pull` 이 `dvc pull <from-dir>` 을 선행 실행해
원격 → 로컬 → ingest 한 줄로 처리합니다.

### Backend orchestrator 와의 관계

`drift_studio/backend/` 는 ddoc 를 *Python library* 로 import 하는 대신
**subprocess 로 호출** 합니다 (Round-2 reframe). 환경변수
`BACKEND_USE_DDOC_CLI=true` 일 때 backend 의 `/drift`, `/eda` 엔드포인트
가 `ddoc analyze drift|eda --json` 을 fork 합니다. 자세한 contract 는
[`_specs/ddoc_orchestrator_pattern.md`](../../_specs/ddoc_orchestrator_pattern.md)
참조.

## 🤝 기여

기여를 환영합니다! 기여 가이드는 [CONTRIBUTING.md](CONTRIBUTING.md)를 참조하세요.

## 📄 라이선스

MIT License

## 👥 기여자

- JPark @ KETI
- Ethicsense @ KETI

---