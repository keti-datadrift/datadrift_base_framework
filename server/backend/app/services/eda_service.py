import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.utils.json_sanitize import clean_json_value
from app.services.zip_resolver import (
    analyze_zip_dataset,
    analyze_roboflow,
    analyze_yolo,
    analyze_voc,
    analyze_coco,
)
from app.services.analyzer_init import get_analyzer_service

# 이미지 확장자
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff'}


def run_eda(file_path: str, dtype: str = "csv") -> dict:
    """
    file_path:
        CSV → raw.csv
        ZIP → dvc_storage/datasets/<id>/   (폴더)
        TEXT → raw.txt
        IMAGE → raw.png

    dtype: csv | zip | text | image | unknown
    """
    dtype = dtype.lower()

    # =========================================================
    # ZIP DATASET EDA
    # =========================================================
    if dtype == "zip":
        # file_path = dvc_storage/datasets/<id>/
        dataset_dir = file_path

        # raw.zip 찾기
        raw_zip = None
        for f in os.listdir(dataset_dir):
            if f.lower().endswith(".zip"):
                raw_zip = os.path.join(dataset_dir, f)
                break

        if not raw_zip:
            raise RuntimeError(f"ZIP Dataset EDA: raw.zip 파일을 찾을 수 없음: {dataset_dir}")

        # ZIP 분석 (roboflow/yolo/voc/coco 자동 감지)
        info = analyze_zip_dataset(raw_zip)

        zip_type = info.get("zip_type", "unknown")

        result = {
            "type": "zip",
            "zip_type": zip_type,
            "tree": info.get("tree"),
            "stats": info.get("stats"),
            "images": info.get("images", []),
        }

        # -----------------------
        # Roboflow EDA
        # -----------------------
        if zip_type == "roboflow":
            result["roboflow"] = analyze_roboflow(info)

        # -----------------------
        # YOLO EDA
        # -----------------------
        elif zip_type == "yolo":
            result["yolo"] = analyze_yolo(info)

        # -----------------------
        # VOC EDA
        # -----------------------
        elif zip_type == "voc":
            result["voc"] = analyze_voc(info)

        # -----------------------
        # COCO EDA
        # -----------------------
        elif zip_type == "coco":
            result["coco"] = analyze_coco(info)

        # 심층 분석 (이미지 속성, 임베딩, 클러스터링)은 별도 API로 분리
        # /eda/{id}/image-analysis 및 /eda/{id}/clustering 참조
        result["root_dir"] = info.get("root_dir")  # 심층 분석용 경로 저장

        return clean_json_value(result)

    # =========================================================
    # CSV EDA
    # =========================================================
    if dtype == "csv":
        df = pd.read_csv(file_path)

        # inf → NaN
        df = df.replace([np.inf, -np.inf], np.nan)

        # NaN → "" (Pandas v2에서 None 불가)
        df = df.fillna("")

        # Preview (5 rows)
        preview = df.head(5).to_dict(orient="records")

        # Summary
        summary = df.describe(include="all").replace({np.nan: None}).to_dict()

        # Missing rate
        missing_rate = (
            df.replace("", np.nan).isna().mean().round(4).replace({np.nan: None}).to_dict()
        )

        return clean_json_value({
            "type": "csv",
            "shape": df.shape,
            "missing_rate": missing_rate,
            "summary": summary,
            "preview": preview,
        })

    # =========================================================
    # TEXT / JSON EDA
    # =========================================================
    if dtype == "text":
        with open(file_path, "r", errors="ignore") as f:
            lines = f.readlines()

        # JSON 파일일 수도 있으니 우선 파싱 시도
        json_data = None
        try:
            with open(file_path, "r", errors="ignore") as j:
                json_data = json.load(j)
        except Exception:
            pass  # TEXT로 처리

        result = {
            "type": "text",
            "num_lines": len(lines),
            "first_lines": lines[:20],
        }

        if json_data:
            result["json"] = json_data

        return clean_json_value(result)

    # =========================================================
    # IMAGE EDA
    # =========================================================
    if dtype == "image":
        # 단일 이미지이므로 간단하게 metadata만 반환
        return {
            "type": "image",
            "image_path": file_path,
            "info": "Single image dataset (no annotations)",
        }

    # =========================================================
    # UNKNOWN TYPE
    # =========================================================
    return clean_json_value({
        "type": dtype,
        "info": f"EDA not implemented for type {dtype}",
    })


def run_image_attributes(directory: str) -> Optional[Dict[str, Any]]:
    """
    이미지 속성 분석만 수행합니다 (빠름).
    
    - 이미지 속성 분석 (크기, 노이즈, 선명도, 품질 점수)
    - 분포 데이터 계산
    
    Args:
        directory: 분석할 디렉토리 경로
        
    Returns:
        dict: 이미지 속성 분석 결과
    """
    try:
        image_files = collect_image_files(directory)
        
        if not image_files:
            return None
        
        print(f"📊 이미지 속성 분석 시작: {len(image_files)}개 파일")
        
        analyzer = get_analyzer_service()
        
        # 이미지 속성 분석
        attr_results = {}
        for img_path in image_files:
            rel_path = os.path.relpath(img_path, directory)
            attrs = analyzer.analyze_image_attributes(img_path)
            if attrs:
                attr_results[rel_path] = attrs
        
        if not attr_results:
            return None
        
        # 요약 통계 계산
        summary_stats = calculate_summary_stats(attr_results)
        
        result = {
            "num_images": len(attr_results),
            "summary": summary_stats,
            "attributes": attr_results,
            "distributions": calculate_distributions(attr_results),
        }
        
        print(f"✅ 이미지 속성 분석 완료: {len(attr_results)}개 파일")
        return result
        
    except Exception as e:
        print(f"⚠️ 이미지 속성 분석 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_image_attributes_with_progress(
    directory: str,
    progress_callback=None,
    tracker=None
) -> Optional[Dict[str, Any]]:
    """
    이미지 속성 분석 (진행률 콜백 지원 버전).
    
    Args:
        directory: 분석할 디렉토리 경로
        progress_callback: 진행률 콜백 함수 (progress, message)
        tracker: ProgressTracker 인스턴스
        
    Returns:
        dict: 이미지 속성 분석 결과
    """
    try:
        image_files = collect_image_files(directory)
        
        if not image_files:
            return None
        
        total_files = len(image_files)
        print(f"📊 이미지 속성 분석 시작: {total_files}개 파일")
        
        if progress_callback:
            progress_callback(0.05, f"이미지 {total_files}개 분석 시작...")
        
        analyzer = get_analyzer_service()
        
        # 이미지 속성 분석
        attr_results = {}
        update_interval = max(1, total_files // 20)  # 5% 간격으로 업데이트
        
        for idx, img_path in enumerate(image_files):
            rel_path = os.path.relpath(img_path, directory)
            attrs = analyzer.analyze_image_attributes(img_path)
            if attrs:
                attr_results[rel_path] = attrs
            
            # 진행률 업데이트
            if tracker:
                tracker.update(1)
            
            if progress_callback and (idx % update_interval == 0 or idx == total_files - 1):
                progress = 0.1 + (idx + 1) / total_files * 0.8  # 10% ~ 90%
                progress_callback(progress, f"이미지 분석 중... ({idx + 1}/{total_files})")
        
        if not attr_results:
            return None
        
        if progress_callback:
            progress_callback(0.92, "통계 계산 중...")
        
        # 요약 통계 계산
        summary_stats = calculate_summary_stats(attr_results)
        
        if progress_callback:
            progress_callback(0.96, "분포 데이터 생성 중...")
        
        result = {
            "num_images": len(attr_results),
            "summary": summary_stats,
            "attributes": attr_results,
            "distributions": calculate_distributions(attr_results),
        }
        
        if progress_callback:
            progress_callback(1.0, "완료")
        
        print(f"✅ 이미지 속성 분석 완료: {len(attr_results)}개 파일")
        return result
        
    except Exception as e:
        print(f"⚠️ 이미지 속성 분석 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_image_clustering(directory: str, save_embeddings: bool = True) -> Optional[Dict[str, Any]]:
    """
    이미지 임베딩 추출 및 클러스터링을 수행합니다 (느림).
    
    - CLIP 임베딩 추출
    - K-means 클러스터링
    - 2D 시각화용 좌표 계산
    
    Args:
        directory: 분석할 디렉토리 경로
        save_embeddings: 원본 임베딩 벡터 저장 여부 (드리프트 분석용)
        
    Returns:
        dict: 클러스터링 결과 (save_embeddings=True면 원본 임베딩 포함)
    """

    try:
        image_files = collect_image_files(directory)
        
        if not image_files or len(image_files) < 5:
            return {"error": "클러스터링에는 최소 5개 이상의 이미지가 필요합니다."}
        
        print(f"🔬 이미지 클러스터링 시작: {len(image_files)}개 파일")
        
        analyzer = get_analyzer_service()
        
        embeddings_list = []
        file_names = []
        file_paths = []
        
        for img_path in image_files:
            rel_path = os.path.relpath(img_path, directory)
            emb = analyzer.extract_embedding(img_path)
            if emb and 'embedding' in emb:
                embeddings_list.append(emb['embedding'])
                file_names.append(rel_path)
                file_paths.append(img_path)
        
        if len(embeddings_list) < 5:
            return {"error": "임베딩 추출 가능한 이미지가 5개 미만입니다."}
        
        clustering_result = analyzer.perform_clustering(
            embeddings_list, file_names, file_paths,
            n_clusters=None, method='kmeans'
        )
        
        if not clustering_result or 'clustering_results' not in clustering_result:
            return {"error": "클러스터링 실패"}
        
        embeddings_2d = clustering_result['clustering_results'].get('embeddings_2d')
        
        result = {
            "num_images": len(embeddings_list),
            "n_clusters": clustering_result.get('n_clusters'),
            "cluster_stats": clustering_result.get('cluster_stats'),
            "embeddings_2d": embeddings_2d,
            "cluster_labels": clustering_result.get('clustering_results', {}).get('cluster_labels'),
            "file_names": file_names,
        }
        
        # 원본 임베딩 저장 (드리프트 분석에서 재사용)
        if save_embeddings:
            # 리스트를 numpy array로 변환 후 다시 리스트로 (JSON 직렬화 가능하게)
            result["embeddings"] = [emb.tolist() if hasattr(emb, 'tolist') else emb for emb in embeddings_list]
        
        print(f"✅ 이미지 클러스터링 완료: {len(embeddings_list)}개 파일, {result['n_clusters']}개 클러스터")
        return result
        
    except Exception as e:
        print(f"⚠️ 이미지 클러스터링 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_image_clustering_with_progress(
    directory: str,
    progress_callback=None,
    tracker=None,
    save_embeddings: bool = True
) -> Optional[Dict[str, Any]]:
    """
    이미지 클러스터링 (진행률 콜백 지원 버전).
    
    Args:
        directory: 분석할 디렉토리 경로
        progress_callback: 진행률 콜백 함수 (progress, message)
        tracker: ProgressTracker 인스턴스
        save_embeddings: 원본 임베딩 벡터 저장 여부 (드리프트 분석용)
        
    Returns:
        dict: 클러스터링 결과 (save_embeddings=True면 원본 임베딩 포함)
    """
    try:
        image_files = collect_image_files(directory)
        
        if not image_files or len(image_files) < 5:
            return {"error": "클러스터링에는 최소 5개 이상의 이미지가 필요합니다."}
        
        total_files = len(image_files)
        print(f"🔬 이미지 클러스터링 시작: {total_files}개 파일")
        
        if progress_callback:
            progress_callback(0.05, f"임베딩 추출 시작... ({total_files}개 이미지)")
        
        analyzer = get_analyzer_service()
        
        embeddings_list = []
        file_names = []
        file_paths = []
        update_interval = max(1, total_files // 20)  # 5% 간격으로 업데이트
        
        for idx, img_path in enumerate(image_files):
            rel_path = os.path.relpath(img_path, directory)
            emb = analyzer.extract_embedding(img_path)
            if emb and 'embedding' in emb:
                embeddings_list.append(emb['embedding'])
                file_names.append(rel_path)
                file_paths.append(img_path)
            
            # 진행률 업데이트
            if tracker:
                tracker.update(1)
            
            if progress_callback and (idx % update_interval == 0 or idx == total_files - 1):
                progress = 0.1 + (idx + 1) / total_files * 0.7  # 10% ~ 80%
                progress_callback(progress, f"임베딩 추출 중... ({idx + 1}/{total_files})")
        
        if len(embeddings_list) < 5:
            return {"error": "임베딩 추출 가능한 이미지가 5개 미만입니다."}
        
        if progress_callback:
            progress_callback(0.85, "K-means 클러스터링 수행 중...")
        
        clustering_result = analyzer.perform_clustering(
            embeddings_list, file_names, file_paths,
            n_clusters=None, method='kmeans'
        )
        
        if not clustering_result or 'clustering_results' not in clustering_result:
            return {"error": "클러스터링 실패"}
        
        if progress_callback:
            progress_callback(0.95, "결과 정리 중...")
        
        embeddings_2d = clustering_result['clustering_results'].get('embeddings_2d')
        
        result = {
            "num_images": len(embeddings_list),
            "n_clusters": clustering_result.get('n_clusters'),
            "cluster_stats": clustering_result.get('cluster_stats'),
            "embeddings_2d": embeddings_2d,
            "cluster_labels": clustering_result.get('clustering_results', {}).get('cluster_labels'),
            "file_names": file_names,
        }
        
        # 원본 임베딩 저장 (드리프트 분석에서 재사용)
        if save_embeddings:
            result["embeddings"] = [emb.tolist() if hasattr(emb, 'tolist') else emb for emb in embeddings_list]
        
        if progress_callback:
            progress_callback(1.0, "완료")
        
        print(f"✅ 이미지 클러스터링 완료: {len(embeddings_list)}개 파일, {result['n_clusters']}개 클러스터")
        return result
        
    except Exception as e:
        print(f"⚠️ 이미지 클러스터링 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_image_analysis(directory: str) -> Optional[Dict[str, Any]]:
    """
    ZIP 압축 해제된 디렉토리에서 전체 이미지 분석을 수행합니다 (레거시 호환).
    
    - 이미지 속성 분석 (크기, 노이즈, 선명도, 품질 점수)
    - CLIP 임베딩 추출
    - K-means 클러스터링
    
    Args:
        directory: 분석할 디렉토리 경로
        
    Returns:
        dict: 이미지 분석 결과
    """
    try:
        # 속성 분석
        attr_result = run_image_attributes(directory)
        if not attr_result:
            return None
        
        result = attr_result.copy()
        
        # 클러스터링 (5개 이상일 때만)
        if attr_result.get("num_images", 0) >= 5:
            clustering_result = run_image_clustering(directory)
            if clustering_result and "error" not in clustering_result:
                result["clustering"] = {
                    "n_clusters": clustering_result.get('n_clusters'),
                    "cluster_stats": clustering_result.get('cluster_stats'),
                    "embeddings_2d": clustering_result.get('embeddings_2d'),
                    "cluster_labels": clustering_result.get('cluster_labels'),
                }
        
        return result
        
    except Exception as e:
        print(f"⚠️ 이미지 분석 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return None


def collect_image_files(directory: str) -> List[str]:
    """
    디렉토리에서 모든 이미지 파일을 수집합니다.
    
    Args:
        directory: 검색할 디렉토리
        
    Returns:
        list: 이미지 파일 경로 리스트
    """
    image_files = []
    
    for root, _, files in os.walk(directory):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in IMAGE_EXTENSIONS:
                image_files.append(os.path.join(root, f))
    
    return image_files


def calculate_summary_stats(attr_results: Dict[str, dict]) -> Dict[str, Any]:
    """
    속성 분석 결과의 요약 통계를 계산합니다.
    
    Args:
        attr_results: 파일별 속성 분석 결과
        
    Returns:
        dict: 요약 통계
    """
    if not attr_results:
        return {}
    
    sizes = [v['size'] for v in attr_results.values() if 'size' in v]
    noise_levels = [v['noise_level'] for v in attr_results.values() if 'noise_level' in v]
    sharpness_values = [v['sharpness'] for v in attr_results.values() if 'sharpness' in v]
    widths = [v['width'] for v in attr_results.values() if 'width' in v]
    heights = [v['height'] for v in attr_results.values() if 'height' in v]
    
    # 형식별 통계
    formats = {}
    resolutions = {}
    for item in attr_results.values():
        fmt = item.get('format', 'unknown')
        formats[fmt] = formats.get(fmt, 0) + 1
        
        res = item.get('resolution', 'unknown')
        resolutions[res] = resolutions.get(res, 0) + 1
    
    # 품질 점수 계산
    quality_scores = []
    if noise_levels and sharpness_values:
        for noise, sharp in zip(noise_levels, sharpness_values):
            # 품질 점수: 선명도 높을수록, 노이즈 낮을수록 좋음
            sharp_norm = min(sharp / 100, 1.0)
            noise_norm = max(0, 1.0 - (noise / 0.5))  # 노이즈 0.5 이상이면 0점
            quality = (sharp_norm * 0.6 + noise_norm * 0.4) * 100
            quality_scores.append(quality)
    
    return {
        "total_images": len(attr_results),
        "total_size_mb": round(sum(sizes), 2) if sizes else 0,
        "avg_size_mb": round(np.mean(sizes), 4) if sizes else 0,
        "avg_width": round(np.mean(widths), 1) if widths else 0,
        "avg_height": round(np.mean(heights), 1) if heights else 0,
        "formats": formats,
        "resolutions": dict(sorted(resolutions.items(), key=lambda x: x[1], reverse=True)[:10]),
        "size_stats": {
            "min": round(float(np.min(sizes)), 4) if sizes else 0,
            "max": round(float(np.max(sizes)), 4) if sizes else 0,
            "mean": round(float(np.mean(sizes)), 4) if sizes else 0,
            "std": round(float(np.std(sizes)), 4) if sizes else 0,
        } if sizes else {},
        "noise_stats": {
            "min": round(float(np.min(noise_levels)), 4) if noise_levels else 0,
            "max": round(float(np.max(noise_levels)), 4) if noise_levels else 0,
            "mean": round(float(np.mean(noise_levels)), 4) if noise_levels else 0,
            "std": round(float(np.std(noise_levels)), 4) if noise_levels else 0,
        } if noise_levels else {},
        "sharpness_stats": {
            "min": round(float(np.min(sharpness_values)), 4) if sharpness_values else 0,
            "max": round(float(np.max(sharpness_values)), 4) if sharpness_values else 0,
            "mean": round(float(np.mean(sharpness_values)), 4) if sharpness_values else 0,
            "std": round(float(np.std(sharpness_values)), 4) if sharpness_values else 0,
        } if sharpness_values else {},
        "quality_stats": {
            "min": round(float(np.min(quality_scores)), 2) if quality_scores else 0,
            "max": round(float(np.max(quality_scores)), 2) if quality_scores else 0,
            "mean": round(float(np.mean(quality_scores)), 2) if quality_scores else 0,
            "std": round(float(np.std(quality_scores)), 2) if quality_scores else 0,
        } if quality_scores else {},
    }


def calculate_distributions(attr_results: Dict[str, dict]) -> Dict[str, Any]:
    """
    차트용 분포 데이터를 계산합니다.
    
    Args:
        attr_results: 파일별 속성 분석 결과
        
    Returns:
        dict: 분포 데이터 (히스토그램, 산점도용)
    """
    if not attr_results:
        return {}
    
    sizes = [v['size'] for v in attr_results.values() if 'size' in v]
    noise_levels = [v['noise_level'] for v in attr_results.values() if 'noise_level' in v]
    sharpness_values = [v['sharpness'] for v in attr_results.values() if 'sharpness' in v]
    
    distributions = {}
    
    # 파일 크기 분포 (히스토그램용)
    if sizes:
        hist, bin_edges = np.histogram(sizes, bins=20)
        distributions["size"] = {
            "bins": [round((bin_edges[i] + bin_edges[i+1]) / 2, 4) for i in range(len(hist))],
            "counts": hist.tolist(),
        }
    
    # 노이즈 분포
    if noise_levels:
        hist, bin_edges = np.histogram(noise_levels, bins=20)
        distributions["noise"] = {
            "bins": [round((bin_edges[i] + bin_edges[i+1]) / 2, 4) for i in range(len(hist))],
            "counts": hist.tolist(),
        }
    
    # 선명도 분포
    if sharpness_values:
        hist, bin_edges = np.histogram(sharpness_values, bins=20)
        distributions["sharpness"] = {
            "bins": [round((bin_edges[i] + bin_edges[i+1]) / 2, 4) for i in range(len(hist))],
            "counts": hist.tolist(),
        }
    
    # 품질 맵 (노이즈 vs 선명도 산점도용)
    if noise_levels and sharpness_values and len(noise_levels) == len(sharpness_values):
        # 샘플링 (너무 많으면 100개로 제한)
        indices = list(range(len(noise_levels)))
        if len(indices) > 100:
            import random
            indices = random.sample(indices, 100)
        
        distributions["quality_map"] = {
            "noise": [round(noise_levels[i], 4) for i in indices],
            "sharpness": [round(sharpness_values[i], 4) for i in indices],
        }
    
    return distributions