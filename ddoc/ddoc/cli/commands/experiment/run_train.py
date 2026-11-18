"""
Experiment train command
"""
import typer
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from rich import print

from ....core.trainer_service import get_trainer_service
from ....core.mlflow_experiment_service import get_mlflow_experiment_service
from ..utils import get_dataset_path, _resolve_dataset_reference


def exp_train_command(
    trainer_name: str = typer.Argument(..., help="Trainer name (directory in code/trainers/)"),
    dataset: str = typer.Option(..., "--dataset", "-d", help="Dataset name or name@version/alias"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name (e.g., yolov8n.pt) or path (e.g., models/custom.pt). If name only, will be downloaded to models/"),
):
    """
    Train a model using a trainer from code/trainers/
    
    Examples:
        ddoc exp train yolo --dataset test_data
        ddoc exp train yolo --dataset test_data@v1.0
        ddoc exp train yolo --dataset test_data --model yolov8n.pt  # Auto-download to models/
        ddoc exp train yolo --dataset test_data --model models/custom.pt  # Use local model
    """
    print(f"[bold cyan]🚀 Training with trainer: {trainer_name}[/bold cyan]")
    
    # 1. Trainer 검증
    trainer_service = get_trainer_service()
    validation = trainer_service.validate_trainer(trainer_name, mode="train")
    if not validation["valid"]:
        print(f"[red]❌ {validation['error']}[/red]")
        raise typer.Exit(1)
    
    # 2. Dataset 경로 확인
    dataset_name, version_or_alias = _resolve_dataset_reference(dataset)
    dataset_path_str = get_dataset_path(dataset_name)
    
    if not dataset_path_str:
        print(f"[red]❌ Dataset not found: {dataset_name}[/red]")
        print("   Provide a valid path or register the dataset with 'ddoc dataset add'")
        raise typer.Exit(1)
    
    dataset_path = Path(dataset_path_str)
    if not dataset_path.exists():
        print(f"[red]❌ Dataset path does not exist: {dataset_path}[/red]")
        raise typer.Exit(1)
    
    # 3. Dataset 버전 확인
    try:
        from ....core.version_service import get_version_service
        version_service = get_version_service()
        version_service.check_version_state(dataset_name)
        
        status = version_service.get_dataset_status(dataset_name)
        
        if version_or_alias:
            resolved_version = version_service.get_dataset_version_by_alias(
                dataset_name, version_or_alias
            )
            if resolved_version:
                current_version = resolved_version
                print(f"📋 Resolved alias '{version_or_alias}' → {current_version}")
            else:
                current_version = version_or_alias
                print(f"📋 Using version: {current_version}")
        else:
            current_version = status['current_version']
            print(f"📋 Current version: {current_version}")
    except Exception as e:
        print(f"[yellow]⚠️  Version check failed: {e}[/yellow]")
        current_version = "unknown"
    
    # 4. Models 디렉토리 설정 및 Ultralytics 설정
    project_root = Path(".").absolute()
    models_dir = project_root / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Ultralytics settings 업데이트 (자동 다운로드 모델을 models/에 저장)
    try:
        from ultralytics import settings
        settings.update({
            "weights_dir": str(models_dir),
            "models_dir": str(models_dir),
        })
        print(f"[blue]📦 Models directory: {models_dir}[/blue]")
    except ImportError:
        # ultralytics가 없으면 무시 (trainer 코드에서 처리)
        pass
    
    # 5. Model 경로 해석
    # --model이 경로처럼 보이면 그대로 사용, 아니면 이름으로 처리
    resolved_model = None
    if model:
        model_path_obj = Path(model)
        # 절대 경로이거나 상대 경로로 존재하는 파일이면 그대로 사용
        if model_path_obj.is_absolute() and model_path_obj.exists():
            resolved_model = str(model_path_obj)
        elif (project_root / model_path_obj).exists():
            resolved_model = str((project_root / model_path_obj).absolute())
        # models/ 디렉토리 기준으로 찾기
        elif (models_dir / model_path_obj.name).exists():
            resolved_model = str((models_dir / model_path_obj.name).absolute())
        # 경로처럼 보이지만 존재하지 않으면 그대로 전달 (trainer에서 처리)
        elif '/' in model or model.endswith('.pt'):
            resolved_model = model
        # 단순 이름이면 그대로 전달 (Ultralytics가 models/에서 찾거나 다운로드)
        else:
            resolved_model = model
    else:
        # model이 지정되지 않았으면 config에서 가져오거나 기본값 사용
        resolved_model = config.get('model') if config else None
    
    # 6. 실험 ID 생성
    exp_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    experiments_dir = project_root / "experiments"
    experiments_dir.mkdir(exist_ok=True)
    output_dir = experiments_dir / exp_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 7. Trainer 함수 로드
    train_func = trainer_service.load_train_function(trainer_name)
    if train_func is None:
        print(f"[red]❌ Failed to load train function from {trainer_name}[/red]")
        raise typer.Exit(1)
    
    # 8. 설정 로드
    config = trainer_service.load_config(trainer_name)
    
    # 9. MLflow 실험 시작
    mlflow_service = get_mlflow_experiment_service()
    
    try:
        import mlflow
        mlflow.set_experiment("ddoc")
        
        with mlflow.start_run(run_name=exp_id) as run:
            # MLflow 태그 설정
            mlflow.set_tags({
                "ddoc.dataset_name": dataset_name,
                "ddoc.dataset_version": current_version,
                "ddoc.dataset_id": f"{dataset_name}@{current_version}",
                "ddoc.experiment_id": exp_id,
                "ddoc.trainer": trainer_name,
                "ddoc.mode": "train"
            })
            
            # 파라미터 로깅
            mlflow.log_params({
                "trainer": trainer_name,
                "dataset": dataset_name,
                "dataset_version": current_version,
                **config  # config.yaml의 내용도 파라미터로 로깅
            })
            
            print(f"[cyan]🔬 Starting experiment: {exp_id}[/cyan]")
            print(f"[blue]📊 MLflow Run ID: {run.info.run_id}[/blue]")
            print(f"[blue]📁 Output directory: {output_dir}[/blue]")
            
            # 10. Trainer 함수 실행
            try:
                # config.yaml의 내용을 파라미터로 전달
                train_params = config.copy() if config else {}
                
                # 해석된 model 경로를 파라미터로 전달
                if resolved_model:
                    train_params['model'] = resolved_model
                
                result = train_func(
                    dataset_path=dataset_path,
                    output_dir=output_dir,
                    **train_params
                )
                
                if not isinstance(result, dict):
                    result = {}
                
                # 11. 결과 처리 및 로깅
                model_path = result.get('model_path')
                metrics = result.get('metrics', {})
                artifacts = result.get('artifacts', [])
                
                # 메트릭 로깅
                if metrics:
                    for key, value in metrics.items():
                        if isinstance(value, (int, float)):
                            mlflow.log_metric(key, value)
                
                # 아티팩트 로깅
                if model_path:
                    model_path_obj = Path(model_path)
                    if model_path_obj.exists():
                        mlflow.log_artifact(str(model_path_obj))
                
                if artifacts:
                    for artifact_path in artifacts:
                        artifact_obj = Path(artifact_path)
                        if artifact_obj.exists():
                            if artifact_obj.is_file():
                                mlflow.log_artifact(str(artifact_obj))
                            elif artifact_obj.is_dir():
                                mlflow.log_artifacts(str(artifact_obj))
                
                # ddoc 메타데이터 저장
                mlflow_service._save_ddoc_metadata(
                    exp_id=exp_id,
                    dataset_name=dataset_name,
                    dataset_version=current_version,
                    params={
                        "trainer": trainer_name,
                        **config
                    },
                    metrics=metrics,
                    mlflow_run_id=run.info.run_id
                )
                
                # 계보 그래프에 연결
                mlflow_service._link_to_lineage(
                    exp_id=exp_id,
                    mlflow_run_id=run.info.run_id,
                    dataset_id=f"{dataset_name}@{current_version}",
                    params={
                        "trainer": trainer_name,
                        **config
                    },
                    metrics=metrics,
                    plugin=trainer_name
                )
                
                print(f"[green]✅ Training completed: {exp_id}[/green]")
                print(f"[blue]🔗 Linked to dataset: {dataset_name}@{current_version}[/blue]")
                
                if metrics:
                    print(f"\n[cyan]📈 Metrics:[/cyan]")
                    for k, v in metrics.items():
                        if isinstance(v, (int, float)):
                            print(f"   {k}: {v:.4f}")
                
                print(f"\n[cyan]💡 View in MLflow UI:[/cyan]")
                print(f"   mlflow ui")
                
            except Exception as e:
                print(f"[red]❌ Training failed: {e}[/red]")
                import traceback
                traceback.print_exc()
                mlflow.log_param("status", "failed")
                mlflow.log_param("error", str(e))
                raise
    
    except ImportError:
        print(f"[red]❌ MLflow not installed. Install with: pip install mlflow[/red]")
        raise typer.Exit(1)
    except Exception as e:
        print(f"[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)

