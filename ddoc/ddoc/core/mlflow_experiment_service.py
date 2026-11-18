"""
MLflow-based Experiment Service for ddoc
Uses Ultralytics native MLflow integration
"""
import mlflow
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from rich import print
#from ultralytics import settings, YOLO

from .metadata_service import MetadataService
from ..ops.core_ops import CoreOpsPlugin


class MLflowExperimentService:
    """
    MLflow 기반 실험 서비스 (Ultralytics 네이티브 통합)
    - Git 없이 작동
    - ddoc 데이터 버전과 자동 연동
    - 계보 그래프에 실험 추가
    """
    
    def __init__(self, project_root: str = "."):
        pass
    
    def run_experiment(
        self,
        dataset_name: str,
        dataset_version: str,
        model: str = "yolov8n.pt",
        params: Dict[str, Any] = None,
        plugin: str = "yolo"
    ) -> Dict[str, Any]:
        return None
        
    def _extract_metrics(self, results) -> Dict[str, Any]:
        return None
    
    def _save_ddoc_metadata(
        self,
        exp_id: str,
        dataset_name: str,
        dataset_version: str,
        params: Dict[str, Any],
        metrics: Dict[str, Any],
        mlflow_run_id: str
    ):
        return None
        
    def _link_to_lineage(
        self,
        exp_id: str,
        mlflow_run_id: str,
        dataset_id: str,
        params: Dict[str, Any],
        metrics: Dict[str, Any],
        plugin: str
    ):
        return None
    
    def get_experiments_by_dataset(
        self,
        dataset_name: str,
        dataset_version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return None
        
    def compare_experiments(
        self,
        exp_ids: List[str]
    ) -> Dict[str, Any]:
        """여러 실험 비교"""
        comparison = {
            "experiments": [],
            "metrics_comparison": {}
        }
        
        return None
        
    def get_best_experiment_for_dataset(
        self,
        dataset_name: str,
        dataset_version: str,
        metric: str = "metrics.mAP50-95"
    ) -> Optional[Dict[str, Any]]:
        
        return None


# 싱글톤
_mlflow_exp_service = None


def get_mlflow_experiment_service(project_root: str = ".") -> MLflowExperimentService:
    """Get global MLflow experiment service instance"""
    global _mlflow_exp_service
    if _mlflow_exp_service is None:
        _mlflow_exp_service = MLflowExperimentService(project_root)
    return _mlflow_exp_service

