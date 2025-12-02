"""
Analyzer Initialization Service

ddoc-plugin-vision이 설치된 경우 사용, 없으면 Fallback 분석기를 사용합니다.
Docker 빌드 시 wheel로 설치되거나, 로컬 개발 시 pip install -e로 설치됩니다.
"""
import os
from typing import Optional


class AnalyzerService:
    """
    ddoc-plugin-vision의 분석기를 관리하는 싱글톤 서비스
    
    - ddoc-plugin-vision 설치 시: 실제 CLIP 기반 분석
    - 미설치 시: Fallback 분석기 (기본 이미지 특성 기반)
    """
    _instance: Optional['AnalyzerService'] = None
    _attr_analyzer = None
    _emb_analyzer = None
    _model_loaded = False
    _use_ddoc_plugin = None  # None: 아직 확인 안 함
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._use_ddoc_plugin is None:
            self._check_ddoc_plugin()
    
    def _check_ddoc_plugin(self):
        """ddoc-plugin-vision 사용 가능 여부 확인"""
        try:
            from ddoc_plugin_vision.data_utils import AttributeAnalyzer, EmbeddingAnalyzer
            self._use_ddoc_plugin = True
            print("✅ ddoc-plugin-vision 사용 가능")
        except ImportError as e:
            self._use_ddoc_plugin = False
            print(f"⚠️ ddoc-plugin-vision 미설치, Fallback 분석기 사용")
            print(f"   (설치: pip install ddoc-plugin-vision 또는 Docker 빌드)")
    
    @property
    def use_ddoc_plugin(self) -> bool:
        """ddoc-plugin-vision 사용 여부"""
        if self._use_ddoc_plugin is None:
            self._check_ddoc_plugin()
        return self._use_ddoc_plugin
    
    @property
    def attr_analyzer(self):
        """AttributeAnalyzer 인스턴스를 반환합니다 (지연 로딩)"""
        if self._attr_analyzer is None:
            if self.use_ddoc_plugin:
                from ddoc_plugin_vision.data_utils import AttributeAnalyzer
                self._attr_analyzer = AttributeAnalyzer()
                print("✅ AttributeAnalyzer (ddoc-plugin-vision) initialized")
            else:
                self._attr_analyzer = FallbackAttributeAnalyzer()
                print("✅ FallbackAttributeAnalyzer initialized")
        return self._attr_analyzer
    
    @property
    def emb_analyzer(self):
        """EmbeddingAnalyzer 인스턴스를 반환합니다 (지연 로딩)"""
        if self._emb_analyzer is None:
            if self.use_ddoc_plugin:
                from ddoc_plugin_vision.data_utils import EmbeddingAnalyzer
                self._emb_analyzer = EmbeddingAnalyzer(device='cpu')
                print("✅ EmbeddingAnalyzer (ddoc-plugin-vision) initialized")
            else:
                self._emb_analyzer = FallbackEmbeddingAnalyzer()
                print("✅ FallbackEmbeddingAnalyzer initialized")
        return self._emb_analyzer
    
    def load_embedding_model(self, model_name: str = "ViT-B/16"):
        """
        CLIP 모델을 명시적으로 로드합니다.
        첫 임베딩 추출 시 자동으로 호출되지만, 미리 로드하고 싶을 때 사용합니다.
        """
        if not self._model_loaded:
            try:
                self.emb_analyzer.load_model(model_name)
                self._model_loaded = True
                print(f"✅ CLIP model '{model_name}' loaded successfully")
            except Exception as e:
                print(f"⚠️ Failed to load CLIP model: {e}")
                self._model_loaded = False
        return self._model_loaded
    
    def is_model_loaded(self) -> bool:
        """CLIP 모델이 로드되었는지 확인합니다."""
        return self._model_loaded
    
    def analyze_image_attributes(self, file_path: str) -> Optional[dict]:
        """
        단일 이미지의 속성을 분석합니다.
        
        Args:
            file_path: 분석할 이미지 파일 경로
            
        Returns:
            dict: 이미지 속성 정보 (size, format, resolution, noise_level, sharpness 등)
        """
        return self.attr_analyzer.analyze_image_attributes(file_path)
    
    def extract_embedding(self, file_path: str) -> Optional[dict]:
        """
        단일 이미지의 임베딩을 추출합니다.
        
        Args:
            file_path: 분석할 이미지 파일 경로
            
        Returns:
            dict: 임베딩 결과 (embedding, hash, path)
        """
        return self.emb_analyzer.extract_embedding(file_path)
    
    def perform_clustering(self, embeddings_data, file_names, file_paths, 
                          n_clusters=None, method='kmeans') -> Optional[dict]:
        """
        임베딩 기반 클러스터링을 수행합니다.
        
        Args:
            embeddings_data: 임베딩 데이터 리스트
            file_names: 파일명 리스트
            file_paths: 파일 경로 리스트
            n_clusters: 클러스터 수 (None이면 자동 결정)
            method: 클러스터링 방법 ('kmeans', 'dbscan', 'hierarchical')
            
        Returns:
            dict: 클러스터링 결과
        """
        import numpy as np
        embeddings_array = np.array(embeddings_data)
        return self.emb_analyzer.perform_clustering(
            embeddings_array, file_names, file_paths, n_clusters, method
        )


class FallbackAttributeAnalyzer:
    """
    ddoc-plugin-vision을 사용할 수 없을 때 사용하는 기본 속성 분석기
    """
    def analyze_image_attributes(self, file_path: str) -> Optional[dict]:
        try:
            import os
            import hashlib
            from PIL import Image
            import numpy as np
            
            with Image.open(file_path) as img:
                file_size_bytes = os.path.getsize(file_path)
                file_size_mb = file_size_bytes / (1024 * 1024)
                image_format = img.format
                width, height = img.size
                resolution = f"{width}x{height}"
                
                # 간단한 노이즈/선명도 추정
                img_array = np.array(img.convert('L'))
                noise_level = float(np.std(img_array) / 255.0)
                
                # Laplacian variance로 선명도 추정
                try:
                    from scipy import ndimage
                    laplacian = ndimage.laplace(img_array.astype(float))
                    sharpness = float(np.var(laplacian))
                except ImportError:
                    # scipy 없으면 간단한 방식
                    sharpness = float(np.std(np.diff(img_array.astype(float), axis=0)))
                
                # 해시 계산
                hasher = hashlib.md5()
                with open(file_path, 'rb') as f:
                    hasher.update(f.read())
                file_hash = hasher.hexdigest()
                
                return {
                    'hash': file_hash,
                    'path': os.path.abspath(file_path),
                    'size': file_size_mb,
                    'format': image_format,
                    'resolution': resolution,
                    'width': width,
                    'height': height,
                    'noise_level': noise_level,
                    'sharpness': sharpness
                }
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None


class FallbackEmbeddingAnalyzer:
    """
    ddoc-plugin-vision을 사용할 수 없을 때 사용하는 기본 임베딩 분석기
    실제 CLIP 임베딩 대신 간단한 특성 벡터를 생성합니다.
    """
    def __init__(self, device=None):
        self.device = device
        self.model = None
    
    def load_model(self, model_name: str = "ViT-B/16"):
        print(f"⚠️ FallbackEmbeddingAnalyzer: CLIP 모델 로드 건너뜀")
        print(f"   (ddoc-plugin-vision 설치 시 실제 CLIP 모델 사용 가능)")
    
    def extract_embedding(self, file_path: str) -> Optional[dict]:
        """
        Fallback: 이미지에서 간단한 특성 벡터를 추출합니다.
        실제 CLIP 임베딩이 아닌 색상/텍스처 기반 특성입니다.
        """
        try:
            import os
            import hashlib
            from PIL import Image
            import numpy as np
            
            with Image.open(file_path) as img:
                img = img.convert('RGB').resize((224, 224))
                img_array = np.array(img)
                
                # 간단한 특성 벡터 생성 (512차원)
                features = []
                
                # RGB 채널별 히스토그램 (각 256 -> 64로 축소)
                for c in range(3):
                    hist, _ = np.histogram(img_array[:, :, c], bins=64, range=(0, 256))
                    features.extend(hist / hist.sum())
                
                # 공간적 통계 (그리드별 평균)
                grid_size = 8
                h, w = img_array.shape[:2]
                gh, gw = h // grid_size, w // grid_size
                for i in range(grid_size):
                    for j in range(grid_size):
                        region = img_array[i*gh:(i+1)*gh, j*gw:(j+1)*gw]
                        features.append(np.mean(region) / 255.0)
                
                # 512차원으로 패딩
                embedding = np.array(features)
                if len(embedding) < 512:
                    embedding = np.pad(embedding, (0, 512 - len(embedding)))
                else:
                    embedding = embedding[:512]
                
                # 해시 계산
                hasher = hashlib.md5()
                with open(file_path, 'rb') as f:
                    hasher.update(f.read())
                file_hash = hasher.hexdigest()
                
                return {
                    'hash': file_hash,
                    'path': os.path.abspath(file_path),
                    'embedding': embedding.tolist()
                }
        except Exception as e:
            print(f"Error extracting embedding from {file_path}: {e}")
            return None
    
    def perform_clustering(self, embeddings_data, file_names, file_paths, 
                          n_clusters=None, method='kmeans'):
        """Fallback 클러스터링"""
        import numpy as np
        from sklearn.cluster import KMeans
        from sklearn.decomposition import PCA
        
        if len(embeddings_data) < 2:
            return None
        
        embeddings_array = np.array(embeddings_data)
        
        # 자동 클러스터 수 결정
        if n_clusters is None:
            n_clusters = min(5, len(embeddings_data) // 3)
            n_clusters = max(2, n_clusters)
        
        # PCA 차원 축소
        pca = PCA(n_components=2)
        embeddings_2d = pca.fit_transform(embeddings_array)
        
        # K-means 클러스터링
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(embeddings_2d)
        
        # 클러스터 통계
        cluster_stats = {}
        for i in range(n_clusters):
            cluster_indices = np.where(cluster_labels == i)[0]
            cluster_stats[f'cluster_{i}'] = {
                'size': len(cluster_indices),
                'files': [file_names[idx] for idx in cluster_indices]
            }
        
        return {
            'clustering_results': {
                'method': method,
                'n_clusters': n_clusters,
                'cluster_labels': cluster_labels.tolist(),
                'file_names': file_names,
                'embeddings_2d': embeddings_2d.tolist(),
                'cluster_stats': cluster_stats
            },
            'n_clusters': n_clusters,
            'cluster_stats': cluster_stats
        }


# 싱글톤 인스턴스 getter
_analyzer_service: Optional[AnalyzerService] = None

def get_analyzer_service() -> AnalyzerService:
    """AnalyzerService 싱글톤 인스턴스를 반환합니다."""
    global _analyzer_service
    if _analyzer_service is None:
        _analyzer_service = AnalyzerService()
    return _analyzer_service
