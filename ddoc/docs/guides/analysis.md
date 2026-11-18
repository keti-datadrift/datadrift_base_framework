# 데이터 분석

ddoc는 EDA(탐색적 데이터 분석) 및 데이터 드리프트 감지 기능을 제공합니다.

## EDA (탐색적 데이터 분석)

### `ddoc analyze eda`

현재 워크스페이스의 데이터에 대한 탐색적 데이터 분석을 수행합니다.

```bash
ddoc analyze eda
```

**기능:**
- 데이터 속성 분석
- 임베딩 생성
- 클러스터링
- 시각화

**캐시 시스템:**
- 분석 결과는 자동으로 캐시됩니다
- 데이터 변경 시 증분 분석을 수행합니다
- 동일한 데이터 해시는 캐시를 재사용합니다

## Drift 감지

### `ddoc analyze drift`

두 스냅샷 간 데이터 드리프트를 분석합니다.

```bash
ddoc analyze drift <version1> <version2>
```

**예시:**
```bash
ddoc analyze drift baseline production
ddoc analyze drift v01 v05
```

**분석 항목:**
- 속성 드리프트 (KL Divergence 기반)
- 임베딩 드리프트 (MMD - Maximum Mean Discrepancy)
- 파일 변경사항 (추가/삭제/수정)

**출력:**
- 드리프트 리포트 (JSON)
- 시각화 차트 (8종류)
- 통계 요약

## 스냅샷 기반 분석

특정 스냅샷에 대한 분석도 가능합니다:

```bash
# 특정 스냅샷 분석
ddoc analyze eda <snapshot_id>

# 분석 후 자동 스냅샷 생성
ddoc analyze eda --save-snapshot
```

## 캐시 활용

ddoc는 분석 결과를 캐시하여 성능을 최적화합니다:

```bash
# 첫 분석 (전체 분석 수행)
ddoc analyze eda

# 데이터 일부 변경 후 재분석 (증분 분석)
ddoc analyze eda  # 변경된 파일만 재분석
```

## 다음 단계

- [스냅샷 관리](snapshots.md) - 스냅샷 생성 및 관리
- [실험 관리](experiments.md) - 실험 실행 및 추적
- [고급 워크플로우](../advanced/workflows.md) - 고급 사용법

