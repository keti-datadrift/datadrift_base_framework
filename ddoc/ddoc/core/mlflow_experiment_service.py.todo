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
from ultralytics import settings, YOLO

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
        self.project_root = Path(project_root)
        self.experiments_dir = self.project_root / "experiments"
        self.mlruns_dir = self.project_root / "mlruns"
        
        # MLflow tracking URI 설정
        tracking_uri = f"file://{self.mlruns_dir.absolute()}"
        os.environ['MLFLOW_TRACKING_URI'] = tracking_uri
        mlflow.set_tracking_uri(tracking_uri)
        
        # Ultralytics MLflow 통합 활성화
        settings.update({
            "mlflow": True,
            "runs_dir": str(self.experiments_dir)  # 실험 결과 저장 위치
        })
        
        # ddoc 서비스 연동
        self.metadata_service = MetadataService(project_root)
        self.core_ops = CoreOpsPlugin(project_root)
    
    def run_experiment(
        self,
        dataset_name: str,
        dataset_version: str,
        model: str = "yolov8n.pt",
        params: Dict[str, Any] = None,
        plugin: str = "yolo"
    ) -> Dict[str, Any]:
        """
        MLflow를 사용한 실험 실행 (Ultralytics 네이티브 통합)
        
        Args:
            dataset_name: 데이터셋 이름
            dataset_version: 데이터셋 버전
            model: 모델 경로
            params: 학습 파라미터
            plugin: 플러그인 이름
        
        Returns:
            실험 결과 딕셔너리
        """
        params = params or {}
        exp_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        dataset_id = f"{dataset_name}@{dataset_version}"
        
        try:
            # MLflow experiment 설정 (ddoc namespace)
            mlflow.set_experiment("ddoc")
            
            # MLflow run 시작 (context manager로 자동 종료)
            with mlflow.start_run(run_name=exp_id) as run:
                
                # 1. ddoc 메타데이터를 MLflow 태그로 설정
                mlflow.set_tags({
                    "ddoc.dataset_name": dataset_name,
                    "ddoc.dataset_version": dataset_version,
                    "ddoc.dataset_id": dataset_id,
                    "ddoc.experiment_id": exp_id,
                    "ddoc.plugin": plugin
                })
                
                # 2. YOLO 학습 실행
                # Ultralytics가 자동으로 모든 것을 MLflow에 로깅
                print(f"[cyan]🔬 Starting experiment: {exp_id}[/cyan]")
                print(f"[blue]📊 MLflow Run ID: {run.info.run_id}[/blue]")
                
                yolo_model = YOLO(model)
                results = yolo_model.train(
                    data=params.get('data_yaml'),
                    epochs=params.get('epochs', 100),
                    batch=params.get('batch', 16),
                    imgsz=params.get('imgsz', 640),
                    device=params.get('device', 'cpu'),
                    project=str(self.experiments_dir),
                    name=exp_id,
                    exist_ok=True
                )
                
                # 3. 학습 결과 메트릭 추출
                metrics = self._extract_metrics(results)
                
                # 4. ddoc 메타데이터 저장
                self._save_ddoc_metadata(
                    exp_id=exp_id,
                    dataset_name=dataset_name,
                    dataset_version=dataset_version,
                    params=params,
                    metrics=metrics,
                    mlflow_run_id=run.info.run_id
                )
                
                # 5. 계보 그래프에 연결
                self._link_to_lineage(
                    exp_id=exp_id,
                    mlflow_run_id=run.info.run_id,
                    dataset_id=dataset_id,
                    params=params,
                    metrics=metrics,
                    plugin=plugin
                )
                
                print(f"[green]✅ Experiment completed: {exp_id}[/green]")
                print(f"[blue]🔗 Linked to dataset: {dataset_id}[/blue]")
                
                return {
                    "success": True,
                    "experiment_id": exp_id,
                    "mlflow_run_id": run.info.run_id,
                    "dataset_id": dataset_id,
                    "metrics": metrics,
                    "results_dir": str(self.experiments_dir / exp_id),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            print(f"[red]❌ Experiment failed: {e}[/red]")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "experiment_id": exp_id,
                "error": str(e)
            }
    
    def _extract_metrics(self, results) -> Dict[str, Any]:
        """YOLO 학습 결과에서 메트릭 추출"""
        try:
            # results.results_dict에서 최종 메트릭 추출
            metrics_dict = results.results_dict if hasattr(results, 'results_dict') else {}
            
            return {
                'mAP50': float(metrics_dict.get('metrics/mAP50(B)', 0)),
                'mAP50-95': float(metrics_dict.get('metrics/mAP50-95(B)', 0)),
                'precision': float(metrics_dict.get('metrics/precision(B)', 0)),
                'recall': float(metrics_dict.get('metrics/recall(B)', 0)),
                'fitness': float(metrics_dict.get('fitness', 0))
            }
        except Exception as e:
            print(f"[yellow]Warning: Could not extract metrics: {e}[/yellow]")
            return {}
    
    def _save_ddoc_metadata(
        self,
        exp_id: str,
        dataset_name: str,
        dataset_version: str,
        params: Dict[str, Any],
        metrics: Dict[str, Any],
        mlflow_run_id: str
    ):
        """ddoc 실험 메타데이터 저장"""
        exp_dir = self.experiments_dir / exp_id
        
        metadata = {
            "experiment_id": exp_id,
            "mlflow_run_id": mlflow_run_id,
            "dataset": {
                "name": dataset_name,
                "version": dataset_version,
                "id": f"{dataset_name}@{dataset_version}"
            },
            "params": params,
            "metrics": metrics,
            "created_at": datetime.now().isoformat(),
            "mlflow_tracking_uri": os.environ.get('MLFLOW_TRACKING_URI'),
            "view_command": f"mlflow ui --backend-store-uri {self.mlruns_dir}"
        }
        
        metadata_file = exp_dir / "ddoc_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _link_to_lineage(
        self,
        exp_id: str,
        mlflow_run_id: str,
        dataset_id: str,
        params: Dict[str, Any],
        metrics: Dict[str, Any],
        plugin: str
    ):
        """실험을 ddoc 계보 그래프에 연결"""
        self.metadata_service.add_experiment(
            experiment_id=exp_id,
            experiment_name=exp_id,
            dataset_id=dataset_id,
            metadata={
                "mlflow_run_id": mlflow_run_id,
                "plugin": plugin,
                "params": params,
                "metrics": metrics,
                "timestamp": datetime.now().isoformat(),
                "tracking_type": "mlflow_ultralytics"
            }
        )
    
    def get_experiments_by_dataset(
        self,
        dataset_name: str,
        dataset_version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """특정 데이터셋의 모든 실험 조회"""
        if dataset_version:
            filter_string = f"tags.`ddoc.dataset_id` = '{dataset_name}@{dataset_version}'"
        else:
            filter_string = f"tags.`ddoc.dataset_name` = '{dataset_name}'"
        
        try:
            runs = mlflow.search_runs(
                experiment_names=["ddoc"],
                filter_string=filter_string,
                order_by=["start_time DESC"]
            )
            return runs.to_dict('records') if not runs.empty else []
        except Exception as e:
            print(f"[yellow]Warning: Could not search MLflow runs: {e}[/yellow]")
            return []
    
    def compare_experiments(
        self,
        exp_ids: List[str]
    ) -> Dict[str, Any]:
        """여러 실험 비교"""
        comparison = {
            "experiments": [],
            "metrics_comparison": {}
        }
        
        for exp_id in exp_ids:
            try:
                runs = mlflow.search_runs(
                    experiment_names=["ddoc"],
                    filter_string=f"tags.`ddoc.experiment_id` = '{exp_id}'"
                )
                
                if not runs.empty:
                    run = runs.iloc[0].to_dict()
                    comparison["experiments"].append({
                        "experiment_id": exp_id,
                        "mlflow_run_id": run['run_id'],
                        "dataset_id": run.get('tags.ddoc.dataset_id'),
                        "metrics": {
                            k.replace('metrics.', ''): v 
                            for k, v in run.items() 
                            if k.startswith('metrics.') and v is not None
                        }
                    })
            except Exception as e:
                print(f"[yellow]Warning: Could not retrieve experiment {exp_id}: {e}[/yellow]")
        
        return comparison
    
    def get_best_experiment_for_dataset(
        self,
        dataset_name: str,
        dataset_version: str,
        metric: str = "metrics.mAP50-95"
    ) -> Optional[Dict[str, Any]]:
        """데이터셋 버전의 최고 성능 실험 찾기"""
        runs = self.get_experiments_by_dataset(dataset_name, dataset_version)
        
        if not runs:
            return None
        
        # 메트릭 기준 정렬
        valid_runs = [r for r in runs if r.get(metric) is not None]
        if not valid_runs:
            return None
        
        best_run = max(valid_runs, key=lambda x: float(x.get(metric, 0)))
        
        return best_run


# 싱글톤
_mlflow_exp_service = None


def get_mlflow_experiment_service(project_root: str = ".") -> MLflowExperimentService:
    """Get global MLflow experiment service instance"""
    global _mlflow_exp_service
    if _mlflow_exp_service is None:
        _mlflow_exp_service = MLflowExperimentService(project_root)
    return _mlflow_exp_service

