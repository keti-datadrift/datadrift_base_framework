# dd

- JPark @ KETI, Since March 2025

## Code structure

```bash

/dd/
│── dd/                         # Python 패키지
│    ├── __init__.py            # 패키지 인식 파일
│    ├── cli.py                 # CLI 명령어 정의
│    ├── core/                  # 기능별 모듈화된 로직 관리
│    │   ├── __init__.py
│    │   ├── init.py            # 프로젝트 초기화 기능
│    │   ├── push.py            # 데이터/모델 업로드
│    │   ├── pull.py            # 데이터/모델 다운로드
│    │   ├── diagnose.py        # 데이터 품질 진단
│    │   ├── treat.py           # 데이터 품질 개선
│    │   ├── train.py           # 모델 학습
│    │   ├── monitor.py         # 모니터링 기능
│    │   ├── lineage.py         # lineage 추적
│    │   ├── compare.py         # 모델 비교
│    │   ├── fuse.py            # 모델 융합
│    ├── hub                    # Hub
│    │   ├── hub_api.py         # FastAPI 서버
│
│── version.json                # 버전 정보 저장
│── setup.py                    # 패키지 설치 정보
│── requirements.txt             # 패키지 의존성 목록


```

## 주요 기능

```bash
	•	dd init: 프로젝트 초기화
	•	dd push <파일>: 데이터/모델 업로드
	•	dd pull <파일명>: 데이터/모델 다운로드
	•	dd diagnose <파일>: 데이터 품질 진단
	•	dd treat <파일>: 데이터 품질 개선
	•	dd train <파일> [--output 모델파일]: 모델 학습
	•	dd monitor <파일> [--interval n]: 데이터/모델 모니터링
	•	dd lineage <파일>: 데이터 및 모델 lineage 추적
	•	dd compare <모델1> <모델2>: 모델 성능 비교
	•	dd fuse <모델1> <모델2> --output <결합모델>: 모델 융합
	•	dd --version (dd -v): 버전 정보 출력
```