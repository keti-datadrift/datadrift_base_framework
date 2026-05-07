"""Legacy in-process drift analysis (pre-Phase 3 — orchestrator pivot).

This module duplicates analytical logic that the ``ddoc-plugin-vision`` /
``ddoc-plugin-yolo`` pluggy hooks already provide. It is kept behind the
``BACKEND_USE_DDOC_CLI`` feature flag for one release so operators can
fall back if the subprocess path regresses, and will be removed once the
flag flips to default-on.

Set ``BACKEND_USE_DDOC_CLI=true`` in the backend env to route ``/drift``
through ``ddoc analyze drift --data-path-ref ... --data-path-cur ...
--json`` instead of ``run_drift`` here. See
``_specs/architecture_consolidation.md`` Round-2 for the rationale.
"""
import os
import json
import warnings

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from scipy import stats

from app.services.zip_resolver import analyze_zip_dataset, analyze_roboflow
from app.utils.json_sanitize import clean_json_value
from app.services.eda_service import run_image_analysis, collect_image_files

# Phase 3 — module-load DeprecationWarning so the migration nudge surfaces
# once in container logs (DeprecationWarning is silent by default; backend
# main.py / pytest config can enable it).
warnings.warn(
    "drift_service.run_drift is the legacy in-process path. "
    "Set BACKEND_USE_DDOC_CLI=true to route /drift via the ddoc CLI subprocess.",
    DeprecationWarning,
    stacklevel=2,
)
from app.services.analyzer_init import get_analyzer_service


# 드리프트 상태 임계값
THRESHOLD_WARNING = 0.15
THRESHOLD_CRITICAL = 0.25


# ============================================================
# ZIP vs ZIP DRIFT
# ============================================================

def compute_zip_drift(base_info, target_info):
    """
    ZIP dataset drift:
        - split distribution 변화
        - class distribution 변화
        - annotation 수 변화
        - 디렉토리 구조 변화
        - 이미지 수 변화
    """

    zip_type = base_info.get("zip_type")

    drift = {
        "zip_type": zip_type,
        "structure": {},
        "splits": {},
        "classes": {},
        "summary": {},
    }

    # ----------------------------------------------------------
    # 1. 구조 비교
    # ----------------------------------------------------------
    drift["structure"] = {
        "base_subdirs": base_info["stats"].get("subdirs", []),
        "target_subdirs": target_info["stats"].get("subdirs", []),
    }

    # ----------------------------------------------------------
    # 2. Roboflow ZIP Drift
    # ----------------------------------------------------------
    if zip_type == "roboflow":
        b = analyze_roboflow(base_info)
        t = analyze_roboflow(target_info)

        # split drift
        split_names = ["train", "valid", "test"]
        for s in split_names:
            drift["splits"][s] = {
                "base": b["splits"][s]["num_images"],
                "target": t["splits"][s]["num_images"],
                "delta": t["splits"][s]["num_images"] - b["splits"][s]["num_images"],
            }

        # class drift
        all_classes = set(b["classes"]) | set(t["classes"])
        for c in all_classes:
            base_cnt = sum([b["splits"][s]["class_counts"].get(c, 0) for s in split_names])
            target_cnt = sum([t["splits"][s]["class_counts"].get(c, 0) for s in split_names])

            drift["classes"][c] = {
                "base": base_cnt,
                "target": target_cnt,
                "delta": target_cnt - base_cnt,
            }

        drift["summary"] = {
            "total_images_base": sum([b["splits"][s]["num_images"] for s in split_names]),
            "total_images_target": sum([t["splits"][s]["num_images"] for s in split_names]),
        }

        return drift

    # ----------------------------------------------------------
    # 3. 일반 YOLO / COCO / VOC Drift (단순 통계)
    # ----------------------------------------------------------
    # 이미지 개수 변화
    drift["summary"]["base_images"] = base_info["stats"]["image_files"]
    drift["summary"]["target_images"] = target_info["stats"]["image_files"]
    drift["summary"]["delta_images"] = (
        target_info["stats"]["image_files"] - base_info["stats"]["image_files"]
    )

    # 텍스트/annotation 변화
    drift["summary"]["base_text"] = base_info["stats"]["text_files"]
    drift["summary"]["target_text"] = target_info["stats"]["text_files"]
    drift["summary"]["delta_text"] = (
        target_info["stats"]["text_files"] - base_info["stats"]["text_files"]
    )

    return drift


# ============================================================
# CSV vs CSV DRIFT
# ============================================================

def compute_csv_drift(base_path, target_path):
    print('base_path = ', base_path)
    print('target_path = ', target_path)
    df1 = pd.read_csv(base_path)
    df2 = pd.read_csv(target_path)
    print(df1)
    print(df2)

    # 수치형 컬럼만 비교
    numeric_cols = [c for c in df1.columns if pd.api.types.is_numeric_dtype(df1[c])]

    drift = {}

    for col in numeric_cols:
        mean1 = df1[col].mean()
        mean2 = df2[col].mean()
        drift[col] = {
            "base_mean": None if pd.isna(mean1) else round(float(mean1), 4),
            "target_mean": None if pd.isna(mean2) else round(float(mean2), 4),
            "delta": None if pd.isna(mean1) or pd.isna(mean2) else round(float(mean2 - mean1), 4),
        }
    print('drift = ', drift)

    return drift


# ============================================================
# ZIP vs CSV / TEXT vs CSV / unsupported
# ============================================================

def run_drift(
    base_path, 
    target_path, 
    base_cache: Optional[Dict[str, Any]] = None,
    target_cache: Optional[Dict[str, Any]] = None
):
    """
    base_path, target_path:
        ZIP → dataset_dir (폴더)
        CSV/TXT/IMAGE → 단일 파일
        
    base_cache, target_cache:
        EDA 결과 캐시 (image_analysis, clustering 포함)
        드리프트 분석 시 재사용하여 속도 향상
    """

    # -------------------
    # ZIP vs ZIP
    # -------------------
    if os.path.isdir(base_path) and os.path.isdir(target_path):
        # raw.zip 찾기
        def locate_raw_zip(path):
            for f in os.listdir(path):
                if f.lower().endswith(".zip"):
                    return os.path.join(path, f)
            return None

        base_zip = locate_raw_zip(base_path)
        target_zip = locate_raw_zip(target_path)

        if not base_zip or not target_zip:
            raise RuntimeError("ZIP dataset drift: raw.zip 파일을 찾을 수 없습니다.")

        base_info = analyze_zip_dataset(base_zip)
        target_info = analyze_zip_dataset(target_zip)

        result = compute_zip_drift(base_info, target_info)
        result["type"] = "zip_zip"
        
        # 이미지 속성/임베딩 기반 고급 드리프트 분석 추가 (캐시 사용)
        try:
            advanced_drift = compute_advanced_image_drift(
                base_info.get("root_dir"),
                target_info.get("root_dir"),
                base_cache=base_cache,
                target_cache=target_cache
            )
            if advanced_drift:
                result["advanced_drift"] = advanced_drift
        except Exception as e:
            print(f"⚠️ 고급 드리프트 분석 실패: {e}")
        
        return clean_json_value(result)

    # -------------------
    # CSV vs CSV
    # -------------------
    if base_path.endswith(".csv") and target_path.endswith(".csv"):
        result = compute_csv_drift(base_path, target_path)
        return clean_json_value({"type": "csv_csv", "drift": result})

    # -------------------
    # 다른 조합은 미지원 (향후 추가 가능)
    # -------------------
    return clean_json_value({
        "type": "unsupported",
        "message": f"Drift not supported between {base_path} and {target_path}"
    })


# ============================================================
# 고급 이미지 드리프트 분석 (앙상블 메트릭)
# ============================================================

def compute_advanced_image_drift(
    base_dir: str, 
    target_dir: str,
    base_cache: Optional[Dict[str, Any]] = None,
    target_cache: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    두 이미지 데이터셋 간의 고급 드리프트 분석을 수행합니다.
    
    EDA 캐시가 있으면 재사용하여 속도를 크게 향상시킵니다.
    
    분석 메트릭:
    - 속성 드리프트: KL Divergence (크기, 노이즈, 선명도)
    - 임베딩 드리프트: MMD, Mean Shift, Wasserstein, PSI
    - 앙상블 점수 및 상태 판정
    
    Args:
        base_dir: 기준 데이터셋 디렉토리
        target_dir: 비교 대상 데이터셋 디렉토리
        base_cache: 기준 데이터셋의 EDA 캐시 (image_analysis, clustering)
        target_cache: 비교 데이터셋의 EDA 캐시
        
    Returns:
        dict: 드리프트 분석 결과
    """
    if not base_dir or not target_dir:
        return None
    
    if not os.path.isdir(base_dir) or not os.path.isdir(target_dir):
        return None
    
    print(f"🔍 고급 드리프트 분석 시작")
    print(f"   Base: {base_dir}")
    print(f"   Target: {target_dir}")
    
    # 캐시 사용 여부 로깅
    base_attrs_cached = base_cache and base_cache.get("image_analysis")
    target_attrs_cached = target_cache and target_cache.get("image_analysis")
    base_embs_cached = base_cache and base_cache.get("clustering") and base_cache["clustering"].get("embeddings")
    target_embs_cached = target_cache and target_cache.get("clustering") and target_cache["clustering"].get("embeddings")
    
    if base_attrs_cached:
        print("   ✅ Base 속성 데이터: 캐시 사용")
    if target_attrs_cached:
        print("   ✅ Target 속성 데이터: 캐시 사용")
    if base_embs_cached:
        print("   ✅ Base 임베딩 데이터: 캐시 사용")
    if target_embs_cached:
        print("   ✅ Target 임베딩 데이터: 캐시 사용")
    
    # ============================================================
    # 1. 속성 데이터 준비 (캐시 또는 새로 분석)
    # ============================================================
    base_attrs = {}
    target_attrs = {}
    
    if base_attrs_cached:
        # 캐시에서 속성 데이터 로드
        base_attrs = base_cache["image_analysis"].get("attributes", {})
    else:
        # 새로 분석
        print("   📊 Base 속성 분석 중...")
        base_images = collect_image_files(base_dir)
        analyzer = get_analyzer_service()
        for img in base_images:
            rel_path = os.path.relpath(img, base_dir)
            attrs = analyzer.analyze_image_attributes(img)
            if attrs:
                base_attrs[rel_path] = attrs
    
    if target_attrs_cached:
        # 캐시에서 속성 데이터 로드
        target_attrs = target_cache["image_analysis"].get("attributes", {})
    else:
        # 새로 분석
        print("   📊 Target 속성 분석 중...")
        target_images = collect_image_files(target_dir)
        analyzer = get_analyzer_service()
        for img in target_images:
            rel_path = os.path.relpath(img, target_dir)
            attrs = analyzer.analyze_image_attributes(img)
            if attrs:
                target_attrs[rel_path] = attrs
    
    if not base_attrs or not target_attrs:
        print("   ⚠️ 속성 분석 결과가 없습니다.")
        return None
    
    # 2. 속성 드리프트 (KL Divergence)
    attribute_drift = compute_attribute_drift(base_attrs, target_attrs)
    
    # ============================================================
    # 3. 임베딩 데이터 준비 (캐시 또는 새로 추출)
    # ============================================================
    embedding_drift = None
    
    if len(base_attrs) >= 5 and len(target_attrs) >= 5:
        base_embs = []
        target_embs = []
        
        # Base 임베딩
        if base_embs_cached:
            base_embs = base_cache["clustering"]["embeddings"]
            print(f"   📦 Base 임베딩 캐시 로드: {len(base_embs)}개")
        else:
            print("   🔬 Base 임베딩 추출 중...")
            base_images = collect_image_files(base_dir)
            analyzer = get_analyzer_service()
            for img in base_images:
                emb = analyzer.extract_embedding(img)
                if emb and 'embedding' in emb:
                    base_embs.append(emb['embedding'])
        
        # Target 임베딩
        if target_embs_cached:
            target_embs = target_cache["clustering"]["embeddings"]
            print(f"   📦 Target 임베딩 캐시 로드: {len(target_embs)}개")
        else:
            print("   🔬 Target 임베딩 추출 중...")
            target_images = collect_image_files(target_dir)
            analyzer = get_analyzer_service()
            for img in target_images:
                emb = analyzer.extract_embedding(img)
                if emb and 'embedding' in emb:
                    target_embs.append(emb['embedding'])
        
        if len(base_embs) >= 5 and len(target_embs) >= 5:
            embedding_drift = compute_embedding_drift(
                np.array(base_embs), 
                np.array(target_embs)
            )
    
    # 4. 앙상블 점수 계산
    ensemble_result = compute_ensemble_drift_score(attribute_drift, embedding_drift)
    
    result = {
        "file_counts": {
            "base": len(base_attrs),
            "target": len(target_attrs),
        },
        "attribute_drift": attribute_drift,
        "embedding_drift": embedding_drift,
        "ensemble": ensemble_result,
        "cache_used": {
            "base_attributes": bool(base_attrs_cached),
            "target_attributes": bool(target_attrs_cached),
            "base_embeddings": bool(base_embs_cached),
            "target_embeddings": bool(target_embs_cached),
        }
    }
    
    print(f"✅ 고급 드리프트 분석 완료")
    print(f"   전체 점수: {ensemble_result['overall_score']:.4f}")
    print(f"   상태: {ensemble_result['status']}")
    
    return result


def compute_attribute_drift(base_attrs: Dict, target_attrs: Dict) -> Dict[str, Any]:
    """
    속성 분포 간 드리프트를 계산합니다.
    
    메트릭: KL Divergence
    """
    # 속성값 추출
    base_sizes = [v['size'] for v in base_attrs.values() if 'size' in v]
    target_sizes = [v['size'] for v in target_attrs.values() if 'size' in v]
    
    base_noise = [v['noise_level'] for v in base_attrs.values() if 'noise_level' in v]
    target_noise = [v['noise_level'] for v in target_attrs.values() if 'noise_level' in v]
    
    base_sharp = [v['sharpness'] for v in base_attrs.values() if 'sharpness' in v]
    target_sharp = [v['sharpness'] for v in target_attrs.values() if 'sharpness' in v]
    
    drift = {}
    
    # KL Divergence 계산
    if base_sizes and target_sizes:
        drift['size'] = {
            'kl_divergence': calculate_kl_divergence(base_sizes, target_sizes),
            'base_mean': round(float(np.mean(base_sizes)), 4),
            'target_mean': round(float(np.mean(target_sizes)), 4),
            'base_std': round(float(np.std(base_sizes)), 4),
            'target_std': round(float(np.std(target_sizes)), 4),
        }
    
    if base_noise and target_noise:
        drift['noise'] = {
            'kl_divergence': calculate_kl_divergence(base_noise, target_noise),
            'base_mean': round(float(np.mean(base_noise)), 4),
            'target_mean': round(float(np.mean(target_noise)), 4),
            'base_std': round(float(np.std(base_noise)), 4),
            'target_std': round(float(np.std(target_noise)), 4),
        }
    
    if base_sharp and target_sharp:
        drift['sharpness'] = {
            'kl_divergence': calculate_kl_divergence(base_sharp, target_sharp),
            'base_mean': round(float(np.mean(base_sharp)), 4),
            'target_mean': round(float(np.mean(target_sharp)), 4),
            'base_std': round(float(np.std(base_sharp)), 4),
            'target_std': round(float(np.std(target_sharp)), 4),
        }
    
    # 히스토그램 데이터 (시각화용)
    drift['distributions'] = {
        'size': create_comparison_histogram(base_sizes, target_sizes, 20),
        'noise': create_comparison_histogram(base_noise, target_noise, 20),
        'sharpness': create_comparison_histogram(base_sharp, target_sharp, 20),
    }
    
    return drift


def compute_embedding_drift(base_embs: np.ndarray, target_embs: np.ndarray) -> Dict[str, Any]:
    """
    임베딩 공간에서의 드리프트를 계산합니다.
    
    메트릭:
    - MMD (Maximum Mean Discrepancy)
    - Mean Shift
    - Wasserstein Distance
    - PSI (Population Stability Index)
    """
    drift = {}
    
    # 1. MMD
    drift['mmd'] = calculate_mmd(base_embs, target_embs)
    
    # 2. Mean Shift
    base_mean = base_embs.mean(axis=0)
    target_mean = target_embs.mean(axis=0)
    mean_shift = np.linalg.norm(base_mean - target_mean)
    drift['mean_shift'] = round(float(mean_shift / np.sqrt(base_embs.shape[1])), 4)
    
    # 3. Wasserstein Distance (1D projection)
    try:
        proj_base = base_embs.mean(axis=1)
        proj_target = target_embs.mean(axis=1)
        drift['wasserstein'] = round(float(stats.wasserstein_distance(proj_base, proj_target)), 4)
    except Exception:
        drift['wasserstein'] = 0.0
    
    # 4. PSI on PCA components
    try:
        from sklearn.decomposition import PCA
        n_components = min(5, base_embs.shape[1], base_embs.shape[0], target_embs.shape[0])
        pca = PCA(n_components=n_components)
        base_pca = pca.fit_transform(base_embs)
        target_pca = pca.transform(target_embs)
        
        psi_scores = []
        for dim in range(n_components):
            psi = calculate_psi(base_pca[:, dim], target_pca[:, dim])
            psi_scores.append(psi)
        
        drift['psi'] = round(float(np.mean(psi_scores)), 4)
        drift['psi_max'] = round(float(np.max(psi_scores)), 4)
    except Exception:
        drift['psi'] = 0.0
        drift['psi_max'] = 0.0
    
    # 5. Cosine Distance
    base_mean_norm = np.linalg.norm(base_mean)
    target_mean_norm = np.linalg.norm(target_mean)
    if base_mean_norm > 0 and target_mean_norm > 0:
        cos_sim = np.dot(base_mean, target_mean) / (base_mean_norm * target_mean_norm)
        drift['cosine_distance'] = round(float(max(0, 1 - cos_sim)), 4)
    else:
        drift['cosine_distance'] = 0.0
    
    return drift


def compute_ensemble_drift_score(
    attribute_drift: Optional[Dict], 
    embedding_drift: Optional[Dict]
) -> Dict[str, Any]:
    """
    속성 및 임베딩 드리프트를 종합한 앙상블 점수를 계산합니다.
    """
    scores = {}
    weights = {}
    
    # 속성 드리프트 점수
    if attribute_drift:
        for attr in ['size', 'noise', 'sharpness']:
            if attr in attribute_drift:
                kl = attribute_drift[attr].get('kl_divergence', 0)
                # KL을 0-1 범위로 정규화
                scores[f'attr_{attr}'] = min(kl / 0.5, 1.0)
                weights[f'attr_{attr}'] = 0.1
    
    # 임베딩 드리프트 점수
    if embedding_drift:
        # MMD
        if 'mmd' in embedding_drift:
            scores['emb_mmd'] = min(embedding_drift['mmd'] / 0.5, 1.0)
            weights['emb_mmd'] = 0.25
        
        # Mean Shift
        if 'mean_shift' in embedding_drift:
            scores['emb_mean_shift'] = min(embedding_drift['mean_shift'] / 0.1, 1.0)
            weights['emb_mean_shift'] = 0.2
        
        # Wasserstein
        if 'wasserstein' in embedding_drift:
            scores['emb_wasserstein'] = min(embedding_drift['wasserstein'] / 1.0, 1.0)
            weights['emb_wasserstein'] = 0.15
        
        # PSI
        if 'psi' in embedding_drift:
            scores['emb_psi'] = min(embedding_drift['psi'] / 0.25, 1.0)
            weights['emb_psi'] = 0.1
    
    # 가중 평균
    if scores and weights:
        total_weight = sum(weights.values())
        overall_score = sum(scores[k] * weights[k] for k in scores) / total_weight
    else:
        overall_score = 0.0
    
    # 상태 판정
    if overall_score < THRESHOLD_WARNING:
        status = "NORMAL"
    elif overall_score < THRESHOLD_CRITICAL:
        status = "WARNING"
    else:
        status = "CRITICAL"
    
    return {
        "overall_score": round(overall_score, 4),
        "status": status,
        "component_scores": {k: round(v, 4) for k, v in scores.items()},
        "weights": weights,
        "thresholds": {
            "warning": THRESHOLD_WARNING,
            "critical": THRESHOLD_CRITICAL,
        }
    }


# ============================================================
# 유틸리티 함수
# ============================================================

def calculate_kl_divergence(p: List[float], q: List[float], bins: int = 20) -> float:
    """KL Divergence를 계산합니다."""
    try:
        # 공통 범위 결정
        min_val = min(min(p), min(q))
        max_val = max(max(p), max(q))
        
        # 히스토그램 계산
        p_hist, edges = np.histogram(p, bins=bins, range=(min_val, max_val), density=True)
        q_hist, _ = np.histogram(q, bins=edges, density=True)
        
        # 0 방지
        p_hist = p_hist + 1e-10
        q_hist = q_hist + 1e-10
        
        # 정규화
        p_hist = p_hist / p_hist.sum()
        q_hist = q_hist / q_hist.sum()
        
        # KL Divergence
        kl = float(np.sum(p_hist * np.log(p_hist / q_hist)))
        return round(abs(kl), 4)
    except Exception:
        return 0.0


def calculate_mmd(X: np.ndarray, Y: np.ndarray, gamma: float = 1.0) -> float:
    """Maximum Mean Discrepancy를 계산합니다."""
    try:
        # 샘플 크기 제한
        if X.shape[0] > 500:
            X = X[:500]
        if Y.shape[0] > 500:
            Y = Y[:500]
        
        # 정규화
        X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-8)
        Y = (Y - Y.mean(axis=0)) / (Y.std(axis=0) + 1e-8)
        
        XX = np.dot(X, X.T)
        YY = np.dot(Y, Y.T)
        XY = np.dot(X, Y.T)
        
        X_sqnorms = np.diagonal(XX)
        Y_sqnorms = np.diagonal(YY)
        
        def rbf_kernel(X_sqnorms, Y_sqnorms, XY):
            K = -2 * XY + X_sqnorms[:, None] + Y_sqnorms[None, :]
            K = np.clip(K, -50, 50)
            return np.exp(-gamma * K)
        
        K_XX = rbf_kernel(X_sqnorms, X_sqnorms, XX)
        K_YY = rbf_kernel(Y_sqnorms, Y_sqnorms, YY)
        K_XY = rbf_kernel(X_sqnorms, Y_sqnorms, XY)
        
        m = X.shape[0]
        n = Y.shape[0]
        
        mmd = np.sum(np.triu(K_XX, k=1)) / (m * (m - 1) / 2)
        mmd += np.sum(np.triu(K_YY, k=1)) / (n * (n - 1) / 2)
        mmd -= 2 * K_XY.sum() / (m * n)
        
        return round(float(np.sqrt(max(mmd, 0))), 4)
    except Exception:
        return 0.0


def calculate_psi(baseline: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index를 계산합니다."""
    try:
        min_val = min(baseline.min(), current.min())
        max_val = max(baseline.max(), current.max())
        edges = np.linspace(min_val, max_val, bins + 1)
        
        baseline_hist, _ = np.histogram(baseline, bins=edges)
        current_hist, _ = np.histogram(current, bins=edges)
        
        baseline_prop = (baseline_hist + 1) / (baseline_hist.sum() + bins)
        current_prop = (current_hist + 1) / (current_hist.sum() + bins)
        
        psi = np.sum((current_prop - baseline_prop) * np.log(current_prop / baseline_prop))
        return round(float(abs(psi)), 4)
    except Exception:
        return 0.0


def create_comparison_histogram(
    base_data: List[float], 
    target_data: List[float], 
    bins: int = 20
) -> Dict[str, Any]:
    """비교용 히스토그램 데이터를 생성합니다."""
    if not base_data or not target_data:
        return {}
    
    try:
        min_val = min(min(base_data), min(target_data))
        max_val = max(max(base_data), max(target_data))
        
        base_hist, edges = np.histogram(base_data, bins=bins, range=(min_val, max_val))
        target_hist, _ = np.histogram(target_data, bins=edges)
        
        bin_centers = [(edges[i] + edges[i+1]) / 2 for i in range(len(base_hist))]
        
        return {
            "bins": [round(b, 4) for b in bin_centers],
            "base": base_hist.tolist(),
            "target": target_hist.tolist(),
        }
    except Exception:
        return {}