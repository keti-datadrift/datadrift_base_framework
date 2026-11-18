# Changelog - ddoc-plugin-vision

## [0.2.1] - 2025-11-25

### 🔧 Bug Fixes & Improvements

#### Drift Detection 개선
- **캐시 로드 메커니즘 업데이트**: ddoc v2.0.2의 새로운 캐시 구조에 맞춰 업데이트
- **Attributes 캐시 사용**: `baseline_cache`와 `current_cache`가 attributes 데이터를 올바르게 사용
- **Summary 캐시 저장 추가**: Drift 분석 완료 후 summary 캐시 저장하여 향후 분석 효율성 향상

#### 증분 분석 안정화
- **빈 캐시 문제 해결**: 데이터 변경 후 removed 파일 처리 시 빈 캐시가 생성되는 문제 수정
- **상대 경로 기반 파일 키**: 다중 데이터셋 및 중첩 디렉토리 구조 지원
- **파일 메타데이터 추적**: `FileMetadata` 스키마 기반 증분 분석

### 🔄 Changed

#### 캐시 통합
- **자체 캐시 매니저 제거**: ddoc core의 `CacheService` 직접 사용
- **데이터 해시 기반 저장**: `.ddoc/cache/data/{data_hash}/` 구조 사용
- **SQLite 인덱싱 지원**: 빠른 캐시 조회 및 중복 제거

### 📦 Dependencies

- ddoc >= 2.0.2 (필수)
- 기존 의존성 유지

### 🔧 Technical Details

#### Hook 구현 업데이트
- `eda_run()`: `data_hash` 파라미터 추가, 증분 분석 지원
- `drift_detect()`: `data_hash_ref`, `data_hash_cur` 파라미터 추가

#### 분석 결과 저장
```python
# Summary 캐시 저장 (drift 분석용)
cache_service.save_analysis_cache(
    snapshot_id=snapshot_id,
    data_hash=data_hash,
    cache_type="summary",
    data={
        "statistics": {...},
        "distributions": {...}
    }
)
```

---

## [0.2.0] - 2025-11-24

### 🎯 Major Update - ddoc v2.0 Integration

#### ddoc v2.0 호환성
- 새로운 hook 시그니처 지원
- 스냅샷 기반 분석 지원
- 데이터 해시 기반 캐시 관리

#### Ensemble Drift Detection
- Multi-scale MMD
- Mean Shift
- Wasserstein Distance
- PSI (Population Stability Index)
- Cosine Distance
- 가중치 기반 앙상블 스코어

#### 증분 분석 지원
- 파일 단위 메타데이터 추적
- 변경된 파일만 재분석
- 캐시 효율성 향상

---

## [0.1.x] - Legacy

초기 버전 (ddoc v1.x 호환)

