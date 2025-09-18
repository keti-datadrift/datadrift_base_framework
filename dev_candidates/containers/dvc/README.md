# dvc 기반 경량 데이터 드리프트 학습 파이프라인

- JPark @ KETI
- Since March 2025

## Project 구조

```bash
📂 project/
├── 📂 data/
│   ├── 📂 raw/
│   │   ├── data.csv  # 원본 데이터
│   ├── 📂 processed/
│       ├── train.csv
│       ├── test.csv
├── 📂 scripts/
│   ├── preprocess.py
│   ├── train.py
│   ├── evaluate.py
├── dvc.yaml
├── params.yaml
├── requirements.txt
├── 📂 venv/

```