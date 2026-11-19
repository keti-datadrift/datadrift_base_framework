# Changelog - ddoc

> **참고**: 각 버전의 상세 릴리스 노트는 [releases/](releases/) 디렉토리에서 확인할 수 있습니다.

## [3.0.0] - Unreleased

### 🩺 판정 도구로 집중 — 하위 호환이 깨지는 릴리스

**주요 변경사항:**
- ✨ `ddoc diff` 한 줄 판정 (OK / DRIFT / BLIND), `--report` HTML 소견서, Drift Zoo, GitHub Action
- ✨ `ddoc serve` (REST + GUI), `recipe`, `report`, `export`, `fetch`, `examples` 명령
- 🗑️ `init` / `add` / `snapshot`, 스냅샷 모드, `exp` / `train`, `ingest`, `vis`, v1 legacy 명령 제거
- 🗑️ yolo / vis / nlp / reference-engine / keti-temporal 플러그인, 관련 hookspec 과 extras 제거 (hookspec 2.0.0)
- 🐛 플러그인 하나의 실패가 다른 플러그인 결과를 지우던 문제, 일반 설치에서 `examples generate` 가 실패하던 문제 수정
- 🔄 `ddoc/`, `plugins/` 를 저장소 최상위로 이동

> 📖 **상세 내역**: [v3.0.0 릴리스 노트](releases/v3.0.0.md)

---

## [2.1.0] - 2025-12-30

### 🎯 Multi-Modal Analysis - 멀티모달 분석 기능 추가

**주요 변경사항:**
- ✨ 이미지/텍스트/시계열/오디오 멀티모달 분석 지원
- ✨ 이미지 속성 지표 9종 구현 및 속성 드리프트 개선
- ✨ 텍스트 분석 플러그인 신규 추가 (CSV + CLIP 텍스트 임베딩)
- ✨ 시계열 분석 플러그인 신규 추가 (숫자형/범주형 지표)
- ✨ 오디오 분석 플러그인 신규 추가 (물리 기반 특징)
- ✨ 캐시 네임스페이싱으로 모달리티별 독립 캐시 관리
- ✨ ddoc-full 메타패키지로 모든 플러그인 통합 설치
- 🗑️ Builtin 텍스트 단일파일 fallback 훅 제거

> 📖 **상세 내역**: [v2.1.0 릴리스 노트](releases/v2.1.0.md)

---

## [2.0.4] - 2025-12-23

### 🧩 Snapshot 안정화 및 CLI 개편

**주요 변경사항:**
- 🐛 초기 워크스페이스에서 스냅샷 생성 실패(`data.dvc not found`) 문제 해결
- 🐛 스냅샷 체크아웃 시 `.ddoc` 변경으로 인해 Git checkout이 실패하는 문제 개선
- 🧹 체크아웃 후 `data/` 하위 빈 디렉터리 및 `.DS_Store` 잔재 자동 정리
- 🔄 `snapshot` 명령을 하이브리드 구조로 개편 (핵심 서브커맨드 + 부가 옵션)

> 📖 **상세 내역**: [v2.0.4 릴리스 노트](releases/v2.0.4.md)

---

## [2.0.3] - 2024-12-04

### 🎯 Experiment 명령 개편 - Trainer 기반 실험 시스템

기존 YOLO 전용 `exp run` 명령을 범용 Trainer 기반 시스템으로 완전히 개편했습니다.

**주요 변경사항:**
- ✨ Trainer 기반 실험 시스템 (`ddoc exp train`, `ddoc exp eval`, `ddoc exp best`)
- ✨ Trainer 인터페이스 표준화 (`code/trainers/{name}/train.py`, `eval.py`)
- 🔄 `ddoc exp run` → `ddoc exp train`으로 대체 (deprecated)
- 📦 `ddoc/core/trainer_service.py` 신규 모듈 추가

> 📖 **상세 내역**: [v2.0.3 릴리스 노트](releases/v2.0.3.md)

---

## [2.0.2] - 2025-11-25

### 🎯 워크스페이스 캐시 동기화 및 증분 분석 안정화

**주요 변경사항:**
- ✨ Workspace Cache Synchronization (자동 캐시 동기화)
- 🐛 증분 분석 빈 캐시 문제 해결 (Critical)
- 🐛 Drift 분석 캐시 타입 오류 수정
- 📦 하이브리드 캐시 구조 (파일 시스템 + SQLite)

> 📖 **상세 내역**: [v2.0.2 릴리스 노트](releases/v2.0.2.md)

---

## [2.0.1] - 2025-11-17

### 🚀 성능 및 개발자 경험 개선

**주요 변경사항:**
- ⚡ CLI 시작 속도 21배 향상
- ⚡ 플러그인 목록 조회 21.8배 향상
- 📁 CLI 모듈화 (2,767줄 → 평균 120줄)
- 🛠️ 압축 파일 해제 수정

> 📖 **상세 내역**: [v2.0.1 릴리스 노트](releases/v2.0.1.md)

---

## [2.0.0] - 2025-11-14

### 🎉 Major Release - Complete System Overhaul

ddoc v2.0.0은 완전히 새로운 아키텍처로 재설계되었습니다.

**주요 변경사항:**
- ✨ Git-like 워크플로우 (commit, checkout, log, diff)
- ✨ Snapshot-based 버전 관리
- ✨ 자동 프로젝트 스캐폴딩
- ⚠️ Breaking Changes: 명령어 구조 전면 변경

> 📖 **상세 내역**: [v2.0.0 릴리스 노트](releases/v2.0.0.md)

---

**전체 릴리스 노트**: [releases/](releases/) 디렉토리 참조

