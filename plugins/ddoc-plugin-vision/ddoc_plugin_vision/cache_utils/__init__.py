"""
캐시 관리 유틸리티 패키지

이 패키지는 데이터셋별 캐시 관리를 위한 유틸리티들을 제공합니다.
"""

from .cache_manager import (
    CacheManager,
    get_cache_manager,
    get_cache_repository,
    get_cached_html_content,
    get_cached_analysis_data,
    save_analysis_data,
    get_cached_analysis_data_by_version,
    save_analysis_data_by_version,
    get_latest_cached_content_by_prefix,
    export_local_cache_to_repository,
    import_repository_cache_to_local,
    repository_has_cache,
)
from .cache_repository import CacheRepository

__all__ = [
    'CacheManager',
    'CacheRepository',
    'get_cache_manager',
    'get_cache_repository',
    'get_cached_html_content',
    'get_cached_analysis_data',
    'save_analysis_data',
    'get_cached_analysis_data_by_version',
    'save_analysis_data_by_version',
    'get_latest_cached_content_by_prefix',
    'export_local_cache_to_repository',
    'import_repository_cache_to_local',
    'repository_has_cache',
] 