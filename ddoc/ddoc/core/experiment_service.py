"""
Experiment Service for ddoc
"""
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from rich import print

from ..ops.core_ops import CoreOpsPlugin


class ExperimentService:
    """
    Experiment management service
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.experiments_dir = self.project_root / "experiments"
        self.core_ops = CoreOpsPlugin(project_root)
    
    def create_experiment_metadata(
        self, 
        name: str, 
        dataset: str, 
        plugin: str, 
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create experiment metadata"""
        # 실험 디렉토리 생성 (실제 실험 시작 시에만)
        self.experiments_dir.mkdir(exist_ok=True)
        
        exp_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        metadata = {
            'experiment_id': exp_id,
            'name': name,
            'dataset': dataset,
            'plugin': plugin,
            'params': params or {},
            'status': 'created',
            'created_at': datetime.now().isoformat(),
            'results': {}
        }
        
        # Save experiment metadata
        exp_dir = self.experiments_dir / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        
        with open(exp_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return metadata
    
    def run_experiment(
        self, 
        name: str,
        params: Dict[str, Any] = None,
        queue: bool = False,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Run experiment"""
        try:
            # Update params.yaml
            if not dry_run:
                self._update_params_yaml(params or {})
            
            # Build DVC command
            dvc_args = ["exp", "run", "--name", name]
            if queue:
                dvc_args.append("--queue")
            
            # Run DVC experiment
            if not dry_run:
                result = self.core_ops._run_dvc_command(
                    dvc_args, 
                    f"Running experiment {name}"
                )
            else:
                result = {"dry_run": True, "command": f"dvc {' '.join(dvc_args)}"}
            
            return {
                "success": True,
                "experiment_name": name,
                "result": result,
                "timestamp": datetime.now().isoformat(),
                "queued": queue,
                "dry_run": dry_run
            }
            
        except Exception as e:
            return {"success": False, "error": f"Experiment failed: {e}"}
    
    def _update_params_yaml(self, params: Dict[str, Any]):
        """Update params.yaml with experiment parameters"""
        try:
            params_file = self.project_root / "params.yaml"
            if params_file.exists():
                with open(params_file, 'r') as f:
                    current_params = yaml.safe_load(f) or {}
            else:
                current_params = {}
            
            # Update with new parameters
            current_params.update(params)
            
            with open(params_file, 'w') as f:
                yaml.dump(current_params, f, default_flow_style=False)
            
            # Stage params.yaml
            # Git operations (optional - only if Git repository exists)
            if (self.project_root / ".git").exists():
                try:
                    self.core_ops._run_git_command(["add", "params.yaml"], "Staging params.yaml")
                except Exception:
                    pass  # Git command failed, skip
            
        except Exception as e:
            print(f"Warning: Failed to update params.yaml: {e}")
    
    def save_experiment_results(self, exp_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Save experiment results"""
        try:
            exp_dir = self.experiments_dir / exp_id
            exp_dir.mkdir(parents=True, exist_ok=True)
            
            # Save metrics
            with open(exp_dir / "metrics.json", 'w') as f:
                json.dump(metrics, f, indent=2)
            
            # Update metadata
            metadata_file = exp_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                metadata['results'] = metrics
                metadata['status'] = 'completed'
                metadata['completed_at'] = datetime.now().isoformat()
                
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            return {"success": True, "experiment_id": exp_id}
        except Exception as e:
            return {"error": f"Failed to save results: {e}"}
    
    def list_experiments(self, dataset: str = None) -> List[Dict[str, Any]]:
        """List experiments"""
        experiments = []
        
        if self.experiments_dir.exists():
            for exp_dir in self.experiments_dir.iterdir():
                if exp_dir.is_dir():
                    metadata_file = exp_dir / "metadata.json"
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                            
                            if dataset is None or metadata.get('dataset') == dataset:
                                experiments.append(metadata)
                        except Exception:
                            continue
        
        return sorted(experiments, key=lambda x: x.get('created_at', ''), reverse=True)
    
    def get_experiment(self, exp_id: str) -> Dict[str, Any]:
        """Get specific experiment"""
        exp_dir = self.experiments_dir / exp_id
        metadata_file = exp_dir / "metadata.json"
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                return {"error": f"Failed to load experiment: {e}"}
        else:
            return {"error": f"Experiment {exp_id} not found"}
    
    def compare_experiments(self, exp_ids: List[str]) -> Dict[str, Any]:
        """Compare experiments"""
        experiments = []
        
        for exp_id in exp_ids:
            exp_info = self.get_experiment(exp_id)
            if "error" not in exp_info:
                experiments.append(exp_info)
        
        if len(experiments) < 2:
            return {"error": "Need at least 2 experiments to compare"}
        
        # Create comparison
        comparison = {
            "experiments": experiments,
            "comparison_metrics": {},
            "best_experiment": None,
            "timestamp": datetime.now().isoformat()
        }
        
        # Simple comparison logic
        if all('results' in exp for exp in experiments):
            # Here you would implement actual metric comparison
            comparison["best_experiment"] = experiments[0]['experiment_id']
        
        return comparison


# Global experiment service instance
_experiment_service = None


def get_experiment_service(project_root: str = ".") -> ExperimentService:
    """Get global experiment service instance"""
    global _experiment_service
    if _experiment_service is None:
        _experiment_service = ExperimentService(project_root)
    return _experiment_service
