## ddoc 개발 철학

- `ddoc`는 별도의 파이썬 패키지(CLI)로써 **데이터 진단, 데이터 드리프트 탐지, 데이터 관리를 위한 MLOps, DataOps 전략 기술**입니다.

### 1\. 객관적/비판적 관점에서의 분석

| 관점 | `ddoc` CLI 방식 | 현재 쉘 스크립트 방식 | 비판적 평가 |
| :--- | :--- | :--- | :--- |
| **사용자 경험 (UX)** | **매우 우수.** `ddoc data add d1`처럼 직관적. 복잡한 DVC/Git 명령을 추상화. | **보통.** 명령어를 일일이 기억해야 하며, 오류 발생 시 디버깅이 어려움. | **`ddoc` 승.** 진입 장벽을 낮추고 오류를 표준화함. |
| **확장성** | **최고.** `pluggy` 기반으로 설계하면, 새로운 분석 기능(예: 이미지 품질 점수)을 플러그인 형태로 쉽게 추가 가능. | **낮음.** 새로운 기능을 추가하려면 여러 쉘 스크립트를 수정해야 함. | **`ddoc` 압승.** `pluggy`를 통해 MLOps 엔지니어 간의 협업이 용이해짐. |
| **데이터 분석/드리프트** | **매우 우수.** Evidently AI, Great Expectations 같은 전문 라이브러리를 내부에 통합하여 표준화된 분석 보고서를 생성. | **보통.** 분석 코드를 별도 파이프라인 스테이지로 관리해야 하며, 결과를 수동으로 비교해야 함. | **`ddoc` 승.** 분석 결과를 하나의 API로 통합하여 UI 연계가 쉬움. |
| **개발/유지보수 비용** | **높음.** DVC, Git, 분석 라이브러리의 API를 모두 감싸는(Wrapping) 계층을 개발해야 함. 초기 개발 및 종속성 관리가 복잡함. | **낮음.** 이미 존재하는 쉘 기능을 활용하므로 개발 비용은 낮음. | **스크립트 승.** (단기적 관점) 장기적으로는 `ddoc`가 유지보수 비용을 절감함. |

**결론:** `ddoc` 방식은 초기 개발 비용은 높지만, **장기적인 MLOps 표준화, 팀 생산성, 그리고 최종 목표인 UI 시각화 연계를 위한 최선의 아키텍처**입니다. DVC의 강력한 데이터 백엔드를 활용하는 이상적인 접근 방식입니다.

-----

## 2\. `ddoc` 핵심 아키텍처 및 구현 예시

`ddoc` 패키지는 `pluggy`를 사용하여 핵심 기능과 분석 기능을 분리하는 아키텍처로 구성합니다.

| 파일 | 역할 | 설명 |
| :--- | :--- | :--- |
| **`ddoc/cli.py`** | **사용자 인터페이스** | `ddoc data add`, `ddoc analyze` 등의 명령을 처리하고, `ddoc/core.py`를 호출합니다. |
| **`ddoc/core.py`** | **DVC/Git 백엔드** | DVC와 Git 명령어를 실행하여 데이터 버전 관리를 수행합니다. |
| **`ddoc/hookspecs.py`** | **플러그인 정의** | `pluggy`를 위한 확장 지점(Hooks)을 정의합니다. (예: `run_data_analysis`) |
| **`ddoc_plugins/drift_analyzer.py`** | **샘플 플러그인** | Evidently AI 등을 사용하여 데이터 드리프트를 분석하고 결과를 반환하는 실제 로직을 구현합니다. |

### 1\. `ddoc/hookspecs.py` (플러그인 확장 정의)

http://googleusercontent.com/immersive_entry_chip/0

### 2\. `ddoc/core.py` (DVC/Git 백엔드 래퍼)

http://googleusercontent.com/immersive_entry_chip/1

### 3\. `ddoc_plugins/drift_analyzer.py` (Evidently AI 플러그인 시뮬레이션)

http://googleusercontent.com/immersive_entry_chip/2

### 4\. `ddoc/cli.py` (CLI 인터페이스)

http://googleusercontent.com/immersive_entry_chip/3

### 5\. 프로젝트 실행 시나리오 (ddoc 사용)

이제 복잡한 쉘 스크립트 대신 다음과 같이 `ddoc` 명령을 사용할 수 있습니다.

```bash
# 초기 환경 설정 (여전히 필요)
# bash ./scripts/project_setup.sh

# 1. d2 데이터셋 등록 및 버전 관리 (dvc/git/params.yaml 자동 처리)
python ddoc/cli.py data add d2 --config yolo_d2.yaml

# 2. d2 데이터셋 기반으로 학습 실행 (기존 run_experiment.sh 실행)
bash ./scripts/run_experiment.sh 'd2_baseline' '.epochs=5'

# 3. d1 데이터셋 브랜치로 전환 및 복구
git checkout feature/dataset_d1 
dvc checkout

# 4. d2와 d1 데이터셋 간의 드리프트 분석 실행 (pluggy 플러그인 실행)
python ddoc/cli.py analyze drift d2 d1
```