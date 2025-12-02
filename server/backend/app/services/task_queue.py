"""
작업 큐 서비스 - 분석 작업 관리 및 중복 실행 방지
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, Callable, Any
from datetime import datetime


class TaskQueueService:
    """
    분석 작업 큐 및 상태 관리
    
    - ThreadPoolExecutor 기반 병렬 처리
    - 중복 실행 방지
    - 실행 중인 작업 추적
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """싱글톤 인스턴스 초기화"""
        # 동시 실행 제한 (4 workers: 속성분석 + 임베딩 분석 병렬 처리)
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="analysis_")
        
        # 현재 실행 중인 작업 추적 (task_key -> task_id)
        self.running_tasks: Dict[str, str] = {}
        self._tasks_lock = threading.Lock()
        
        # 작업 취소 플래그 (task_id -> bool)
        self.cancel_flags: Dict[str, bool] = {}
        
        print("📦 TaskQueueService 초기화 완료 (max_workers=4)")
    
    def get_task_key(
        self, 
        dataset_id: str, 
        task_type: str, 
        target_id: Optional[str] = None
    ) -> str:
        """
        작업 고유 키 생성
        
        Args:
            dataset_id: 데이터셋 ID
            task_type: 작업 유형 (eda, image_analysis, clustering, drift)
            target_id: 비교 대상 데이터셋 ID (drift 전용)
            
        Returns:
            str: 고유 작업 키
        """
        if target_id:
            return f"{dataset_id}:{task_type}:{target_id}"
        return f"{dataset_id}:{task_type}"
    
    def is_running(
        self, 
        dataset_id: str, 
        task_type: str, 
        target_id: Optional[str] = None
    ) -> Optional[str]:
        """
        해당 작업이 이미 실행 중인지 확인
        
        Returns:
            실행 중이면 task_id, 아니면 None
        """
        key = self.get_task_key(dataset_id, task_type, target_id)
        with self._tasks_lock:
            return self.running_tasks.get(key)
    
    def start_task(
        self, 
        task_id: str, 
        dataset_id: str, 
        task_type: str, 
        target_id: Optional[str] = None
    ) -> bool:
        """
        작업 시작 등록
        
        Returns:
            성공시 True, 이미 실행 중이면 False
        """
        key = self.get_task_key(dataset_id, task_type, target_id)
        with self._tasks_lock:
            if key in self.running_tasks:
                return False
            self.running_tasks[key] = task_id
            self.cancel_flags[task_id] = False
            return True
    
    def finish_task(
        self, 
        dataset_id: str, 
        task_type: str, 
        target_id: Optional[str] = None
    ):
        """작업 완료 등록"""
        key = self.get_task_key(dataset_id, task_type, target_id)
        with self._tasks_lock:
            task_id = self.running_tasks.pop(key, None)
            if task_id:
                self.cancel_flags.pop(task_id, None)
    
    def cancel_task(self, task_id: str) -> bool:
        """
        작업 취소 요청
        
        Returns:
            취소 요청 성공 여부
        """
        with self._tasks_lock:
            if task_id in self.cancel_flags:
                self.cancel_flags[task_id] = True
                return True
            return False
    
    def is_cancelled(self, task_id: str) -> bool:
        """작업이 취소되었는지 확인"""
        with self._tasks_lock:
            return self.cancel_flags.get(task_id, False)
    
    def submit_task(
        self, 
        func: Callable, 
        *args, 
        **kwargs
    ):
        """
        작업을 스레드풀에 제출
        
        Args:
            func: 실행할 함수
            *args, **kwargs: 함수 인자
            
        Returns:
            Future 객체
        """
        return self.executor.submit(func, *args, **kwargs)
    
    def get_running_tasks_for_dataset(self, dataset_id: str) -> Dict[str, str]:
        """
        특정 데이터셋의 실행 중인 작업 목록 조회
        
        Returns:
            {task_type: task_id} 딕셔너리
        """
        result = {}
        with self._tasks_lock:
            for key, task_id in self.running_tasks.items():
                parts = key.split(":")
                if parts[0] == dataset_id:
                    task_type = parts[1]
                    result[task_type] = task_id
        return result
    
    def get_all_running_tasks(self) -> Dict[str, str]:
        """모든 실행 중인 작업 조회"""
        with self._tasks_lock:
            return dict(self.running_tasks)
    
    def shutdown(self, wait: bool = True):
        """스레드풀 종료"""
        self.executor.shutdown(wait=wait)
        print("📦 TaskQueueService 종료")


# 싱글톤 인스턴스 가져오기
def get_task_queue() -> TaskQueueService:
    """TaskQueueService 싱글톤 인스턴스 반환"""
    return TaskQueueService()
