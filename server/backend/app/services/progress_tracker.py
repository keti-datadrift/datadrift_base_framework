"""
진행률 추적 및 예상 시간 계산 유틸리티
"""

import time
import statistics
from collections import deque
from typing import Optional, Dict, Callable, Any


# 타입 정의
ProgressCallback = Callable[[float, str, Optional[Dict[str, Any]]], None]


class TimeEstimator:
    """
    분석 작업 소요 시간 추정기
    
    이전 작업 이력을 기반으로 예상 소요 시간을 계산합니다.
    """
    
    # 작업 유형별 이력 저장 (클래스 변수)
    _history: Dict[str, deque] = {}
    _max_history: int = 20
    
    # 작업 유형별 기본 추정치 (파일당 초)
    DEFAULT_ESTIMATES = {
        "eda": 0.1,
        "image_analysis": 0.5,
        "clustering": 1.0,
        "drift": 1.5,
    }
    
    @classmethod
    def record_completion(
        cls, 
        task_type: str, 
        item_count: int, 
        duration_seconds: float
    ):
        """
        완료된 작업의 소요 시간 기록
        
        Args:
            task_type: 작업 유형
            item_count: 처리된 항목 수
            duration_seconds: 소요 시간 (초)
        """
        if task_type not in cls._history:
            cls._history[task_type] = deque(maxlen=cls._max_history)
        
        if item_count > 0:
            per_item_time = duration_seconds / item_count
            cls._history[task_type].append(per_item_time)
    
    @classmethod
    def estimate_time(cls, task_type: str, item_count: int) -> float:
        """
        예상 소요 시간 계산
        
        Args:
            task_type: 작업 유형
            item_count: 처리할 항목 수
            
        Returns:
            예상 소요 시간 (초)
        """
        if task_type not in cls._history or len(cls._history[task_type]) == 0:
            # 이력이 없으면 기본값 사용
            per_item = cls.DEFAULT_ESTIMATES.get(task_type, 1.0)
        else:
            # 중앙값 사용 (이상치 영향 최소화)
            per_item = statistics.median(cls._history[task_type])
        
        return per_item * item_count
    
    @staticmethod
    def format_time(seconds: Optional[float]) -> str:
        """
        사람이 읽기 쉬운 시간 포맷
        
        Args:
            seconds: 시간 (초)
            
        Returns:
            포맷된 문자열 (예: "2분 30초")
        """
        if seconds is None:
            return "계산 중..."
        
        seconds = max(0, seconds)
        
        if seconds < 60:
            return f"{int(seconds)}초"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            if secs == 0:
                return f"{minutes}분"
            return f"{minutes}분 {secs}초"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            if minutes == 0:
                return f"{hours}시간"
            return f"{hours}시간 {minutes}분"


class ProgressTracker:
    """
    실시간 진행률 및 ETA 추적기
    
    처리 중인 작업의 진행률과 예상 남은 시간을 계산합니다.
    """
    
    def __init__(self, total_items: int, task_type: str = "unknown"):
        """
        Args:
            total_items: 처리할 총 항목 수
            task_type: 작업 유형 (완료 후 기록용)
        """
        self.total = max(total_items, 1)
        self.task_type = task_type
        self.processed = 0
        self.start_time = time.time()
        
        # 최근 항목 처리 시간 (이동 평균용)
        self.item_times: deque = deque(maxlen=20)
        self._last_item_time = self.start_time
    
    def update(self, count: int = 1) -> Dict[str, Any]:
        """
        처리 완료 업데이트
        
        Args:
            count: 처리 완료된 항목 수
            
        Returns:
            현재 상태 딕셔너리
        """
        now = time.time()
        
        # 항목당 처리 시간 계산
        if self.processed > 0:
            item_duration = (now - self._last_item_time) / max(count, 1)
            self.item_times.append(item_duration)
        
        self._last_item_time = now
        self.processed += count
        
        return self.get_status()
    
    @property
    def progress(self) -> float:
        """현재 진행률 (0.0 ~ 1.0)"""
        return min(self.processed / self.total, 1.0)
    
    @property
    def elapsed(self) -> float:
        """경과 시간 (초)"""
        return time.time() - self.start_time
    
    @property
    def eta(self) -> Optional[float]:
        """
        예상 남은 시간 (초)
        
        최근 처리 속도를 기반으로 계산합니다.
        """
        if self.processed == 0:
            # 아직 처리 시작 전이면 기본 추정치 사용
            return TimeEstimator.estimate_time(self.task_type, self.total)
        
        remaining = self.total - self.processed
        
        if remaining <= 0:
            return 0.0
        
        if self.item_times:
            # 최근 처리 속도 기반 추정
            avg_time = sum(self.item_times) / len(self.item_times)
            return avg_time * remaining
        else:
            # 전체 평균 기반 추정
            avg_time = self.elapsed / self.processed
            return avg_time * remaining
    
    def get_status(self) -> Dict[str, Any]:
        """
        현재 상태 딕셔너리 반환
        
        Returns:
            dict: 진행률, 처리 수, ETA 등 포함
        """
        eta = self.eta
        
        return {
            "progress": round(self.progress, 4),
            "processed": self.processed,
            "total": self.total,
            "elapsed_seconds": round(self.elapsed, 1),
            "eta_seconds": round(eta, 1) if eta is not None else None,
            "eta_formatted": TimeEstimator.format_time(eta),
        }
    
    def finish(self):
        """
        작업 완료 처리
        
        소요 시간을 TimeEstimator에 기록합니다.
        """
        duration = self.elapsed
        TimeEstimator.record_completion(self.task_type, self.processed, duration)
        
        return {
            "progress": 1.0,
            "processed": self.processed,
            "total": self.total,
            "elapsed_seconds": round(duration, 1),
            "eta_seconds": 0,
            "eta_formatted": "완료",
        }


def create_progress_callback(
    tracker: ProgressTracker,
    update_func: Callable[[float, str, Dict[str, Any]], None],
    update_interval: int = 10
) -> ProgressCallback:
    """
    진행률 콜백 함수 생성
    
    Args:
        tracker: ProgressTracker 인스턴스
        update_func: 상태 업데이트 함수 (progress, message, metadata)
        update_interval: 업데이트 간격 (항목 수)
        
    Returns:
        진행률 콜백 함수
    """
    call_count = [0]  # closure로 카운트 유지
    
    def callback(progress: float, message: str, metadata: Optional[Dict[str, Any]] = None):
        call_count[0] += 1
        
        # 지정된 간격마다 또는 마지막 항목에서 업데이트
        if call_count[0] % update_interval == 0 or progress >= 1.0:
            status = tracker.get_status()
            if metadata:
                status.update(metadata)
            update_func(progress, message, status)
    
    return callback
