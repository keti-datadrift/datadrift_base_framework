"""
Sampling Service for ddoc-workspace
Provides data exploration, modification, sampling strategies, and export functionality.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import os
import shutil
import json
import random
import hashlib
from datetime import datetime
import yaml

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


class DatasetFormat(Enum):
    """Supported dataset formats"""
    YOLO = "yolo"
    COCO = "coco"
    VOC = "voc"
    UNKNOWN = "unknown"


class SamplingStrategy(Enum):
    """Sampling strategies"""
    RANDOM = "random"
    STRATIFIED = "stratified"
    THRESHOLD = "threshold"


@dataclass
class DataItem:
    """Represents a single data item (image + optional label)"""
    id: str
    filename: str
    path: str
    split: Optional[str] = None
    label: Optional[str] = None
    label_path: Optional[str] = None
    size_bytes: int = 0
    width: Optional[int] = None
    height: Optional[int] = None
    classes: List[str] = field(default_factory=list)


@dataclass
class DatasetStats:
    """Dataset statistics"""
    total_items: int
    total_size_mb: float
    format: DatasetFormat
    splits: Dict[str, int]
    classes: Dict[str, int]
    image_stats: Optional[Dict[str, Any]] = None


IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp'}
LABEL_EXTENSIONS = {'.txt', '.xml', '.json'}


class SamplingService:
    """
    Service for data exploration, modification, sampling, and export.
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.data_dir = self._find_data_directory()
        self.format = self._detect_format()
    
    def _find_data_directory(self) -> Path:
        """Find the actual data directory in workspace"""
        data_dir = self.workspace_path / "data"
        if not data_dir.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
            return data_dir
        
        # Check for subdirectory (dataset folder)
        subdirs = [d for d in data_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if subdirs:
            return subdirs[0]
        return data_dir
    
    def _detect_format(self) -> DatasetFormat:
        """Detect dataset format based on structure"""
        if not self.data_dir.exists():
            return DatasetFormat.UNKNOWN
        
        # Check for YOLO format (images/ + labels/)
        has_images = (self.data_dir / "images").exists() or any(
            (self.data_dir / split / "images").exists() 
            for split in ["train", "valid", "val", "test"]
        )
        has_labels = (self.data_dir / "labels").exists() or any(
            (self.data_dir / split / "labels").exists() 
            for split in ["train", "valid", "val", "test"]
        )
        
        if has_images and has_labels:
            # Check if labels are YOLO format (txt files with numbers)
            label_files = list(self.data_dir.rglob("labels/*.txt"))
            if label_files:
                return DatasetFormat.YOLO
        
        # Check for COCO format (annotations/*.json)
        coco_annotations = list(self.data_dir.rglob("annotations/*.json"))
        if coco_annotations:
            return DatasetFormat.COCO
        
        # Check for VOC format (Annotations/*.xml)
        voc_annotations = list(self.data_dir.rglob("Annotations/*.xml"))
        if voc_annotations:
            return DatasetFormat.VOC
        
        return DatasetFormat.UNKNOWN
    
    def _get_splits(self) -> List[str]:
        """Get available splits in dataset"""
        splits = []
        for split_name in ["train", "valid", "val", "test"]:
            split_dir = self.data_dir / split_name
            if split_dir.exists():
                splits.append(split_name)
        
        # If no splits found, treat as single dataset
        if not splits:
            splits = ["all"]
        
        return splits
    
    def _generate_item_id(self, path: Path) -> str:
        """Generate unique ID for a data item"""
        rel_path = str(path.relative_to(self.data_dir))
        return hashlib.md5(rel_path.encode()).hexdigest()[:12]
    
    def _get_label_path(self, image_path: Path) -> Optional[Path]:
        """Get corresponding label path for an image"""
        if self.format == DatasetFormat.YOLO:
            # YOLO: images/xxx.jpg -> labels/xxx.txt
            label_path = Path(str(image_path).replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt")
            if label_path.exists():
                return label_path
        elif self.format == DatasetFormat.VOC:
            # VOC: JPEGImages/xxx.jpg -> Annotations/xxx.xml
            label_path = Path(str(image_path).replace("/JPEGImages/", "/Annotations/").rsplit(".", 1)[0] + ".xml")
            if label_path.exists():
                return label_path
        return None
    
    def _parse_yolo_label(self, label_path: Path) -> List[str]:
        """Parse YOLO label file to get class indices"""
        classes = []
        try:
            with open(label_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        classes.append(parts[0])
        except Exception:
            pass
        return classes
    
    def _get_class_names(self) -> Dict[int, str]:
        """Get class name mapping from data.yaml"""
        class_names = {}
        
        # Try to find data.yaml
        for yaml_file in self.data_dir.rglob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)
                if data and 'names' in data:
                    names = data['names']
                    if isinstance(names, list):
                        class_names = {i: name for i, name in enumerate(names)}
                    elif isinstance(names, dict):
                        class_names = {int(k): v for k, v in names.items()}
                    break
            except Exception:
                continue
        
        return class_names
    
    # ===========================================
    # Data Exploration
    # ===========================================
    
    def list_items(
        self,
        split: Optional[str] = None,
        class_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[DataItem], int]:
        """
        List data items with optional filtering.
        
        Args:
            split: Filter by split (train, valid, test)
            class_filter: Filter by class name/index
            limit: Maximum items to return
            offset: Offset for pagination
            
        Returns:
            Tuple of (items, total_count)
        """
        items = []
        class_names = self._get_class_names()
        
        # Determine search directories
        if split and split != "all":
            search_dirs = [self.data_dir / split / "images"]
            if not search_dirs[0].exists():
                search_dirs = [self.data_dir / split]
        else:
            search_dirs = []
            for s in self._get_splits():
                if s == "all":
                    search_dirs.append(self.data_dir)
                else:
                    img_dir = self.data_dir / s / "images"
                    if img_dir.exists():
                        search_dirs.append(img_dir)
                    else:
                        search_dirs.append(self.data_dir / s)
        
        # Collect all image files
        all_images = []
        for search_dir in search_dirs:
            if search_dir.exists():
                for img_path in search_dir.rglob("*"):
                    if img_path.is_file() and img_path.suffix.lower() in IMAGE_EXTENSIONS:
                        all_images.append(img_path)
        
        # Sort for consistent pagination
        all_images.sort(key=lambda x: str(x))
        
        # Build items with metadata
        for img_path in all_images:
            label_path = self._get_label_path(img_path)
            classes = []
            if label_path and self.format == DatasetFormat.YOLO:
                classes = self._parse_yolo_label(label_path)
            
            # Apply class filter
            if class_filter:
                if class_filter not in classes:
                    # Try matching by class name
                    class_indices = [str(i) for i, name in class_names.items() if name == class_filter]
                    if not any(ci in classes for ci in class_indices):
                        continue
            
            # Determine split
            item_split = None
            rel_path = str(img_path.relative_to(self.data_dir))
            for s in ["train", "valid", "val", "test"]:
                if rel_path.startswith(s):
                    item_split = s
                    break
            
            # Get image dimensions if PIL available
            width, height = None, None
            if PIL_AVAILABLE:
                try:
                    with Image.open(img_path) as img:
                        width, height = img.size
                except Exception:
                    pass
            
            item = DataItem(
                id=self._generate_item_id(img_path),
                filename=img_path.name,
                path=str(img_path),
                split=item_split,
                label=label_path.name if label_path else None,
                label_path=str(label_path) if label_path else None,
                size_bytes=img_path.stat().st_size,
                width=width,
                height=height,
                classes=[class_names.get(int(c), c) for c in classes] if class_names else classes,
            )
            items.append(item)
        
        total = len(items)
        
        # Apply pagination
        items = items[offset:offset + limit]
        
        return items, total
    
    def get_item_preview(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get preview data for a specific item.
        
        Returns image as base64 and metadata.
        """
        items, _ = self.list_items(limit=10000)  # Get all items
        
        for item in items:
            if item.id == item_id:
                result = {
                    "id": item.id,
                    "filename": item.filename,
                    "path": item.path,
                    "split": item.split,
                    "classes": item.classes,
                    "width": item.width,
                    "height": item.height,
                    "size_bytes": item.size_bytes,
                }
                
                # Read label content if exists
                if item.label_path:
                    try:
                        with open(item.label_path, 'r') as f:
                            result["label_content"] = f.read()
                    except Exception:
                        pass
                
                return result
        
        return None
    
    def get_statistics(self) -> DatasetStats:
        """Get dataset statistics"""
        items, total = self.list_items(limit=100000)
        
        # Count by split
        splits = {}
        for item in items:
            split_name = item.split or "unknown"
            splits[split_name] = splits.get(split_name, 0) + 1
        
        # Count by class
        classes = {}
        for item in items:
            for cls in item.classes:
                classes[cls] = classes.get(cls, 0) + 1
        
        # Calculate total size
        total_bytes = sum(item.size_bytes for item in items)
        
        # Image statistics
        image_stats = None
        if PIL_AVAILABLE and items:
            widths = [item.width for item in items if item.width]
            heights = [item.height for item in items if item.height]
            if widths and heights:
                image_stats = {
                    "avg_width": sum(widths) / len(widths),
                    "avg_height": sum(heights) / len(heights),
                    "min_width": min(widths),
                    "max_width": max(widths),
                    "min_height": min(heights),
                    "max_height": max(heights),
                }
        
        return DatasetStats(
            total_items=total,
            total_size_mb=round(total_bytes / (1024 * 1024), 2),
            format=self.format,
            splits=splits,
            classes=classes,
            image_stats=image_stats,
        )
    
    # ===========================================
    # Data Modification
    # ===========================================
    
    def add_items(self, source_paths: List[str], target_split: str = "train") -> Dict[str, Any]:
        """
        Add items to the dataset.
        
        Args:
            source_paths: List of source file paths to add
            target_split: Target split to add to
            
        Returns:
            Result with count of added items
        """
        added = 0
        errors = []
        
        # Ensure target directory exists
        if self.format == DatasetFormat.YOLO:
            target_images = self.data_dir / target_split / "images"
            target_labels = self.data_dir / target_split / "labels"
        else:
            target_images = self.data_dir / target_split
            target_labels = None
        
        target_images.mkdir(parents=True, exist_ok=True)
        if target_labels:
            target_labels.mkdir(parents=True, exist_ok=True)
        
        for source_path in source_paths:
            source = Path(source_path)
            if not source.exists():
                errors.append(f"Source not found: {source_path}")
                continue
            
            try:
                # Copy image
                dest_image = target_images / source.name
                shutil.copy2(source, dest_image)
                
                # Try to find and copy corresponding label
                if target_labels:
                    label_source = source.parent / (source.stem + ".txt")
                    if label_source.exists():
                        dest_label = target_labels / (source.stem + ".txt")
                        shutil.copy2(label_source, dest_label)
                
                added += 1
            except Exception as e:
                errors.append(f"Failed to add {source_path}: {e}")
        
        return {
            "success": True,
            "added": added,
            "errors": errors,
        }
    
    def remove_items(self, item_ids: List[str]) -> Dict[str, Any]:
        """
        Remove items from the dataset.
        
        Args:
            item_ids: List of item IDs to remove
            
        Returns:
            Result with count of removed items
        """
        removed = 0
        errors = []
        
        items, _ = self.list_items(limit=100000)
        id_to_item = {item.id: item for item in items}
        
        for item_id in item_ids:
            if item_id not in id_to_item:
                errors.append(f"Item not found: {item_id}")
                continue
            
            item = id_to_item[item_id]
            
            try:
                # Remove image
                Path(item.path).unlink()
                
                # Remove label if exists
                if item.label_path:
                    Path(item.label_path).unlink()
                
                removed += 1
            except Exception as e:
                errors.append(f"Failed to remove {item_id}: {e}")
        
        return {
            "success": True,
            "removed": removed,
            "errors": errors,
        }
    
    def move_items(self, item_ids: List[str], target_split: str) -> Dict[str, Any]:
        """
        Move items between splits.
        
        Args:
            item_ids: List of item IDs to move
            target_split: Target split
            
        Returns:
            Result with count of moved items
        """
        moved = 0
        errors = []
        
        items, _ = self.list_items(limit=100000)
        id_to_item = {item.id: item for item in items}
        
        # Ensure target directories exist
        if self.format == DatasetFormat.YOLO:
            target_images = self.data_dir / target_split / "images"
            target_labels = self.data_dir / target_split / "labels"
        else:
            target_images = self.data_dir / target_split
            target_labels = None
        
        target_images.mkdir(parents=True, exist_ok=True)
        if target_labels:
            target_labels.mkdir(parents=True, exist_ok=True)
        
        for item_id in item_ids:
            if item_id not in id_to_item:
                errors.append(f"Item not found: {item_id}")
                continue
            
            item = id_to_item[item_id]
            
            if item.split == target_split:
                continue  # Already in target split
            
            try:
                # Move image
                source_image = Path(item.path)
                dest_image = target_images / source_image.name
                shutil.move(str(source_image), str(dest_image))
                
                # Move label if exists
                if item.label_path and target_labels:
                    source_label = Path(item.label_path)
                    dest_label = target_labels / source_label.name
                    shutil.move(str(source_label), str(dest_label))
                
                moved += 1
            except Exception as e:
                errors.append(f"Failed to move {item_id}: {e}")
        
        return {
            "success": True,
            "moved": moved,
            "errors": errors,
        }
    
    def relabel_items(self, item_ids: List[str], new_label: str) -> Dict[str, Any]:
        """
        Change label for items (for YOLO format, changes class index).
        
        Args:
            item_ids: List of item IDs to relabel
            new_label: New class index/name
            
        Returns:
            Result with count of relabeled items
        """
        if self.format != DatasetFormat.YOLO:
            return {
                "success": False,
                "error": "Relabeling only supported for YOLO format",
            }
        
        relabeled = 0
        errors = []
        
        items, _ = self.list_items(limit=100000)
        id_to_item = {item.id: item for item in items}
        
        # Get class index for new label
        class_names = self._get_class_names()
        if new_label.isdigit():
            new_class_idx = new_label
        else:
            # Find class index by name
            new_class_idx = None
            for idx, name in class_names.items():
                if name == new_label:
                    new_class_idx = str(idx)
                    break
            if new_class_idx is None:
                return {
                    "success": False,
                    "error": f"Unknown class: {new_label}",
                }
        
        for item_id in item_ids:
            if item_id not in id_to_item:
                errors.append(f"Item not found: {item_id}")
                continue
            
            item = id_to_item[item_id]
            
            if not item.label_path:
                errors.append(f"No label file for {item_id}")
                continue
            
            try:
                # Read and modify label file
                label_path = Path(item.label_path)
                lines = []
                with open(label_path, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            parts[0] = new_class_idx
                            lines.append(" ".join(parts))
                
                # Write back
                with open(label_path, 'w') as f:
                    f.write("\n".join(lines))
                
                relabeled += 1
            except Exception as e:
                errors.append(f"Failed to relabel {item_id}: {e}")
        
        return {
            "success": True,
            "relabeled": relabeled,
            "errors": errors,
        }
    
    # ===========================================
    # Sampling Strategies
    # ===========================================
    
    def create_sample(
        self,
        strategy: SamplingStrategy,
        params: Dict[str, Any],
        output_name: str,
    ) -> Dict[str, Any]:
        """
        Create a sampled dataset.
        
        Args:
            strategy: Sampling strategy to use
            params: Strategy-specific parameters
            output_name: Name for the sampled dataset
            
        Returns:
            Result with sample path and count
        """
        items, total = self.list_items(limit=100000)
        
        if strategy == SamplingStrategy.RANDOM:
            sampled = self._sample_random(items, params)
        elif strategy == SamplingStrategy.STRATIFIED:
            sampled = self._sample_stratified(items, params)
        elif strategy == SamplingStrategy.THRESHOLD:
            sampled = self._sample_threshold(items, params)
        else:
            return {"success": False, "error": f"Unknown strategy: {strategy}"}
        
        # Create sample directory
        sample_dir = self.workspace_path / "samples" / output_name
        sample_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy sampled items
        copied = 0
        if self.format == DatasetFormat.YOLO:
            (sample_dir / "images").mkdir(exist_ok=True)
            (sample_dir / "labels").mkdir(exist_ok=True)
        
        for item in sampled:
            try:
                source_image = Path(item.path)
                if self.format == DatasetFormat.YOLO:
                    dest_image = sample_dir / "images" / source_image.name
                else:
                    dest_image = sample_dir / source_image.name
                
                shutil.copy2(source_image, dest_image)
                
                if item.label_path:
                    source_label = Path(item.label_path)
                    if self.format == DatasetFormat.YOLO:
                        dest_label = sample_dir / "labels" / source_label.name
                    else:
                        dest_label = sample_dir / source_label.name
                    shutil.copy2(source_label, dest_label)
                
                copied += 1
            except Exception:
                continue
        
        # Copy data.yaml if exists
        for yaml_file in self.data_dir.rglob("data.yaml"):
            shutil.copy2(yaml_file, sample_dir / "data.yaml")
            break
        
        return {
            "success": True,
            "sample_path": str(sample_dir),
            "item_count": copied,
            "strategy": strategy.value,
            "params": params,
        }
    
    def _sample_random(self, items: List[DataItem], params: Dict[str, Any]) -> List[DataItem]:
        """Random sampling"""
        n = params.get("n", 100)
        seed = params.get("seed", None)
        
        if seed is not None:
            random.seed(seed)
        
        if n >= len(items):
            return items
        
        return random.sample(items, n)
    
    def _sample_stratified(self, items: List[DataItem], params: Dict[str, Any]) -> List[DataItem]:
        """Stratified sampling - maintains class distribution"""
        n = params.get("n", 100)
        seed = params.get("seed", None)
        
        if seed is not None:
            random.seed(seed)
        
        # Group by primary class
        class_groups = {}
        for item in items:
            primary_class = item.classes[0] if item.classes else "unknown"
            if primary_class not in class_groups:
                class_groups[primary_class] = []
            class_groups[primary_class].append(item)
        
        # Calculate samples per class
        total_items = len(items)
        sampled = []
        
        for cls, class_items in class_groups.items():
            class_ratio = len(class_items) / total_items
            class_n = max(1, int(n * class_ratio))
            
            if class_n >= len(class_items):
                sampled.extend(class_items)
            else:
                sampled.extend(random.sample(class_items, class_n))
        
        return sampled
    
    def _sample_threshold(self, items: List[DataItem], params: Dict[str, Any]) -> List[DataItem]:
        """Threshold-based sampling (e.g., by drift score)"""
        # This would integrate with drift analysis results
        # For now, implement basic size-based threshold
        min_size = params.get("min_size", 0)
        max_size = params.get("max_size", float('inf'))
        
        return [
            item for item in items
            if min_size <= item.size_bytes <= max_size
        ]
    
    # ===========================================
    # Export
    # ===========================================
    
    def export_dataset(
        self,
        format: str,
        output_path: Optional[str] = None,
        include_splits: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Export dataset to specified format.
        
        Args:
            format: Export format (yolo, coco, voc)
            output_path: Output directory path
            include_splits: List of splits to include
            
        Returns:
            Result with export path and count
        """
        if output_path:
            export_dir = Path(output_path)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_dir = self.workspace_path / "exports" / f"{format}_{timestamp}"
        
        export_dir.mkdir(parents=True, exist_ok=True)
        
        items, total = self.list_items(limit=100000)
        
        # Filter by splits if specified
        if include_splits:
            items = [item for item in items if item.split in include_splits]
        
        if format == "yolo":
            return self._export_yolo(items, export_dir)
        elif format == "coco":
            return self._export_coco(items, export_dir)
        elif format == "voc":
            return self._export_voc(items, export_dir)
        else:
            return {"success": False, "error": f"Unknown format: {format}"}
    
    def _export_yolo(self, items: List[DataItem], export_dir: Path) -> Dict[str, Any]:
        """Export to YOLO format"""
        # Group by split
        splits = {}
        for item in items:
            split = item.split or "train"
            if split not in splits:
                splits[split] = []
            splits[split].append(item)
        
        exported = 0
        for split, split_items in splits.items():
            images_dir = export_dir / split / "images"
            labels_dir = export_dir / split / "labels"
            images_dir.mkdir(parents=True, exist_ok=True)
            labels_dir.mkdir(parents=True, exist_ok=True)
            
            for item in split_items:
                try:
                    shutil.copy2(item.path, images_dir / Path(item.path).name)
                    if item.label_path:
                        shutil.copy2(item.label_path, labels_dir / Path(item.label_path).name)
                    exported += 1
                except Exception:
                    continue
        
        # Copy data.yaml
        for yaml_file in self.data_dir.rglob("data.yaml"):
            shutil.copy2(yaml_file, export_dir / "data.yaml")
            break
        
        total_size = sum(
            f.stat().st_size for f in export_dir.rglob("*") if f.is_file()
        )
        
        return {
            "success": True,
            "format": "yolo",
            "output_path": str(export_dir),
            "item_count": exported,
            "size_mb": round(total_size / (1024 * 1024), 2),
        }
    
    def _export_coco(self, items: List[DataItem], export_dir: Path) -> Dict[str, Any]:
        """Export to COCO format"""
        images_dir = export_dir / "images"
        annotations_dir = export_dir / "annotations"
        images_dir.mkdir(parents=True, exist_ok=True)
        annotations_dir.mkdir(parents=True, exist_ok=True)
        
        class_names = self._get_class_names()
        
        # Build COCO annotation structure
        coco_data = {
            "images": [],
            "annotations": [],
            "categories": [
                {"id": idx, "name": name}
                for idx, name in class_names.items()
            ] if class_names else [],
        }
        
        annotation_id = 1
        exported = 0
        
        for idx, item in enumerate(items):
            try:
                # Copy image
                dest_image = images_dir / Path(item.path).name
                shutil.copy2(item.path, dest_image)
                
                # Add image entry
                coco_data["images"].append({
                    "id": idx + 1,
                    "file_name": Path(item.path).name,
                    "width": item.width or 0,
                    "height": item.height or 0,
                })
                
                # Convert YOLO labels to COCO if exists
                if item.label_path and self.format == DatasetFormat.YOLO:
                    with open(item.label_path, 'r') as f:
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 5:
                                cls_id = int(parts[0])
                                x_center = float(parts[1])
                                y_center = float(parts[2])
                                width = float(parts[3])
                                height = float(parts[4])
                                
                                # Convert to COCO format (x, y, w, h in pixels)
                                if item.width and item.height:
                                    x = (x_center - width/2) * item.width
                                    y = (y_center - height/2) * item.height
                                    w = width * item.width
                                    h = height * item.height
                                    
                                    coco_data["annotations"].append({
                                        "id": annotation_id,
                                        "image_id": idx + 1,
                                        "category_id": cls_id,
                                        "bbox": [x, y, w, h],
                                        "area": w * h,
                                        "iscrowd": 0,
                                    })
                                    annotation_id += 1
                
                exported += 1
            except Exception:
                continue
        
        # Save annotations JSON
        with open(annotations_dir / "instances.json", 'w') as f:
            json.dump(coco_data, f, indent=2)
        
        total_size = sum(
            f.stat().st_size for f in export_dir.rglob("*") if f.is_file()
        )
        
        return {
            "success": True,
            "format": "coco",
            "output_path": str(export_dir),
            "item_count": exported,
            "size_mb": round(total_size / (1024 * 1024), 2),
        }
    
    def _export_voc(self, items: List[DataItem], export_dir: Path) -> Dict[str, Any]:
        """Export to Pascal VOC format"""
        images_dir = export_dir / "JPEGImages"
        annotations_dir = export_dir / "Annotations"
        images_dir.mkdir(parents=True, exist_ok=True)
        annotations_dir.mkdir(parents=True, exist_ok=True)
        
        class_names = self._get_class_names()
        exported = 0
        
        for item in items:
            try:
                # Copy image
                dest_image = images_dir / Path(item.path).name
                shutil.copy2(item.path, dest_image)
                
                # Convert YOLO labels to VOC XML if exists
                if item.label_path and self.format == DatasetFormat.YOLO:
                    xml_content = self._yolo_to_voc_xml(
                        item, class_names
                    )
                    xml_path = annotations_dir / (Path(item.path).stem + ".xml")
                    with open(xml_path, 'w') as f:
                        f.write(xml_content)
                
                exported += 1
            except Exception:
                continue
        
        total_size = sum(
            f.stat().st_size for f in export_dir.rglob("*") if f.is_file()
        )
        
        return {
            "success": True,
            "format": "voc",
            "output_path": str(export_dir),
            "item_count": exported,
            "size_mb": round(total_size / (1024 * 1024), 2),
        }
    
    def _yolo_to_voc_xml(self, item: DataItem, class_names: Dict[int, str]) -> str:
        """Convert YOLO annotation to VOC XML format"""
        objects_xml = ""
        
        if item.label_path:
            with open(item.label_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5 and item.width and item.height:
                        cls_id = int(parts[0])
                        x_center = float(parts[1])
                        y_center = float(parts[2])
                        width = float(parts[3])
                        height = float(parts[4])
                        
                        # Convert to VOC format
                        xmin = int((x_center - width/2) * item.width)
                        ymin = int((y_center - height/2) * item.height)
                        xmax = int((x_center + width/2) * item.width)
                        ymax = int((y_center + height/2) * item.height)
                        
                        cls_name = class_names.get(cls_id, str(cls_id))
                        
                        objects_xml += f"""
    <object>
        <name>{cls_name}</name>
        <pose>Unspecified</pose>
        <truncated>0</truncated>
        <difficult>0</difficult>
        <bndbox>
            <xmin>{xmin}</xmin>
            <ymin>{ymin}</ymin>
            <xmax>{xmax}</xmax>
            <ymax>{ymax}</ymax>
        </bndbox>
    </object>"""
        
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<annotation>
    <folder>JPEGImages</folder>
    <filename>{Path(item.path).name}</filename>
    <size>
        <width>{item.width or 0}</width>
        <height>{item.height or 0}</height>
        <depth>3</depth>
    </size>
    <segmented>0</segmented>{objects_xml}
</annotation>"""
    
    def get_supported_export_formats(self) -> List[Dict[str, str]]:
        """Get list of supported export formats"""
        return [
            {"id": "yolo", "name": "YOLO", "description": "Ultralytics YOLO format (images/ + labels/)"},
            {"id": "coco", "name": "COCO", "description": "COCO JSON format (images/ + annotations/)"},
            {"id": "voc", "name": "Pascal VOC", "description": "Pascal VOC XML format (JPEGImages/ + Annotations/)"},
        ]
