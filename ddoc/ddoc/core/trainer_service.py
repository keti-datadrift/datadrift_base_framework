"""
Trainer Service for loading and executing trainer/evaluator code
"""
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from rich import print


class TrainerService:
    """
    Trainer 코드 로드 및 실행 서비스
    - code/trainers/{name}/train.py에서 train() 함수 로드
    - code/trainers/{name}/eval.py에서 evaluate() 함수 로드
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.trainers_dir = self.project_root / "code" / "trainers"
    
    def list_trainers(self) -> list[str]:
        """사용 가능한 trainer 목록 반환"""
        if not self.trainers_dir.exists():
            return []
        
        trainers = []
        for item in self.trainers_dir.iterdir():
            if item.is_dir():
                # train.py 또는 eval.py가 있는지 확인
                if (item / "train.py").exists() or (item / "eval.py").exists():
                    trainers.append(item.name)
        
        return sorted(trainers)
    
    def get_trainer_path(self, trainer_name: str) -> Optional[Path]:
        """Trainer 디렉토리 경로 반환"""
        trainer_path = self.trainers_dir / trainer_name
        if trainer_path.exists() and trainer_path.is_dir():
            return trainer_path
        return None
    
    def validate_trainer(self, trainer_name: str, mode: str = "train") -> Dict[str, Any]:
        """
        Trainer 유효성 검증
        
        Args:
            trainer_name: Trainer 이름
            mode: "train" 또는 "eval"
        
        Returns:
            검증 결과 딕셔너리
        """
        trainer_path = self.get_trainer_path(trainer_name)
        if not trainer_path:
            return {
                "valid": False,
                "error": f"Trainer '{trainer_name}' not found in {self.trainers_dir}"
            }
        
        if mode == "train":
            train_file = trainer_path / "train.py"
            if not train_file.exists():
                return {
                    "valid": False,
                    "error": f"train.py not found in {trainer_path}"
                }
        elif mode == "eval":
            eval_file = trainer_path / "eval.py"
            if not eval_file.exists():
                return {
                    "valid": False,
                    "error": f"eval.py not found in {trainer_path}"
                }
        
        return {"valid": True, "trainer_path": trainer_path}
    
    def load_train_function(self, trainer_name: str) -> Optional[Callable]:
        """
        train() 함수 로드
        
        Args:
            trainer_name: Trainer 이름
        
        Returns:
            train 함수 또는 None
        """
        validation = self.validate_trainer(trainer_name, mode="train")
        if not validation["valid"]:
            print(f"[red]❌ {validation['error']}[/red]")
            return None
        
        trainer_path = validation["trainer_path"]
        train_file = trainer_path / "train.py"
        
        try:
            # 모듈 로드
            spec = importlib.util.spec_from_file_location(
                f"trainer_{trainer_name}_train",
                train_file
            )
            if spec is None or spec.loader is None:
                print(f"[red]❌ Failed to load {train_file}[/red]")
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            # train 함수 확인
            if not hasattr(module, "train"):
                print(f"[red]❌ train() function not found in {train_file}[/red]")
                return None
            
            return module.train
            
        except Exception as e:
            print(f"[red]❌ Failed to load trainer: {e}[/red]")
            import traceback
            traceback.print_exc()
            return None
    
    def load_eval_function(self, trainer_name: str) -> Optional[Callable]:
        """
        evaluate() 함수 로드
        
        Args:
            trainer_name: Trainer 이름
        
        Returns:
            evaluate 함수 또는 None
        """
        validation = self.validate_trainer(trainer_name, mode="eval")
        if not validation["valid"]:
            print(f"[red]❌ {validation['error']}[/red]")
            return None
        
        trainer_path = validation["trainer_path"]
        eval_file = trainer_path / "eval.py"
        
        try:
            # 모듈 로드
            spec = importlib.util.spec_from_file_location(
                f"trainer_{trainer_name}_eval",
                eval_file
            )
            if spec is None or spec.loader is None:
                print(f"[red]❌ Failed to load {eval_file}[/red]")
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            # evaluate 함수 확인
            if not hasattr(module, "evaluate"):
                print(f"[red]❌ evaluate() function not found in {eval_file}[/red]")
                return None
            
            return module.evaluate
            
        except Exception as e:
            print(f"[red]❌ Failed to load evaluator: {e}[/red]")
            import traceback
            traceback.print_exc()
            return None
    
    def load_config(self, trainer_name: str) -> Dict[str, Any]:
        """
        Trainer 설정 파일 로드 (config.yaml)
        
        Args:
            trainer_name: Trainer 이름
        
        Returns:
            설정 딕셔너리
        """
        trainer_path = self.get_trainer_path(trainer_name)
        if not trainer_path:
            return {}
        
        config_file = trainer_path / "config.yaml"
        if not config_file.exists():
            return {}
        
        try:
            import yaml
            with open(config_file, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[yellow]⚠️  Warning: Failed to load config.yaml: {e}[/yellow]")
            return {}


# 싱글톤
_trainer_service = None


def get_trainer_service(project_root: str = ".") -> TrainerService:
    """Get global trainer service instance"""
    global _trainer_service
    if _trainer_service is None:
        _trainer_service = TrainerService(project_root)
    return _trainer_service



