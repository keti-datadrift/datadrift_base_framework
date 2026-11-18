#!/usr/bin/env python3
"""
캐시 관리 유틸리티 스크립트
데이터셋별 캐시를 관리하는 명령줄 도구입니다.
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 캐시 매니저 import (상대 경로 사용)
from .cache_manager import get_cache_manager, get_cached_analysis_data, save_analysis_data

def main():
    parser = argparse.ArgumentParser(
        description='캐시 관리 유틸리티',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python cache_utils/cache_utils.py info /path/to/dataset
  python cache_utils/cache_utils.py list /path/to/dataset
  python cache_utils/cache_utils.py clear /path/to/dataset
  python cache_utils/cache_utils.py invalidate html_report /path/to/dataset
        """
    )
    
    parser.add_argument('command', choices=['info', 'list', 'clear', 'invalidate'],
                       help='실행할 명령')
    parser.add_argument('directory', nargs='?', help='데이터셋 디렉토리 (선택사항)')
    parser.add_argument('--identifier', help='무효화할 캐시 식별자 (invalidate 명령에서 사용)')
    parser.add_argument('--content-type', default='html', 
                       choices=['html', 'analysis'], help='캐시 컨텐츠 타입')
    
    args = parser.parse_args()
    
    # 디렉토리가 지정되지 않은 경우 현재 디렉토리 사용
    if not args.directory:
        args.directory = os.getcwd()
    
    if not os.path.exists(args.directory):
        print(f"오류: 디렉토리가 존재하지 않습니다: {args.directory}")
        sys.exit(1)
    
    # 캐시 매니저 가져오기
    cache_manager = get_cache_manager(args.directory)
    
    if args.command == 'info':
        show_cache_info(cache_manager, args.directory)
    
    elif args.command == 'list':
        list_cache_files(cache_manager, args.directory)
    
    elif args.command == 'clear':
        clear_cache(cache_manager, args.directory)
    
    elif args.command == 'invalidate':
        if not args.identifier:
            print("오류: invalidate 명령에는 --identifier가 필요합니다.")
            sys.exit(1)
        invalidate_cache(cache_manager, args.identifier, args.content_type, args.directory)

def show_cache_info(cache_manager, directory):
    """캐시 정보 표시"""
    info = cache_manager.get_cache_info()
    
    print(f"📁 캐시 디렉토리: {info['cache_dir']}")
    print(f"📊 총 파일 수: {info['total_files']}")
    print(f"💾 총 크기: {info['total_size_mb']} MB")
    print(f"🔒 최대 크기: {info['max_size_mb']} MB")
    print(f"⏰ 만료 기간: {info['expiry_days']}일")
    
    # 분석 데이터 확인
    cached_data = get_cached_analysis_data(directory, "image_analysis")
    if cached_data:
        print(f"🖼️ 이미지 분석 데이터: {len(cached_data)}개 파일")
    else:
        print("🖼️ 이미지 분석 데이터: 없음")

def list_cache_files(cache_manager, directory):
    """캐시 파일 목록 표시"""
    cache_dir = Path(cache_manager.cache_dir)
    
    if not cache_dir.exists():
        print("캐시 디렉토리가 존재하지 않습니다.")
        return
    
    cache_files = list(cache_dir.glob("*.cache"))
    
    if not cache_files:
        print("캐시 파일이 없습니다.")
        return
    
    print(f"📋 캐시 파일 목록 ({len(cache_files)}개):")
    print("-" * 80)
    
    for cache_file in sorted(cache_files):
        size = cache_file.stat().st_size
        size_mb = size / (1024 * 1024)
        modified_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        
        # 메타데이터 파일 확인
        metadata_file = cache_file.with_name(f"{cache_file.stem}_meta.json")
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    import json
                    metadata = json.load(f)
                    content_type = metadata.get('content_type', 'unknown')
                    created_time = metadata.get('created_time', 'unknown')
            except:
                content_type = 'unknown'
                created_time = 'unknown'
        else:
            content_type = 'unknown'
            created_time = 'unknown'
        
        print(f"📄 {cache_file.name}")
        print(f"   크기: {size_mb:.2f} MB")
        print(f"   타입: {content_type}")
        print(f"   생성: {created_time}")
        print(f"   수정: {modified_time}")
        print()

def clear_cache(cache_manager, directory):
    """캐시 정리"""
    print(f"🗑️ 캐시 정리 중: {directory}")
    
    result = cache_manager.clear_all_cache()
    
    if result:
        print("✅ 캐시가 성공적으로 정리되었습니다.")
    else:
        print("❌ 캐시 정리 중 오류가 발생했습니다.")

def invalidate_cache(cache_manager, identifier, content_type, directory):
    """특정 캐시 무효화"""
    print(f"🔄 캐시 무효화 중: {identifier} ({content_type})")
    
    result = cache_manager.invalidate_cache(identifier, content_type)
    
    if result:
        print("✅ 캐시가 성공적으로 무효화되었습니다.")
    else:
        print("❌ 캐시 무효화 중 오류가 발생했습니다.")

if __name__ == '__main__':
    main() 