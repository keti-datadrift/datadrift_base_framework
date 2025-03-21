# Git LFS vs DVC

- JPark, ChatGPT 
- March 2025

## 한줄 요약
- 🚀 __2025년 기준, 온프레미스 환경에서 ML 모델 & 데이터 버전 관리를 원한다면 DVC를 사용하는 것이 가장 적절합니다!__ 🎯


## 약어
- Git LFS (Large File System)
- DVC (Data Version Control)


## 📌 Git LFS vs. DVC: 비교 분석

- Git LFS와 DVC는 대용량 파일 및 모델을 버전 관리하는 도구지만, 사용 방식과 기능에 차이가 있다.
- 아래에서 Git LFS와 DVC의 장단점을 비교하고, 온프레미스(On-Premise) 환경에서 어떤 도구가 더 적절한지 분석한다.


### 1️⃣ Git LFS vs. DVC 개요

| **항목**         | **Git LFS (Git Large File Storage)** | **DVC (Data Version Control)** |
|------------------|-------------------------------------|--------------------------------|
| **주요 목적**   | 대용량 파일(모델, 바이너리 등) 버전 관리 | ML 실험, 데이터셋, 모델 버전 관리 |
| **Git과의 관계** | Git의 확장 기능 (Git과 강하게 결합) | Git과 독립적 (Git은 코드, DVC는 데이터) |
| **버전 관리 대상** | 대용량 파일 (.bin, .jpg, .csv 등) | 데이터, 모델, 실험 파이프라인 |
| **스토리지 방식** | Git LFS 서버 (GitHub, GitLab, Bitbucket) 또는 자체 서버 | 로컬/NAS, 클라우드(S3, GDrive, SSH, WebDAV) 등 다양한 스토리지 지원 |
| **데이터 추적 방식** | Git LFS 메타데이터 (.gitattributes) | `.dvc` 파일 및 `dvc.yaml` 파이프라인 |
| **협업 지원** | Git 기반, 브랜치 간 충돌 발생 가능 | Git에서 `.dvc` 파일만 관리, 대용량 파일 충돌 최소화 |
| **필요한 설치** | Git + Git LFS | Git + DVC |
| **사용 난이도** | Git 사용자에게 익숙한 방식 | 별도의 학습 필요 |

---

### 2️⃣ Git LFS vs. DVC: 장단점 비교

#### ✅ Git LFS 장점
- **Git과 원활한 통합** → 기존 Git 워크플로우를 그대로 사용 가능
- **쉬운 설정** → `git lfs track "*.bin"` 한 줄로 파일 추적 가능
- **빠른 속도** → Git과 함께 LFS 서버를 사용하여 모델/데이터 관리 가능
- **제3자 서비스 지원** → GitHub, GitLab, Bitbucket 등의 Git LFS 지원

#### ❌ Git LFS 단점
- **대형 파일 충돌 문제** → 브랜치에서 모델/데이터가 다를 경우 충돌이 발생할 수 있음
- **스토리지 확장 어려움** → Git LFS 서버가 필요하거나, 원격 저장소 제한 존재 (GitHub는 2GB 무료)
- **데이터 파이프라인 없음** → 데이터 처리 단계(ETL, 모델 훈련) 추적 불가능

#### ✅ DVC 장점
- **데이터 + 모델 + 파이프라인까지 관리 가능**  
  - Git에서 코드만 관리하고, DVC는 데이터와 ML 모델을 별도로 관리 가능  
  - `.dvc` 파일을 이용해 **대용량 데이터 변경 사항을 Git처럼 추적 가능**
- **다양한 스토리지 지원**  
  - 로컬 저장소(NAS), 클라우드(AWS S3, GCP, WebDAV, SSH 등) 연결 가능  
  - GitHub, GitLab과 독립적으로 **온프레미스 환경에서도 사용 가능**
- **충돌 방지 및 협업 용이**  
  - `.dvc` 파일만 Git에 저장하여, **Git 리포지토리 크기를 줄일 수 있음**  
  - 팀원 간 **데이터 충돌 없이 동기화 가능**
- **ML 실험 관리 지원 (`dvc exp run`)**  
  - 하이퍼파라미터, 모델 성능, 데이터셋 버전을 쉽게 비교 가능  
  - `dvc exp show`, `dvc diff` 등을 사용하여 실험 간 차이를 추적 가능

#### ❌ DVC 단점
- **Git LFS보다 학습 곡선이 높음**  
  - `dvc add`, `dvc push`, `dvc repro` 등 추가적인 개념을 익혀야 함  
  - Git LFS보다 설정 과정이 복잡할 수 있음
- **모델 및 데이터 저장이 Git과 별도로 이루어짐**  
  - GitHub처럼 Git LFS는 파일과 코드를 함께 저장할 수 있지만,  
  - DVC는 **Git에서 코드 + `.dvc` 파일만 추적하고, 원본 데이터는 다른 저장소(NAS, S3 등)에 저장**

---

### 3️⃣ 온프레미스(On-Premise) 환경에서의 선택

| **요구사항** | **추천 도구** | **이유** |
|-------------|--------------|---------|
| **Git과 완벽한 통합이 필요** | Git LFS | Git을 그대로 사용하며 모델/데이터를 함께 관리 가능 |
| **대용량 데이터 & 모델 관리** | DVC | Git과 분리하여 대용량 데이터를 NAS/S3에 저장 가능 |
| **로컬 스토리지 (NAS, 외장하드) 사용** | DVC | Git LFS는 별도 서버가 필요하지만, DVC는 로컬 저장소를 쉽게 연동 가능 |
| **ML 실험 및 파이프라인 관리** | DVC | `dvc.yaml`을 활용해 데이터 & 모델 실험 자동화 가능 |
| **데이터 변경 사항 추적 (Diff 기능)** | DVC | `dvc diff`로 데이터셋 변경 추적 가능 |

---

## 🚀 결론: Git LFS vs. DVC 선택 가이드

| 사용 시나리오 | 추천 도구 |
|--------------|---------|
| **작은 프로젝트에서 코드 & 모델을 GitHub에서 함께 관리** | ✅ Git LFS |
| **대용량 데이터(GB~TB)를 온프레미스(NAS, 서버)에 저장하고 Git과 독립적으로 관리** | ✅ DVC |
| **ML 실험, 하이퍼파라미터 튜닝을 함께 관리** | ✅ DVC |
| **GitHub/GitLab과 강력한 연동이 필요** | ✅ Git LFS |

## 결론 요약
- 🚀 __온프레미스 환경에서 ML 모델 & 데이터 버전 관리를 원한다면 DVC를 사용하는 것이 가장 적절합니다!__ 🎯

