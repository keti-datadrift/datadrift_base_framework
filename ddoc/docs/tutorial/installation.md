# 설치 가이드

ddoc 설치 및 요구사항에 대한 가이드입니다.

## 요구사항

- **Python**: 3.8 이상
- **Git**: 필수 (버전 관리용)
- **DVC**: 필수 (데이터 버전 관리용)

## 설치 방법

### pip를 통한 설치

```bash
pip install ddoc
```

### 개발 버전 설치

```bash
git clone https://github.com/your-org/ddoc.git
cd ddoc
pip install -e .
```

### 플러그인과 함께 설치

```bash
# YOLO 플러그인 포함
pip install ddoc[yolo]

# Vision 플러그인 포함
pip install ddoc[vision]
```

## 의존성 설치

### Git 설치

**macOS:**
```bash
brew install git
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install git
```

**Windows:**
[Git for Windows](https://git-scm.com/download/win) 다운로드 및 설치

### DVC 설치

```bash
pip install dvc
```

또는 conda를 사용하는 경우:
```bash
conda install -c conda-forge dvc
```

## 설치 확인

설치가 완료되면 다음 명령어로 확인할 수 있습니다:

```bash
ddoc --version
```

또는:

```bash
ddoc --help
```

## 다음 단계

설치가 완료되었다면:
1. [빠른 시작](quick-start.md)으로 기본 사용법 익히기
2. [핵심 개념](concepts.md)으로 ddoc 이해하기

