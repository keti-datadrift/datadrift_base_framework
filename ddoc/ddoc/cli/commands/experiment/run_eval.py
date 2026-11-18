"""
Experiment eval command
"""
import typer
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from rich import print

from ....core.trainer_service import get_trainer_service
from ....core.mlflow_experiment_service import get_mlflow_experiment_service
from ..utils import get_dataset_path, _resolve_dataset_reference


def exp_eval_command(
    trainer_name: str = typer.Argument(..., help="Trainer name (directory in code/trainers/)"),
    dataset: str = typer.Option(..., "--dataset", "-d", help="Dataset name or name@version/alias"),
    model_path: str = typer.Option(..., "--model", "-m", help="Path to trained model (searches in models/ first)"),
):
    """
    Evaluate a model using an evaluator from code/trainers/
    
    Examples:
        ddoc exp eval yolo --dataset test_data --model experiments/exp_20241219_120000/best.pt
        ddoc exp eval yolo --dataset test_data@v1.0 --model ./models/best.pt
    """
    print(f"[bold cyan]🔍 Evaluating with trainer: {trainer_name}[/bold cyan]")
    
    # 1. Trainer 검증
    trainer_service = get_trainer_service()
    validation = trainer_service.validate_trainer(trainer_name, mode="eval")
    if not validation["valid"]:
        print(f"[red]❌ {validation['error']}[/red]")
        raise typer.Exit(1)
    
    # 2. Models 디렉토리 설정 및 Ultralytics 설정
    project_root = Path(".").absolute()
    models_dir = project_root / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Ultralytics settings 업데이트
    try:
        from ultralytics import settings
        settings.update({
            "weights_dir": str(models_dir),
            "models_dir": str(models_dir),
        })
    except ImportError:
        # ultralytics가 없으면 무시
        pass
    
    # 3. Model 경로 확인 및 해석
    model_path_obj = Path(model_path)
    
    # 상대 경로인 경우 워크스페이스 기준으로 해석
    if not model_path_obj.is_absolute():
        # models/ 디렉토리에서 먼저 찾기
        if (models_dir / model_path_obj).exists():
            model_path_obj = models_dir / model_path_obj
        # 워크스페이스 루트 기준으로 찾기
        elif (project_root / model_path_obj).exists():
            model_path_obj = project_root / model_path_obj
        # 그대로 사용 (trainer에서 처리)
        else:
            model_path_obj = model_path_obj
    
    # 절대 경로로 변환
    model_path_obj = model_path_obj.resolve()
    
    if not model_path_obj.exists():
        print(f"[red]❌ Model not found: {model_path}[/red]")
        print(f"   Searched in: {models_dir}, {project_root}")
        raise typer.Exit(1)
    
    # 4. Dataset 경로 확인
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
    
    # 5. Dataset 버전 확인
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
    
    # 6. 실험 ID 생성
    exp_id = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    experiments_dir = Path(".") / "experiments"
    experiments_dir.mkdir(exist_ok=True)
    output_dir = experiments_dir / exp_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 7. Evaluator 함수 로드
    eval_func = trainer_service.load_eval_function(trainer_name)
    if eval_func is None:
        print(f"[red]❌ Failed to load evaluate function from {trainer_name}[/red]")
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
                "ddoc.mode": "eval",
                "ddoc.model_path": str(model_path_obj)
            })
            
            # 파라미터 로깅
            mlflow.log_params({
                "trainer": trainer_name,
                "dataset": dataset_name,
                "dataset_version": current_version,
                "model_path": str(model_path_obj),
                **config
            })
            
            print(f"[cyan]🔬 Starting evaluation: {exp_id}[/cyan]")
            print(f"[blue]📊 MLflow Run ID: {run.info.run_id}[/blue]")
            print(f"[blue]📁 Output directory: {output_dir}[/blue]")
            print(f"[blue]🤖 Model: {model_path_obj}[/blue]")
            
            # 10. Evaluator 함수 실행
            try:
                # config.yaml의 내용을 파라미터로 전달
                eval_params = config.copy() if config else {}
                result = eval_func(
                    model_path=model_path_obj,
                    dataset_path=dataset_path,
                    output_dir=output_dir,
                    **eval_params
                )
                
                if not isinstance(result, dict):
                    result = {}
                
                # 11. 결과 처리 및 로깅
                metrics = result.get('metrics', {})
                artifacts = result.get('artifacts', [])
                
                # 메트릭 로깅
                if metrics:
                    for key, value in metrics.items():
                        if isinstance(value, (int, float)):
                            mlflow.log_metric(key, value)
                
                # 아티팩트 로깅
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
                        "model_path": str(model_path_obj),
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
                        "model_path": str(model_path_obj),
                        **config
                    },
                    metrics=metrics,
                    plugin=trainer_name
                )
                
                print(f"[green]✅ Evaluation completed: {exp_id}[/green]")
                print(f"[blue]🔗 Linked to dataset: {dataset_name}@{current_version}[/blue]")
                
                if metrics:
                    print(f"\n[cyan]📈 Metrics:[/cyan]")
                    for k, v in metrics.items():
                        if isinstance(v, (int, float)):
                            print(f"   {k}: {v:.4f}")
                
                print(f"\n[cyan]💡 View in MLflow UI:[/cyan]")
                print(f"   mlflow ui")
                
            except Exception as e:
                print(f"[red]❌ Evaluation failed: {e}[/red]")
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

