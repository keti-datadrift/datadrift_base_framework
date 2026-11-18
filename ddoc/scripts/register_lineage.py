#!/usr/bin/env python3
"""
기존 데이터를 lineage 시스템에 등록하는 스크립트
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ddoc.tracking.lineage_tracker import LineageTracker
from ddoc.tracking.experiment_tracker import ExperimentTracker
import json

def register_existing_data():
    """기존 데이터를 lineage에 등록"""
    lineage_tracker = LineageTracker()
    experiment_tracker = ExperimentTracker()
    
    print("🔗 Registering existing data to lineage system...")
    
    # 1. 데이터셋 등록
    datasets = [
        ("test_yolo", "test_yolo", {"type": "yolo_dataset", "path": "datasets/test_yolo"}),
        ("test_data", "test_data", {"type": "general_dataset", "path": "datasets/test_data"}),
        ("yolo_reference", "yolo_reference", {"type": "yolo_dataset", "path": "datasets/yolo_reference"}),
        ("yolo_current", "yolo_current", {"type": "yolo_dataset", "path": "datasets/yolo_current"}),
        ("yolo_target", "yolo_target", {"type": "yolo_dataset", "path": "datasets/yolo_target"}),
    ]
    
    for dataset_id, dataset_name, metadata in datasets:
        lineage_tracker.add_dataset(dataset_id, dataset_name, metadata)
        print(f"  ✅ Registered dataset: {dataset_name}")
    
    # 2. 분석 등록
    analyses = [
        ("analysis_test_yolo", "test_yolo EDA", "test_yolo", {"type": "eda", "output": "analysis/test_yolo"}),
        ("analysis_test_data", "test_data EDA", "test_data", {"type": "eda", "output": "analysis/test_data"}),
        ("analysis_yolo_reference", "yolo_reference EDA", "yolo_reference", {"type": "eda", "output": "analysis/yolo_reference"}),
        ("analysis_yolo_current", "yolo_current EDA", "yolo_current", {"type": "eda", "output": "analysis/yolo_current"}),
        ("analysis_yolo_target", "yolo_target EDA", "yolo_target", {"type": "eda", "output": "analysis/yolo_target"}),
    ]
    
    for analysis_id, analysis_name, dataset_id, metadata in analyses:
        lineage_tracker.add_analysis(analysis_id, analysis_name, dataset_id, metadata)
        print(f"  ✅ Registered analysis: {analysis_name}")
    
    # 3. 실험 등록
    experiments = experiment_tracker.list_experiments()
    for exp in experiments:
        exp_id = exp.get('exp_name', exp.get('experiment_id', 'unknown'))
        exp_name = exp.get('exp_name', exp_id)
        dataset = exp.get('dataset', 'unknown')
        
        # 데이터셋 ID 추출 (경로에서)
        if 'datasets/' in dataset:
            dataset_id = dataset.split('datasets/')[-1]
        else:
            dataset_id = dataset
        
        metadata = {
            'model': exp.get('model', 'unknown'),
            'epochs': exp.get('epochs', 0),
            'batch': exp.get('batch', 0),
            'device': exp.get('device', 'unknown'),
            'metrics': exp.get('metrics', {})
        }
        
        lineage_tracker.add_experiment(exp_id, exp_name, dataset_id, metadata)
        print(f"  ✅ Registered experiment: {exp_name}")
    
    # 4. 드리프트 분석 등록
    drift_analyses = [
        ("drift_target_vs_ref", "Target vs Reference Drift", "yolo_target", "yolo_reference", {"type": "drift_analysis", "output": "analysis/drift_target_vs_ref"}),
        ("drift_target_vs_cur", "Target vs Current Drift", "yolo_target", "yolo_current", {"type": "drift_analysis", "output": "analysis/drift_target_vs_cur"}),
    ]
    
    for drift_id, drift_name, ref_dataset, cur_dataset, metadata in drift_analyses:
        lineage_tracker.add_drift_analysis(drift_id, drift_name, ref_dataset, cur_dataset, metadata)
        print(f"  ✅ Registered drift analysis: {drift_name}")
    
    print(f"\n🎉 Successfully registered {len(datasets)} datasets, {len(analyses)} analyses, {len(experiments)} experiments, {len(drift_analyses)} drift analyses")
    print("🔗 Lineage system is now ready!")

if __name__ == "__main__":
    register_existing_data()
