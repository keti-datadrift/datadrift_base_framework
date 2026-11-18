import os
import hashlib
import numpy as np
from PIL import Image
from skimage import io, filters, img_as_float, color, exposure
from scipy import stats
from scipy.ndimage import gaussian_filter
import sys


class AttributeAnalyzer:
    """이미지 속성 분석을 관리하는 클래스"""
    
    def __init__(self):
        """AttributeAnalyzer 초기화"""
        pass
    
    def analyze_image_attributes(self, file_path):
        """
        단일 이미지의 속성을 분석하고 해시와 함께 결과를 반환합니다.
        
        Args:
            file_path: 분석할 이미지 파일 경로
        
        Returns:
            dict: 이미지 속성 정보 (해시 포함) 또는 None
        """
        try:
            with Image.open(file_path) as img:
                # 기본 메타데이터
                file_size_bytes = os.path.getsize(file_path)
                file_size_mb = file_size_bytes / (1024 * 1024)  # Convert to MB
                image_format = img.format
                width, height = img.size
                resolution = f"{width}x{height}"

                # 이미지 데이터 분석 (컬러와 그레이스케일 모두 지원)
                image_rgb = img_as_float(io.imread(file_path))
                is_grayscale = len(image_rgb.shape) == 2 or (len(image_rgb.shape) == 3 and image_rgb.shape[2] == 1)
                
                if is_grayscale or len(image_rgb.shape) == 2:
                    image_gray = image_rgb if len(image_rgb.shape) == 2 else image_rgb[:, :, 0]
                    image_lab = None
                else:
                    # Convert to grayscale for some metrics
                    image_gray = color.rgb2gray(image_rgb)
                    # Convert to LAB for colorfulness
                    image_lab = color.rgb2lab(image_rgb)
                
                # 1. Brightness: luminance 평균 (grayscale 평균)
                brightness = np.mean(image_gray)
                
                # 2. Exposure: 히스토그램 기반 노출 지표 (중간톤 대비 하이라이트/섀도우 클리핑)
                hist, bins = exposure.histogram(image_gray, nbins=256)
                hist_norm = hist / hist.sum()
                # 하이라이트 클리핑 비율 (상위 5%)
                highlight_clip = np.sum(hist_norm[-13:])  # 상위 5% (256 * 0.05 ≈ 13)
                # 섀도우 클리핑 비율 (하위 5%)
                shadow_clip = np.sum(hist_norm[:13])  # 하위 5%
                exposure_score = 1.0 - (highlight_clip + shadow_clip) / 2.0
                
                # 3. Contrast: 표준편차
                contrast = np.std(image_gray)
                
                # 4. Dynamic Range: 최대값 - 최소값
                dynamic_range = np.max(image_gray) - np.min(image_gray)
                
                # 5. Colorfulness: LAB 색공간에서 a*, b* 채널의 표준편차 (컬러 이미지만)
                if image_lab is not None:
                    a_channel = image_lab[:, :, 1]
                    b_channel = image_lab[:, :, 2]
                    colorfulness = np.sqrt(np.std(a_channel)**2 + np.std(b_channel)**2)
                else:
                    colorfulness = 0.0  # Grayscale 이미지는 0
                
                # 6. Edge Density: 엣지 픽셀 비율 (sobel 엣지의 임계값 초과 비율)
                edges = filters.sobel(image_gray)
                edge_threshold = np.percentile(edges, 90)  # 상위 10%를 엣지로 간주
                edge_density = np.sum(edges > edge_threshold) / edges.size
                
                # 7. Sharpness: sobel 필터 평균 (기존 유지)
                sharpness = filters.sobel(image_gray).mean()
                
                # 8. Entropy: 정보 엔트로피
                hist, _ = np.histogram(image_gray.flatten(), bins=256, range=(0, 1))
                hist_norm = hist / hist.sum()
                hist_norm = hist_norm[hist_norm > 0]  # 0 제거
                entropy = -np.sum(hist_norm * np.log2(hist_norm))
                
                # 9. Gaussian Noise Level: 가우시안 필터 적용 후 원본과의 차이 표준편차
                image_smooth = gaussian_filter(image_gray, sigma=1.0)
                noise_residual = image_gray - image_smooth
                gaussian_noise_level = np.std(noise_residual)
                
                # Legacy: noise_level (기존 호환성 유지)
                noise_level = gaussian_noise_level

                # 해시 계산
                import hashlib
                hasher = hashlib.md5()
                with open(file_path, 'rb') as f:
                    buf = f.read()
                    hasher.update(buf)
                file_hash = hasher.hexdigest()

                return {
                    'hash': file_hash,
                    'path': os.path.abspath(file_path),
                    'size': file_size_mb,
                    'format': image_format,
                    'resolution': resolution,
                    'width': width,
                    'height': height,
                    # Legacy metrics (호환성 유지)
                    'noise_level': noise_level,
                    'sharpness': sharpness,
                    # New metrics (9종)
                    'brightness': brightness,
                    'exposure': exposure_score,
                    'contrast': contrast,
                    'dynamic_range': dynamic_range,
                    'colorfulness': colorfulness,
                    'edge_density': edge_density,
                    'entropy': entropy,
                    'gaussian_noise_level': gaussian_noise_level
                }
        
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None
    
    def analyze_directory(self, directory, formats):
        """
        디렉토리의 모든 이미지 속성을 분석합니다.
        
        Args:
            directory: 분석할 디렉토리 경로
            formats: 분석할 이미지 포맷 리스트
        
        Returns:
            dict: 파일별 속성 분석 결과
        """
        if not os.path.exists(directory):
            print(f"Error: Directory {directory} does not exist.")
            return {}
        
        print(f"\nAnalyzing images in directory: {directory}\n")
        
        results = {}
        format_count = 0

        # 파일 수 계산
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(tuple(formats)):
                    format_count += 1
        print(f"Found {format_count} files in {directory}\n")

        # 속성 분석
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(tuple(formats)):
                    file_path = os.path.join(root, file)

                    # 속성 분석 수행
                    attributes = self.analyze_image_attributes(file_path)
                    
                    if attributes:
                        results[file] = attributes
                        print(f"Processed {file}")
                    else:
                        print(f"Failed to process {file}")

        return results
    
    def get_summary_statistics(self, analysis_results):
        """
        분석 결과의 요약 통계를 계산합니다.
        
        Args:
            analysis_results: 속성 분석 결과 딕셔너리
        
        Returns:
            dict: 요약 통계 정보
        """
        if not analysis_results:
            return {}
        
        # 데이터 수집 (새로운 지표 포함)
        sizes = [item['size'] for item in analysis_results.values()]
        noise_levels = [item.get('noise_level', item.get('gaussian_noise_level', 0)) for item in analysis_results.values()]
        sharpness_values = [item['sharpness'] for item in analysis_results.values()]
        
        # 새로운 지표들 수집
        brightness_values = [item.get('brightness', 0) for item in analysis_results.values()]
        exposure_values = [item.get('exposure', 0) for item in analysis_results.values()]
        contrast_values = [item.get('contrast', 0) for item in analysis_results.values()]
        dynamic_range_values = [item.get('dynamic_range', 0) for item in analysis_results.values()]
        colorfulness_values = [item.get('colorfulness', 0) for item in analysis_results.values()]
        edge_density_values = [item.get('edge_density', 0) for item in analysis_results.values()]
        entropy_values = [item.get('entropy', 0) for item in analysis_results.values()]
        gaussian_noise_levels = [item.get('gaussian_noise_level', 0) for item in analysis_results.values()]
        
        # 형식별 통계
        formats = {}
        resolutions = {}
        
        for item in analysis_results.values():
            fmt = item['format']
            formats[fmt] = formats.get(fmt, 0) + 1
            
            res = item['resolution']
            resolutions[res] = resolutions.get(res, 0) + 1
        
        def compute_stats(values):
            """통계 계산 헬퍼 함수"""
            if not values:
                return {}
            return {
                'min': float(np.min(values)),
                'max': float(np.max(values)),
                'mean': float(np.mean(values)),
                'std': float(np.std(values)),
                'median': float(np.median(values))
            }
        
        return {
            'total_images': len(analysis_results),
            'total_size_mb': sum(sizes),
            'avg_size_mb': np.mean(sizes),
            'formats': formats,
            'resolutions': resolutions,
            'size_stats': compute_stats(sizes),
            'noise_stats': compute_stats(noise_levels),
            'sharpness_stats': compute_stats(sharpness_values),
            # 새로운 지표 통계
            'brightness_stats': compute_stats(brightness_values),
            'exposure_stats': compute_stats(exposure_values),
            'contrast_stats': compute_stats(contrast_values),
            'dynamic_range_stats': compute_stats(dynamic_range_values),
            'colorfulness_stats': compute_stats(colorfulness_values),
            'edge_density_stats': compute_stats(edge_density_values),
            'entropy_stats': compute_stats(entropy_values),
            'gaussian_noise_level_stats': compute_stats(gaussian_noise_levels)
        }


def run_attribute_analysis(directories, formats):
    """
    속성 분석을 실행하는 편의 함수
    
    Args:
        directories: 분석할 디렉토리 리스트
        formats: 이미지 포맷 리스트
    
    Returns:
        dict: 각 디렉토리별 분석 결과
    """
    analyzer = AttributeAnalyzer()
    results = {}
    
    for directory in directories:
        if not os.path.exists(directory):
            print(f"Error: Directory {directory} does not exist.")
            continue
        
        # 속성 분석 수행
        analysis_results = analyzer.analyze_directory(directory, formats)
        
        if analysis_results:
            # 요약 통계 계산
            summary_stats = analyzer.get_summary_statistics(analysis_results)
            
            results[directory] = {
                'analysis_results': analysis_results,
                'summary_stats': summary_stats,
                'total_files': len(analysis_results)
            }
            
            print(f"\nAnalysis completed for {directory}")
            print(f"Total files processed: {len(analysis_results)}")
            print(f"Total size: {summary_stats['total_size_mb']:.2f} MB")
            print(f"Average size: {summary_stats['avg_size_mb']:.2f} MB")
        else:
            print(f"No valid files found in {directory}")
    
    return results 