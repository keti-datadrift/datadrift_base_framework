# 설치 가이드

## 요구사항

- **Python**: 3.9 이상 (코어 단독은 3.8 이상)
- PDF 리포트를 만들려면 weasyprint 가 쓰는 시스템 라이브러리
  (pango, cairo) 가 필요합니다. HTML / Markdown 리포트에는 필요 없습니다.

## 설치

저장소 루트에서:

```bash
pip install -e packages/ddoc
```

코어만으로 `ddoc diff` 가 생 CSV 를 비교할 수 있습니다.
다른 데이터를 다루려면 modality 플러그인을 추가합니다:

```bash
pip install -e packages/plugins/ddoc-plugin-categorical   # 범주형 분포
pip install -e packages/plugins/ddoc-plugin-tabular       # 표 데이터
pip install -e packages/plugins/ddoc-plugin-timeseries    # 시계열
pip install -e packages/plugins/ddoc-plugin-text          # 텍스트
pip install -e packages/plugins/ddoc-plugin-audio         # 오디오
pip install -e packages/plugins/ddoc-plugin-vision        # 이미지 (torch 필요)
pip install -e packages/plugins/ddoc-plugin-evidently     # Evidently 기반 검출기
```

기본 플러그인 묶음을 한 번에 설치하려면 `packages/plugins/ddoc-full/install_dev.sh`
를 실행합니다.

테스트 의존성:

```bash
pip install -e "ddoc[test]"
```

## 설치 확인

```bash
ddoc --version
ddoc plugin list
```

## 다음 단계

1. [빠른 시작](quick-start.md)으로 기본 사용법 익히기
2. [핵심 개념](concepts.md)으로 ddoc 이해하기
