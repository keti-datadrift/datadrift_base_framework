#!/usr/bin/env python3
"""
YOLO 데이터셋 분할 스크립트

test_yolo 데이터셋을 3개의 독립적인 데이터셋으로 분할:
- yolo_reference: 40% (학습용)
- yolo_current: 40% (학습용)
- yolo_target: 20% (평가용)

각 데이터셋은 YOLO 포맷을 유지하며 랜덤 샘플링으로 자연스러운 분포 차이를 가집니다.
"""

import os
import shutil
import random
import yaml
from pathlib import Path
from typing import List, Tuple
import argparse


def get_image_label_pairs(images_dir: Path, labels_dir: Path) -> List[Tuple[Path, Path]]:
    """
    이미지와 라벨 파일 쌍을 반환
    
    Args:
        images_dir: 이미지 디렉토리
        labels_dir: 라벨 디렉토리
        
    Returns:
        List of (image_path, label_path) tuples
    """
    pairs = []
    
    for img_file in images_dir.glob('*'):
        if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            # 라벨 파일 찾기
            label_file = labels_dir / f"{img_file.stem}.txt"
            if label_file.exists():
                pairs.append((img_file, label_file))
            else:
                print(f"Warning: No label found for {img_file.name}")
    
    return pairs


def split_dataset(pairs: List[Tuple[Path, Path]], ratios: List[float]) -> List[List[Tuple[Path, Path]]]:
    """
    데이터를 지정된 비율로 분할
    
    Args:
        pairs: (image, label) 쌍 리스트
        ratios: 분할 비율 [0.4, 0.4, 0.2]
        
    Returns:
        분할된 데이터 리스트
    """
    # 랜덤 섞기
    random.shuffle(pairs)
    
    total = len(pairs)
    splits = []
    start_idx = 0
    
    for i, ratio in enumerate(ratios):
        if i == len(ratios) - 1:
            # 마지막 분할은 남은 모든 데이터
            end_idx = total
        else:
            end_idx = start_idx + int(total * ratio)
        
        splits.append(pairs[start_idx:end_idx])
        start_idx = end_idx
    
    return splits


def copy_dataset(pairs: List[Tuple[Path, Path]], 
                output_dir: Path,
                split_name: str = 'train'):
    """
    분할된 데이터를 출력 디렉토리로 복사
    
    Args:
        pairs: (image, label) 쌍 리스트
        output_dir: 출력 디렉토리
        split_name: 분할 이름 (train/valid/test)
    """
    # 디렉토리 생성
    images_dir = output_dir / split_name / 'images'
    labels_dir = output_dir / split_name / 'labels'
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)
    
    # 파일 복사
    for img_path, label_path in pairs:
        shutil.copy2(img_path, images_dir / img_path.name)
        shutil.copy2(label_path, labels_dir / label_path.name)
    
    print(f"  Copied {len(pairs)} samples to {split_name}/")


def create_data_yaml(output_dir: Path, dataset_name: str, nc: int = 1, names: List[str] = None):
    """
    data.yaml 파일 생성
    
    Args:
        output_dir: 출력 디렉토리
        dataset_name: 데이터셋 이름
        nc: 클래스 개수
        names: 클래스 이름 리스트
    """
    if names is None:
        names = ['License_Plate']
    
    data_config = {
        'path': str(output_dir.absolute()),
        'train': 'train/images',
        'val': 'valid/images',
        'test': 'test/images',
        'nc': nc,
        'names': names
    }
    
    yaml_path = output_dir / 'data.yaml'
    with open(yaml_path, 'w') as f:
        yaml.dump(data_config, f, default_flow_style=False)
    
    print(f"  Created {yaml_path}")


def main():
    parser = argparse.ArgumentParser(description='Split YOLO dataset into reference, current, and target sets')
    parser.add_argument('--source', type=str, default='datasets/test_yolo',
                       help='Source YOLO dataset directory')
    parser.add_argument('--output-dir', type=str, default='datasets',
                       help='Output directory for split datasets')
    parser.add_argument('--ratios', type=float, nargs=3, default=[0.4, 0.4, 0.2],
                       help='Split ratios for reference, current, target')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for reproducibility')
    
    args = parser.parse_args()
    
    # 시드 설정
    random.seed(args.seed)
    
    # 경로 설정
    source_dir = Path(args.source)
    output_base_dir = Path(args.output_dir)
    
    print(f"🔄 Splitting YOLO dataset from {source_dir}")
    print(f"   Ratios: Reference={args.ratios[0]:.0%}, Current={args.ratios[1]:.0%}, Target={args.ratios[2]:.0%}")
    print(f"   Random seed: {args.seed}\n")
    
    # train 데이터 로드
    train_images_dir = source_dir / 'train' / 'images'
    train_labels_dir = source_dir / 'train' / 'labels'
    
    if not train_images_dir.exists():
        print(f"❌ Error: {train_images_dir} not found")
        return
    
    print(f"📂 Loading train data...")
    train_pairs = get_image_label_pairs(train_images_dir, train_labels_dir)
    print(f"   Found {len(train_pairs)} image-label pairs\n")
    
    # 데이터 분할
    print(f"✂️  Splitting data...")
    splits = split_dataset(train_pairs, args.ratios)
    
    dataset_names = ['yolo_reference', 'yolo_current', 'yolo_target']
    
    for dataset_name, split_data in zip(dataset_names, splits):
        print(f"\n📦 Creating {dataset_name}...")
        output_dir = output_base_dir / dataset_name
        
        # 기존 디렉토리 제거 (선택적)
        if output_dir.exists():
            print(f"   Removing existing {output_dir}")
            shutil.rmtree(output_dir)
        
        # train 데이터 복사
        copy_dataset(split_data, output_dir, 'train')
        
        # valid/test는 원본 test_yolo의 valid/test를 복사 (평가용)
        # 또는 train의 일부를 valid로 사용
        # 여기서는 train의 20%를 valid로 사용
        train_size = int(len(split_data) * 0.8)
        train_subset = split_data[:train_size]
        valid_subset = split_data[train_size:]
        
        copy_dataset(train_subset, output_dir, 'train')
        copy_dataset(valid_subset, output_dir, 'valid')
        
        # 원본의 test 데이터를 복사 (공통 테스트셋)
        source_test_images = source_dir / 'test' / 'images'
        source_test_labels = source_dir / 'test' / 'labels'
        if source_test_images.exists():
            test_pairs = get_image_label_pairs(source_test_images, source_test_labels)
            copy_dataset(test_pairs, output_dir, 'test')
        
        # data.yaml 생성
        create_data_yaml(output_dir, dataset_name)
        
        print(f"✅ {dataset_name} created: {len(split_data)} samples")
    
    print(f"\n🎉 Dataset split complete!")
    print(f"\n📊 Summary:")
    print(f"   yolo_reference: {len(splits[0])} samples")
    print(f"   yolo_current:   {len(splits[1])} samples")
    print(f"   yolo_target:    {len(splits[2])} samples")
    print(f"   Total:          {sum(len(s) for s in splits)} samples")
    
    print(f"\n🔜 Next steps:")
    print(f"   1. Register datasets with DVC:")
    print(f"      ddoc dataset add yolo_reference datasets/yolo_reference")
    print(f"      ddoc dataset add yolo_current datasets/yolo_current")
    print(f"      ddoc dataset add yolo_target datasets/yolo_target")


if __name__ == '__main__':
    main()

