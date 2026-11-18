"""
YOLO Training Plugin Implementation for ddoc

Provides hookimpl for:
- retrain_run: YOLO model training and evaluation
"""
from pathlib import Path
from datetime import datetime
import json
import yaml
import os
import subprocess
from typing import Dict, Any, Optional, List

try:
    from ddoc.plugins.hookspecs import hookimpl
    from ddoc.tracking.experiment_interface import TrainingPlugin, ExperimentResult, DVCCompatibleMetadata
except ImportError:
    # Fallback for development/testing
    def hookimpl(func):
        return func
    
    # Mock classes for development
    class TrainingPlugin:
        pass
    class ExperimentResult:
        pass
    class DVCCompatibleMetadata:
        pass

try:
    from ultralytics import YOLO
except ImportError:  # pragma: no cover - optional dependency
    YOLO = None


class DDOCYoloPlugin(TrainingPlugin):
    """YOLO Training Plugin for ddoc - 표준 인터페이스 구현"""
    
    def __init__(self):
        self.model = None
        self.supported_models = [
            'yolov8n.pt', 'yolov8s.pt', 'yolov8m.pt', 'yolov8l.pt', 'yolov8x.pt',
            'yolov10n.pt', 'yolov10s.pt', 'yolov10m.pt', 'yolov10l.pt', 'yolov10x.pt'
        ]
        self.default_params = {
            'model': 'yolov8n.pt',
            'epochs': 100,
            'batch': 16,
            'imgsz': 640,
            'device': 'cpu',
            'patience': 50,
            'save': True,
            'save_period': 10,
            'cache': False,
            'workers': 8,
            'project': 'experiments',
            'name': None,
            'exist_ok': False,
            'pretrained': True,
            'optimizer': 'auto',
            'verbose': True,
            'seed': 0,
            'deterministic': True,
            'single_cls': False,
            'rect': False,
            'cos_lr': False,
            'close_mosaic': 10,
            'resume': False,
            'amp': True,
            'fraction': 1.0,
            'profile': False,
            'freeze': None,
            'lr0': 0.01,
            'lrf': 0.01,
            'momentum': 0.937,
            'weight_decay': 0.0005,
            'warmup_epochs': 3.0,
            'warmup_momentum': 0.8,
            'warmup_bias_lr': 0.1,
            'box': 7.5,
            'cls': 0.5,
            'dfl': 1.5,
            'pose': 12.0,
            'kobj': 1.0,
            'label_smoothing': 0.0,
            'nbs': 64,
            'overlap_mask': True,
            'mask_ratio': 4,
            'dropout': 0.0,
            'val': True
        }
    
    @hookimpl
    def retrain_run(
        self, 
        train_path: str, 
        trainer: str, 
        params: Dict[str, Any], 
        model_out: str
    ) -> Optional[Dict[str, Any]]:
        """
        Train YOLO model
        
        Args:
            train_path: Path to dataset directory
            trainer: Trainer type (should be "yolo")
            params: Training parameters
            model_out: Output directory for model and results
        
        Returns:
            Dict with training metrics
        """
        if trainer != "yolo":
            print(f"⚠️ YOLO plugin only supports 'yolo' trainer, got '{trainer}'")
            return None

        if YOLO is None:
            return {
                "status": "error",
                "message": "Ultralytics dependency is not installed. Install with 'pip install ddoc[yolo]' on Python 3.10+ or add a compatible ultralytics version manually."
            }
        
        train_path = Path(train_path)
        model_out = Path(model_out)
        model_out.mkdir(parents=True, exist_ok=True)
        
        print(f"🚀 YOLO Training Started")
        print(f"=" * 80)
        print(f"Dataset: {train_path}")
        print(f"Output: {model_out}")
        print()
        
        # Extract parameters
        model_name = params.get('model', 'yolov8n.pt')
        data_yaml = params.get('data_yaml')
        epochs = params.get('epochs', 100)
        imgsz = params.get('imgsz', 640)
        batch = params.get('batch', 16)
        exp_name = params.get('exp_name', f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        device = params.get('device', 'cpu')
        
        # Create data.yaml if not provided
        if not data_yaml:
            data_yaml = self._create_data_yaml(train_path, params)
        
        if not data_yaml or not Path(data_yaml).exists():
            print(f"❌ data.yaml not found: {data_yaml}")
            return {
                "status": "error",
                "message": f"data.yaml not found: {data_yaml}"
            }
        
        print(f"📋 Training Configuration:")
        print(f"   Model: {model_name}")
        print(f"   Data YAML: {data_yaml}")
        print(f"   Epochs: {epochs}")
        print(f"   Image Size: {imgsz}")
        print(f"   Batch Size: {batch}")
        print(f"   Device: {device}")
        print(f"   Experiment Name: {exp_name}")
        print()
        
        try:
            # Load model
            print(f"📦 Loading model: {model_name}")
            self.model = YOLO(model_name)
            print(f"✅ Model loaded successfully")
            print()
            
            # Train
            print(f"🏋️ Training started...")
            results = self.model.train(
                data=str(data_yaml),
                epochs=epochs,
                imgsz=imgsz,
                batch=batch,
                project=str(model_out),
                name=exp_name,
                device=device,
                exist_ok=True,
                verbose=True
            )
            
            print()
            print(f"✅ Training completed!")
            
            # Extract metrics from results
            metrics = self._extract_metrics(results, model_out / exp_name)
            
            # Save experiment metadata
            metadata = {
                'exp_name': exp_name,
                'model': model_name,
                'dataset': str(train_path),
                'data_yaml': str(data_yaml),
                'epochs': epochs,
                'imgsz': imgsz,
                'batch': batch,
                'device': device,
                'timestamp': datetime.now().isoformat(),
                'metrics': metrics,
                'output_dir': str(model_out / exp_name)
            }
            
            metadata_file = model_out / exp_name / "experiment_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"\n📊 Training Metrics:")
            print(f"   mAP50: {metrics.get('mAP50', 'N/A')}")
            print(f"   mAP50-95: {metrics.get('mAP50-95', 'N/A')}")
            print(f"   Precision: {metrics.get('precision', 'N/A')}")
            print(f"   Recall: {metrics.get('recall', 'N/A')}")
            print(f"\n📄 Metadata: {metadata_file}")
            print(f"🏆 Best Model: {model_out / exp_name / 'weights' / 'best.pt'}")
            
            return metadata
            
        except Exception as e:
            print(f"❌ Training failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _create_data_yaml(self, dataset_path: Path, params: Dict[str, Any]) -> Optional[str]:
        """
        Create data.yaml for YOLO training
        
        Args:
            dataset_path: Path to dataset directory
            params: Parameters dict that may contain class names and paths
        
        Returns:
            Path to created data.yaml or None
        """
        # Check if dataset follows YOLO structure
        train_dir = dataset_path / "train" / "images"
        val_dir = dataset_path / "val" / "images"
        
        if not train_dir.exists() or not val_dir.exists():
            print(f"⚠️ Dataset doesn't follow YOLO structure (train/images, val/images)")
            print(f"   Expected: {train_dir}")
            print(f"   Expected: {val_dir}")
            return None
        
        # Try to infer classes from labels
        labels_dir = dataset_path / "train" / "labels"
        classes = params.get('classes', [])
        
        if not classes and labels_dir.exists():
            # Try to read classes from a classes.txt file if it exists
            classes_file = dataset_path / "classes.txt"
            if classes_file.exists():
                with open(classes_file, 'r') as f:
                    classes = [line.strip() for line in f if line.strip()]
        
        if not classes:
            classes = ['object']  # Default class
            print(f"⚠️ No classes specified, using default: {classes}")
        
        # Create data.yaml
        data_config = {
            'path': str(dataset_path.absolute()),
            'train': 'train/images',
            'val': 'val/images',
            'nc': len(classes),
            'names': classes
        }
        
        # Add test set if it exists
        test_dir = dataset_path / "test" / "images"
        if test_dir.exists():
            data_config['test'] = 'test/images'
        
        data_yaml_path = dataset_path / "data.yaml"
        with open(data_yaml_path, 'w') as f:
            yaml.dump(data_config, f, default_flow_style=False)
        
        print(f"📝 Created data.yaml: {data_yaml_path}")
        print(f"   Classes ({len(classes)}): {', '.join(classes)}")
        
        return str(data_yaml_path)
    
    def _extract_metrics(self, results, exp_dir: Path) -> Dict[str, Any]:
        """
        Extract metrics from training results
        
        Args:
            results: YOLO training results object
            exp_dir: Experiment directory
        
        Returns:
            Dict with extracted metrics
        """
        metrics = {}
        
        try:
            # Try to read from results.csv if it exists
            results_csv = exp_dir / "results.csv"
            if results_csv.exists():
                import pandas as pd
                df = pd.read_csv(results_csv)
                
                # Get last row (final epoch metrics)
                if len(df) > 0:
                    last_row = df.iloc[-1]
                    
                    # Extract common YOLO metrics
                    metric_mapping = {
                        'metrics/mAP50(B)': 'mAP50',
                        'metrics/mAP50-95(B)': 'mAP50-95',
                        'metrics/precision(B)': 'precision',
                        'metrics/recall(B)': 'recall',
                        'train/box_loss': 'box_loss',
                        'train/cls_loss': 'cls_loss',
                        'train/dfl_loss': 'dfl_loss',
                        'val/box_loss': 'val_box_loss',
                        'val/cls_loss': 'val_cls_loss',
                        'val/dfl_loss': 'val_dfl_loss',
                    }
                    
                    for csv_col, metric_name in metric_mapping.items():
                        if csv_col in df.columns:
                            value = last_row[csv_col]
                            if pd.notna(value):
                                metrics[metric_name] = float(value)
            
            # Try to extract from results object directly
            if hasattr(results, 'results_dict'):
                results_dict = results.results_dict
                for key, value in results_dict.items():
                    if isinstance(value, (int, float)):
                        metrics[key] = float(value)
            
        except Exception as e:
            print(f"⚠️ Could not extract metrics: {e}")
        
        return metrics
    
    @hookimpl
    def ddoc_get_metadata(self) -> Dict[str, Any]:
        """Return plugin metadata"""
        return {
            "name": "ddoc-plugin-yolo",
            "version": "0.1.0",
            "description": "YOLO training plugin for object detection",
            "hooks": ["retrain_run"],
            "models": ["yolov8n", "yolov8s", "yolov8m", "yolov8l", "yolov8x", 
                      "yolov10n", "yolov10s", "yolov10m", "yolov10l", "yolov10x"]
        }
    
    # 새로운 표준 인터페이스 메서드들
    def train(self, dataset: str, params: Dict[str, Any], output_dir: str) -> ExperimentResult:
        """
        표준화된 학습 인터페이스
        
        Args:
            dataset: 데이터셋 이름
            params: 학습 파라미터
            output_dir: 결과 저장 디렉토리
            
        Returns:
            ExperimentResult: 실험 결과
        """
        # 파라미터 병합
        training_params = self.default_params.copy()
        training_params.update(params)
        
        # 실험 ID 생성
        experiment_id = f"yolo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 데이터셋 경로 설정
        dataset_path = f"datasets/{dataset}"
        data_yaml = os.path.join(dataset_path, "data.yaml")
        
        if not os.path.exists(data_yaml):
            # data.yaml 자동 생성
            self._create_data_yaml(dataset, data_yaml)
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        # YOLO 모델 초기화
        model_name = training_params.get('model', 'yolov8n.pt')
        model = YOLO(model_name)
        
        # 학습 실행
        start_time = datetime.now()
        
        try:
            results = model.train(
                data=data_yaml,
                epochs=training_params.get('epochs', 100),
                batch=training_params.get('batch', 16),
                imgsz=training_params.get('imgsz', 640),
                device=training_params.get('device', 'cpu'),
                project=output_dir,
                name=experiment_id,
                exist_ok=True,
                **{k: v for k, v in training_params.items() if k not in ['model', 'epochs', 'batch', 'imgsz', 'device', 'project', 'name']}
            )
            
            end_time = datetime.now()
            
            # 메트릭 추출
            metrics = self._extract_metrics(results, Path(output_dir))
            
            # 실험 결과 생성
            result = ExperimentResult(
                experiment_id=experiment_id,
                dataset=dataset,
                plugin='yolo',
                status='completed',
                start_time=start_time,
                end_time=end_time,
                metrics=metrics,
                params=training_params,
                output_dir=output_dir,
                logs=[f"Training completed successfully in {end_time - start_time}"]
            )
            
            # 결과 저장
            self._save_experiment_results(result, output_dir)
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            return ExperimentResult(
                experiment_id=experiment_id,
                dataset=dataset,
                plugin='yolo',
                status='failed',
                start_time=start_time,
                end_time=end_time,
                params=training_params,
                output_dir=output_dir,
                logs=[f"Training failed: {str(e)}"]
            )
    
    def generate_dvc_metadata(self, result: ExperimentResult) -> DVCCompatibleMetadata:
        """
        DVC 호환 메타데이터 생성
        
        Args:
            result: 실험 결과
            
        Returns:
            DVCCompatibleMetadata: DVC 호환 메타데이터
        """
        return DVCCompatibleMetadata(
            experiment_id=result.experiment_id,
            dataset=result.dataset,
            plugin=result.plugin,
            params=result.params,
            metrics=result.metrics,
            dependencies=[f"datasets/{result.dataset}", "params.yaml"],
            outputs=[
                f"{result.output_dir}/weights/",
                f"{result.output_dir}/results.csv",
                f"{result.output_dir}/experiment_metadata.json"
            ],
            timestamp=result.start_time.isoformat(),
            git_commit=self._get_git_commit()
        )
    
    def save_logs(self, result: ExperimentResult, output_dir: str, format: str = 'dvc') -> str:
        """
        DVC 호환 로그 저장
        
        Args:
            result: 실험 결과
            output_dir: 출력 디렉토리
            format: 로그 형식 ('dvc', 'json', 'csv')
            
        Returns:
            str: 로그 파일 경로
        """
        if format == 'dvc':
            # DVC 호환 JSON 형식
            log_data = {
                'experiment_id': result.experiment_id,
                'dataset': result.dataset,
                'plugin': result.plugin,
                'status': result.status,
                'start_time': result.start_time.isoformat(),
                'end_time': result.end_time.isoformat() if result.end_time else None,
                'metrics': result.metrics,
                'params': result.params,
                'logs': result.logs
            }
            
            log_file = os.path.join(output_dir, 'experiment_log.json')
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            return log_file
        
        elif format == 'json':
            # 표준 JSON 형식
            log_file = os.path.join(output_dir, 'training_log.json')
            with open(log_file, 'w') as f:
                json.dump({
                    'experiment_id': result.experiment_id,
                    'metrics': result.metrics,
                    'params': result.params
                }, f, indent=2)
            
            return log_file
        
        elif format == 'csv':
            # CSV 형식 (메트릭만)
            import pandas as pd
            
            log_file = os.path.join(output_dir, 'metrics.csv')
            metrics_df = pd.DataFrame([result.metrics])
            metrics_df.to_csv(log_file, index=False)
            
            return log_file
        
        else:
            raise ValueError(f"Unsupported log format: {format}")
    
    def get_supported_models(self) -> List[str]:
        """지원하는 모델 목록 반환"""
        return self.supported_models
    
    def get_default_params(self) -> Dict[str, Any]:
        """기본 파라미터 반환"""
        return self.default_params.copy()
    
    def _create_data_yaml(self, train_path: str, params: Dict[str, Any]) -> str:
        """data.yaml 파일 자동 생성"""
        dataset_path = train_path if os.path.isabs(train_path) else os.path.abspath(train_path)
        
        # data.yaml 파일 경로
        data_yaml_path = os.path.join(dataset_path, "data.yaml")
        
        # 클래스 정보 추출 (간단한 휴리스틱)
        classes = self._extract_classes_from_dataset(dataset_path)
        
        data_config = {
            'path': dataset_path,
            'train': 'train/images',
            'val': 'valid/images',
            'test': 'test/images',
            'nc': len(classes),
            'names': classes
        }
        
        with open(data_yaml_path, 'w') as f:
            yaml.dump(data_config, f, default_flow_style=False)
        
        return data_yaml_path
    
    def _extract_classes_from_dataset(self, dataset_path: str) -> List[str]:
        """데이터셋에서 클래스 정보 추출"""
        # 간단한 휴리스틱: 라벨 파일에서 클래스 추출
        labels_dir = os.path.join(dataset_path, 'labels')
        if os.path.exists(labels_dir):
            # YOLO 형식 라벨에서 클래스 ID 추출
            class_ids = set()
            for label_file in os.listdir(labels_dir):
                if label_file.endswith('.txt'):
                    with open(os.path.join(labels_dir, label_file), 'r') as f:
                        for line in f:
                            if line.strip():
                                class_id = int(line.split()[0])
                                class_ids.add(class_id)
            
            # 클래스 이름 생성
            return [f"class_{i}" for i in sorted(class_ids)]
        
        # 기본 클래스
        return ['object']
    
    def _save_experiment_results(self, result: ExperimentResult, output_dir: str):
        """실험 결과 저장"""
        # 실험 메타데이터 저장
        metadata = {
            'experiment_id': result.experiment_id,
            'dataset': result.dataset,
            'plugin': result.plugin,
            'status': result.status,
            'start_time': result.start_time.isoformat(),
            'end_time': result.end_time.isoformat() if result.end_time else None,
            'metrics': result.metrics,
            'params': result.params,
            'output_dir': result.output_dir
        }
        
        metadata_file = os.path.join(output_dir, 'experiment_metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # 메트릭 파일 저장
        metrics_file = os.path.join(output_dir, 'metrics.json')
        with open(metrics_file, 'w') as f:
            json.dump(result.metrics, f, indent=2)
    
    def _get_git_commit(self) -> str:
        """현재 Git 커밋 해시 반환"""
        try:
            result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], 
                                  capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return 'unknown'

