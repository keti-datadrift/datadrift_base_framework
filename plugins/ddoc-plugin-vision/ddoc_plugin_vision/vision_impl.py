"""
Vision Analysis Plugin Implementation for ddoc

Provides hookimpl for:
- eda_run: Image attribute analysis, embedding extraction, clustering
- drift_detect: Drift detection between baseline and current datasets
"""
import os
from pathlib import Path
from datetime import datetime
import json
import yaml
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Any, Optional

try:
    from ddoc.plugins.hookspecs import hookimpl
except ImportError:
    # Fallback for development/testing
    def hookimpl(func):
        return func

# Import vision modules
from .data_utils import AttributeAnalyzer, EmbeddingAnalyzer
from .cache_utils import (
    get_cache_manager,
    get_latest_cached_content_by_prefix,
    import_repository_cache_to_local,
    export_local_cache_to_repository,
    get_cached_analysis_data,
    save_analysis_data,
    save_analysis_data_by_version,
)


class DDOCVisionPlugin:
    """Vision Analysis Plugin for ddoc"""
    
    def __init__(self):
        self.attr_analyzer = None
        self.emb_analyzer = None
    
    def _get_dataset_name_from_path(self, dataset_path: str) -> str:
        """
        Get dataset name from path by querying metadata service.
        Falls back to basename if mapping not found.
        
        Args:
            dataset_path: Path to dataset directory
            
        Returns:
            Dataset name
        """
        try:
            from ddoc.core.metadata_service import get_metadata_service
            metadata_service = get_metadata_service()
            
            mappings = metadata_service.get_all_dataset_mappings()
            dataset_path_normalized = str(Path(dataset_path).resolve())
            
            for name, info in mappings.get('datasets', {}).items():
                mapped_path = str(Path(info['dataset_path']).resolve())
                if mapped_path == dataset_path_normalized:
                    return name
            
            # Fallback to basename for backward compatibility
            return os.path.basename(dataset_path)
            
        except Exception as e:
            # If metadata service unavailable, use basename
            print(f"⚠️ Could not query metadata service: {e}")
            return os.path.basename(dataset_path)
    
    def _compute_embeddings_from_path(self, data_path) -> Dict[str, Any]:
        """Round-12 — companion to ``_compute_attributes_from_path``.

        Walks ``data_path`` for images and runs the CLIP embedding
        analyzer on each. Only invoked in path mode when the caller
        passes ``cfg['with_embeddings']`` (i.e. the user opted in via
        ``--with-embeddings``) AND no embedding cache is available;
        otherwise the plugin's drift falls back to attribute-only
        (Round-7 contract).

        Mirrors text plugin's path-mode embedding helper (Round-10).
        Returns the same shape that the cache would
        (``{rel_path: {embedding: [...], file_size?: n, file_mtime?: n}}``)
        so ``drift_detect`` doesn't have to branch on source.
        """
        input_path = Path(data_path)
        if not input_path.exists() or not input_path.is_dir():
            return {}

        formats = ('.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG')
        image_files = self._get_current_image_files(input_path, formats)
        if not image_files:
            return {}

        if self.emb_analyzer is None:
            self.emb_analyzer = EmbeddingAnalyzer(device='cpu')
            try:
                self.emb_analyzer.load_model("ViT-B/16")
            except Exception as e:
                print(f"⚠️ CLIP load failed in path mode: {e}")
                return {}

        out: Dict[str, Any] = {}
        for img_file in image_files:
            try:
                result = self.emb_analyzer.extract_embedding(str(img_file))
            except Exception as e:
                print(f"⚠️ embedding extract failed for {img_file.name}: {e}")
                continue
            if result and 'embedding' in result:
                rel_path = str(img_file.relative_to(input_path))
                out[rel_path] = {
                    'embedding': result['embedding'],
                    'file_size': img_file.stat().st_size,
                    'file_mtime': int(img_file.stat().st_mtime),
                }
        return out

    def _compute_attributes_from_path(self, data_path) -> Dict[str, Any]:
        """Walk ``data_path`` for image files and run the attribute
        analyzer on each. Round-7 — minimal helper for ``drift_detect``
        path-mode fallback. Skips embeddings (CLIP load), incremental
        cache deltas, and file-metadata bookkeeping — those belong to
        the snapshot/cache flow, not the orchestrator path-mode flow.
        """
        input_path = Path(data_path)
        if not input_path.exists() or not input_path.is_dir():
            return {}

        formats = ('.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG')
        image_files = self._get_current_image_files(input_path, formats)
        if not image_files:
            return {}

        if self.attr_analyzer is None:
            self.attr_analyzer = AttributeAnalyzer()

        out: Dict[str, Any] = {}
        for img_file in image_files:
            attrs = self.attr_analyzer.analyze_image_attributes(str(img_file))
            if attrs:
                rel_path = str(img_file.relative_to(input_path))
                out[rel_path] = attrs
        return out

    @hookimpl
    def eda_run(self, snapshot_id, data_path, data_hash, output_path, invalidate_cache=False):
        """
        Run EDA (Exploratory Data Analysis) for image datasets.
        
        Args:
            snapshot_id: Snapshot ID (or "workspace" for current workspace)
            data_path: Path to data directory
            data_hash: DVC hash of the data
            output_path: Path to save analysis results
            invalidate_cache: Whether to invalidate existing cache
        
        Returns:
            Dict with analysis summary
        """
        from ddoc.core.cache_service import get_cache_service
        from ddoc.core.schemas import FileMetadata
        
        cache_service = get_cache_service()
        input_path = Path(data_path)
        output_path = Path(output_path)
        
        print(f"🚀 Vision EDA Analysis Started")
        print(f"=" * 80)
        print(f"Snapshot: {snapshot_id}")
        print(f"Data Hash: {data_hash[:8] if data_hash != 'unknown' else 'unknown'}")
        print(f"Input: {input_path}")
        print(f"Output: {output_path}")
        print()
        
        # Create output directories
        plot_dir = output_path / "plots"
        plot_csv_dir = plot_dir / "csv"
        plot_images_dir = plot_dir / "images"
        plot_csv_dir.mkdir(parents=True, exist_ok=True)
        plot_images_dir.mkdir(parents=True, exist_ok=True)
        
        # Supported image formats
        formats = ('.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG')
        
        # Initialize analyzers
        if self.attr_analyzer is None:
            self.attr_analyzer = AttributeAnalyzer()
        if self.emb_analyzer is None:
            self.emb_analyzer = EmbeddingAnalyzer(device='cpu')
            self.emb_analyzer.load_model("ViT-B/16")
        
        # Metrics dictionary
        metrics = {}
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        metrics['timestamp'] = timestamp
        metrics['snapshot_id'] = snapshot_id
        metrics['data_hash'] = data_hash
        
        print(f"📋 Snapshot: {snapshot_id}")

        # Load cache from CacheService
        attr_cache = {}
        emb_cache = {}
        file_metadata = {}
        
        if not invalidate_cache:
            # Try to load existing cache (use namespaced cache type)
            attr_cache_data = cache_service.load_analysis_cache(
                snapshot_id=snapshot_id,
                data_hash=data_hash,
                cache_type="attributes_image"
            )
            if attr_cache_data:
                attr_cache = attr_cache_data
                print(f"✅ Loaded cached attribute analysis ({len(attr_cache)} files)")
            
            emb_cache_data = cache_service.load_analysis_cache(
                snapshot_id=snapshot_id,
                data_hash=data_hash,
                cache_type="embedding_image"
            )
            if emb_cache_data:
                emb_cache = emb_cache_data
                print(f"✅ Loaded cached embedding analysis ({len(emb_cache)} files)")
            
            file_metadata = cache_service.load_file_metadata(
                snapshot_id=snapshot_id,
                data_hash=data_hash
            ) or {}
        
        # === Step 1: Attribute Analysis ===
        print("📊 Step 1: Attribute Analysis")
        print("-" * 80)
        
        # Get current files
        image_files = self._get_current_image_files(input_path, formats)
        
        # Compute incremental changes using file metadata
        # Use relative path as key to handle multiple datasets and nested structures
        current_file_info = {}
        for img_file in image_files:
            st = img_file.stat()
            # Use relative path as key (e.g., "yolo_reference/train/images/image.jpg")
            rel_path = str(img_file.relative_to(input_path))
            current_file_info[rel_path] = {
                "size": st.st_size,
                "mtime": st.st_mtime
            }
        
        changes = cache_service.compute_incremental_changes(
            snapshot_id=snapshot_id,
            current_files=current_file_info
        )
        
        new_files = set(changes.get("new_files", []))
        modified_files = set(changes.get("modified_files", []))
        removed_files = set(changes.get("removed_files", []))
        unchanged_files = set(changes.get("unchanged_files", []))
        
        print(f"Changed summary → new: {len(new_files)}, modified: {len(modified_files)}, removed: {len(removed_files)}, skipped(cached): {len(unchanged_files)}")
        
        # Remove deleted files from cache
        if removed_files:
            print(f"🗑️ Detected removed files: {len(removed_files)}")
            for rel_path in removed_files:
                attr_cache.pop(rel_path, None)
                if rel_path in file_metadata:
                    del file_metadata[rel_path]

        # Process new or modified files only
        if new_files or modified_files:
            print(f"➕ Processing changed files (new: {len(new_files)}, modified: {len(modified_files)})")
        
        for img_file in image_files:
            rel_path = str(img_file.relative_to(input_path))
            if rel_path in new_files or rel_path in modified_files:
                attrs = self.attr_analyzer.analyze_image_attributes(str(img_file))
                if attrs:
                    st = img_file.stat()
                    attrs['file_mtime'] = int(st.st_mtime)
                    attr_cache[rel_path] = attrs

                    # Update file metadata
                    import hashlib
                    file_hash = hashlib.md5(open(img_file, 'rb').read()).hexdigest()
                    file_metadata[rel_path] = FileMetadata(
                        file_path=rel_path,
                        file_hash=file_hash,
                        file_size=st.st_size,
                        file_mtime=st.st_mtime,
                        analyzed_at=datetime.now().isoformat()
                    )

        # Save cache if changed
        if new_files or removed_files or modified_files or not attr_cache:
            print(f"💾 Saving attribute analysis to cache")
            cache_service.save_analysis_cache(
                snapshot_id=snapshot_id,
                data_hash=data_hash,
                cache_type="attributes_image",
                data=attr_cache
            )
            cache_service.save_file_metadata(
                snapshot_id=snapshot_id,
                data_hash=data_hash,
                file_metadata=file_metadata
            )
            print(f"💾 Saved attribute analysis to cache: {len(attr_cache)} files")
        
        if attr_cache:
            num_files = len(attr_cache)
            sizes = [v['size'] for v in attr_cache.values() if 'size' in v]
            widths = [v['width'] for v in attr_cache.values() if 'width' in v]
            heights = [v['height'] for v in attr_cache.values() if 'height' in v]
            noise_levels = [v['noise_level'] for v in attr_cache.values() if 'noise_level' in v]
            sharpness_vals = [v['sharpness'] for v in attr_cache.values() if 'sharpness' in v]
            
            metrics['num_files'] = num_files
            metrics['avg_size_mb'] = sum(sizes) / len(sizes) if sizes else 0
            metrics['avg_width'] = sum(widths) / len(widths) if widths else 0
            metrics['avg_height'] = sum(heights) / len(heights) if heights else 0
            
            print(f"✅ Analyzed {num_files} files")
            
            # Quality score calculation
            def calculate_quality_score(sharpness, noise_level):
                sharp_norm = min(sharpness / 100, 1.0)
                noise_norm = max(0, 1.0 - (noise_level / 50))
                return (sharp_norm * 0.6 + noise_norm * 0.4) * 100
            
            quality_scores = []
            if noise_levels and sharpness_vals and len(noise_levels) == len(sharpness_vals):
                quality_scores = [calculate_quality_score(s, n) for s, n in zip(sharpness_vals, noise_levels)]
                metrics['avg_quality_score'] = sum(quality_scores) / len(quality_scores)
                metrics['avg_noise_level'] = sum(noise_levels) / len(noise_levels)
                metrics['avg_sharpness'] = sum(sharpness_vals) / len(sharpness_vals)
            
            # Save CSV plots for DVC
            self._save_attribute_plots_csv(
                plot_csv_dir, sizes, noise_levels, sharpness_vals, quality_scores
            )
        
        # === Step 2: Embedding Extraction ===
        print("\n🧠 Step 2: Embedding Extraction")
        print("-" * 80)
        
        # Use same incremental changes from attribute analysis
        # Remove deleted files from embedding cache
        if removed_files:
            for rel_path in removed_files:
                emb_cache.pop(rel_path, None)
        
        # Extract embeddings for new or modified files only
        skipped_files = unchanged_files & set(emb_cache.keys())
        
        def _sample(names, k=5):
            try:
                import itertools
                return ', '.join(list(itertools.islice(sorted(names), k)))
            except Exception:
                return ''
        
        print(f"Changed summary → new: {len(new_files)}, modified: {len(modified_files)}, removed: {len(removed_files)}, skipped(cached): {len(skipped_files)}")
        if new_files:
            print(f"   new: {_sample(new_files)}{' ...' if len(new_files) > 5 else ''}")
        if modified_files:
            print(f"   modified: {_sample(modified_files)}{' ...' if len(modified_files) > 5 else ''}")
        if removed_files:
            print(f"   removed: {_sample(removed_files)}{' ...' if len(removed_files) > 5 else ''}")
        
        if new_files or modified_files:
            print(f"➕ Processing new/modified files: {len(new_files) + len(modified_files)}")
        
        # Extract embeddings for new or modified files only
        for img_file in image_files:
            rel_path = str(img_file.relative_to(input_path))
            
            # Only process new or modified files
            if rel_path in new_files or rel_path in modified_files:
                try:
                    result = self.emb_analyzer.extract_embedding(str(img_file))
                    if result and 'embedding' in result:
                        st = img_file.stat()
                        result['file_size'] = st.st_size
                        result['file_mtime'] = int(st.st_mtime)
                        emb_cache[rel_path] = result
                        print(f"  Processed {rel_path}")
                except Exception as e:
                    print(f"  ⚠️ Error processing {rel_path}: {e}")
        
        # Save embeddings to cache (only if there were changes)
        if new_files or removed_files or modified_files:
            print(f"💾 Saving embedding analysis to cache")
            cache_service.save_analysis_cache(
                snapshot_id=snapshot_id,
                data_hash=data_hash,
                cache_type="embedding_image",
                data=emb_cache,
                metadata={
                    "created_at": datetime.now().isoformat(),
                    "file_count": len(emb_cache)
                }
            )
            print(f"💾 Updated embedding cache: {len(emb_cache)} files")
        else:
            print(f"✅ Using validated cached embeddings ({len(emb_cache)} files)")
        
        if emb_cache:
            print(f"✅ Extracted embeddings for {len(emb_cache)} files")
            metrics['embeddings_extracted'] = len(emb_cache)
            
            # Perform clustering
            print("\n🔬 Step 3: Clustering Analysis")
            print("-" * 80)
            
            embeddings_list = [v['embedding'] for v in emb_cache.values()]
            file_names = list(emb_cache.keys())  # These are now relative paths
            file_paths = [str(input_path / rel_path) for rel_path in file_names]
            
            embeddings_data = {
                'embeddings': np.array(embeddings_list),
                'file_names': file_names,
                'file_paths': file_paths
            }
            
            # Clustering
            clustering_result = self.emb_analyzer.perform_clustering(
                embeddings_data['embeddings'],
                embeddings_data['file_names'],
                embeddings_data['file_paths'],
                method='kmeans',
                n_clusters=None  # Auto-determine
            )
            
            print(f"✅ Clustering complete: {clustering_result['n_clusters']} clusters")
            metrics['n_clusters'] = clustering_result['n_clusters']
            
            # Save clustering CSV
            # Extract the nested clustering_results for plotting
            inner_clustering_results = clustering_result.get('clustering_results', {})
            self._save_clustering_plots_csv(
                plot_csv_dir, plot_images_dir, inner_clustering_results, embeddings_data
            )
        
        # Save metrics
        metrics_file = output_path / "metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)

        # Save metrics as summary cache for drift analysis
        print(f"💾 Saving summary cache for drift analysis")
        cache_service.save_analysis_cache(
            snapshot_id=snapshot_id,
            data_hash=data_hash,
            cache_type="summary",
            data=metrics
        )
        
        print(f"\n✅ Analysis Complete")
        print(f"   📄 Metrics: {metrics_file}")
        print(f"   📊 Plots: {plot_csv_dir} & {plot_images_dir}")
        
        return {
            "status": "success",
            "modality": "image",
            "files_analyzed": metrics.get('num_files', 0),
            "metrics_file": str(metrics_file),
            "output_path": str(output_path),
            "summary": metrics
        }
    
    @hookimpl
    def drift_detect(
        self, 
        snapshot_id_ref: str,
        snapshot_id_cur: str,
        data_path_ref: str,
        data_path_cur: str,
        data_hash_ref: str,
        data_hash_cur: str,
        detector: str, 
        cfg: Dict[str, Any],
        output_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        Detect drift between two snapshots.
        
        Args:
            snapshot_id_ref: Reference snapshot ID
            snapshot_id_cur: Current snapshot ID
            data_path_ref: Reference snapshot data path
            data_path_cur: Current snapshot data path
            data_hash_ref: Reference snapshot data hash
            data_hash_cur: Current snapshot data hash
            detector: Drift detector method (e.g., "mmd")
            cfg: Configuration dictionary
            output_path: Path to save drift analysis results
        
        Returns:
            Dict with drift metrics
        """
        from ddoc.core.cache_service import get_cache_service
        
        cache_service = get_cache_service()
        output_path = Path(output_path)
        
        print(f"🔍 Drift Detection Started")
        print(f"=" * 80)
        print(f"Baseline: {snapshot_id_ref} ({data_hash_ref[:8]})")
        print(f"Current:  {snapshot_id_cur} ({data_hash_cur[:8]})")
        print(f"Output: {output_path}")
        print()
        
        output_path.mkdir(parents=True, exist_ok=True)
        plot_dir = output_path / "plots" / "images"
        plot_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration defaults
        threshold_warning = cfg.get('threshold_warning', 0.15)
        threshold_critical = cfg.get('threshold_critical', 0.25)
        
        # Load caches from CacheService (use namespaced cache types)
        baseline_attr = cfg.get('baseline_cache') or cache_service.load_analysis_cache(
            snapshot_id=snapshot_id_ref,
            data_hash=data_hash_ref,
            cache_type="attributes_image"
        )
        baseline_emb = cache_service.load_analysis_cache(
            snapshot_id=snapshot_id_ref,
            data_hash=data_hash_ref,
            cache_type="embedding_image"
        )
        
        current_attr = cfg.get('current_cache') or cache_service.load_analysis_cache(
            snapshot_id=snapshot_id_cur,
            data_hash=data_hash_cur,
            cache_type="attributes_image"
        )
        current_emb = cache_service.load_analysis_cache(
            snapshot_id=snapshot_id_cur,
            data_hash=data_hash_cur,
            cache_type="embedding_image"
        )
        
        # Fallback to old cache system if new cache not found
        ref_dataset_path = Path(data_path_ref)
        cur_dataset_path = Path(data_path_cur)
        
        if not baseline_attr:
            baseline_attr = get_cached_analysis_data(ref_dataset_path, "attribute_analysis")
        if not baseline_emb:
            baseline_emb = get_cached_analysis_data(ref_dataset_path, "embedding_analysis")

        if not current_attr:
            current_attr = get_cached_analysis_data(cur_dataset_path, "attribute_analysis")
        if not current_emb:
            current_emb = get_cached_analysis_data(cur_dataset_path, "embedding_analysis")

        # Round-7 path-mode fallback — when no cache (new ddoc cache,
        # legacy cache, or at all) is available but the orchestrator
        # passed concrete data paths, compute attributes inline. Drift
        # then runs on the freshly-computed attribute snapshot. This is
        # what makes ``ddoc analyze drift --data-path-ref X
        # --data-path-cur Y`` work without project / snapshot context.
        # Embeddings stay None — drift's overall_score then weights
        # them as 0 and returns attribute-only drift.
        if not baseline_attr and data_path_ref:
            baseline_attr = self._compute_attributes_from_path(data_path_ref)
        if not current_attr and data_path_cur:
            current_attr = self._compute_attributes_from_path(data_path_cur)

        # Round-12 (Track B Gap follow-up) — vision ``--with-embeddings``.
        # Symmetric with the text plugin's Round-10 contract: when path
        # mode has no embedding cache AND the user opted in, load CLIP
        # inline and compute embeddings. Without the flag we keep
        # attribute-only drift (path-mode default) so the embedding-
        # heavy CLIP load (~5 s, ~600 MB RAM) stays explicit.
        _with_embeddings = bool(cfg.get('with_embeddings', False))
        if _with_embeddings and not baseline_emb and data_path_ref:
            baseline_emb = self._compute_embeddings_from_path(data_path_ref)
        if _with_embeddings and not current_emb and data_path_cur:
            current_emb = self._compute_embeddings_from_path(data_path_cur)

        # If no baseline, set current as baseline (only for same snapshot comparison)
        if not baseline_attr and current_attr and snapshot_id_ref == snapshot_id_cur:
            print("⚠️ No baseline found. Setting current as baseline.")
            # Save to cache service (use namespaced cache types)
            cache_service.save_analysis_cache(
                snapshot_id=snapshot_id_cur,
                data_hash=data_hash_cur,
                cache_type="attributes_image",
                data=current_attr
            )
            if current_emb:
                cache_service.save_analysis_cache(
                    snapshot_id=snapshot_id_cur,
                    data_hash=data_hash_cur,
                    cache_type="embedding_image",
                    data=current_emb
                )
            
            # Create baseline metrics
            metrics = {
                'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'status': 'BASELINE_CREATED',
                'num_files': len(current_attr)
            }
            
            metrics_file = output_path / 'metrics.json'
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
            
            # Create timeline
            timeline_file = output_path / "timeline.tsv"
            with open(timeline_file, 'w') as f:
                f.write("timestamp\toverall_score\tstatus\tfiles_added\tfiles_removed\n")
                f.write(f"{metrics['timestamp']}\t0.00\tBASELINE\t0\t0\n")
            
            # Create placeholder plots
            self._create_placeholder_plots(plot_dir)
            
            print("✅ Baseline created")
            return {
                "status": "BASELINE_CREATED",
                "modality": "image",
                "metrics_file": str(metrics_file)
            }
        
        # Drift analysis
        if not baseline_attr or not current_attr:
            print("❌ Missing baseline or current data")
            return None  # no image data — silently defer to other plugins

        # Round-11 (Track B) — detector validation at the top of the
        # work-doing path so unsupported values are rejected even when
        # embeddings aren't computed (e.g. path mode without CLIP).
        # The full per-strategy mapping for embedding_drift happens
        # later inside the ``if baseline_emb and current_emb:`` block.
        _SUPPORTED_DETECTORS = {
            "default", "ensemble", "mmd", "mean_shift",
            "wasserstein", "psi", "cosine",
        }
        _strategy = (detector or "default").lower()
        if _strategy not in _SUPPORTED_DETECTORS:
            return {
                "status": "error",
                "error_code": "unsupported_detector",
                "modality": "image",
                "message": (
                    f"vision plugin supports detector ∈ "
                    f"{sorted(_SUPPORTED_DETECTORS)}; got {detector!r}."
                ),
            }

        # File changes
        ref_files = set(baseline_attr.keys())
        cur_files = set(current_attr.keys())
        added = cur_files - ref_files
        removed = ref_files - cur_files
        common = ref_files & cur_files
        
        print(f"📊 File changes:")
        print(f"   Added: {len(added)}")
        print(f"   Removed: {len(removed)}")
        print(f"   Common: {len(common)}")
        print()
        
        drift_metrics = {
            'files_added': len(added),
            'files_removed': len(removed),
            'files_common': len(common)
        }
        
        # Attribute drift (compare distributions of all 9 metrics)
        print("📈 Attribute Drift (9 metrics):")
        print("-" * 80)
        
        # Helper function to extract metric values
        def extract_metric(attr_dict, metric_name, fallback_name=None):
            """Extract metric values from attribute cache"""
            values = []
            for f in attr_dict:
                if metric_name in attr_dict[f]:
                    values.append(attr_dict[f][metric_name])
                elif fallback_name and fallback_name in attr_dict[f]:
                    values.append(attr_dict[f][fallback_name])
            return values
        
        # Extract all 9 metrics
        metric_extractors = {
            'brightness': ('brightness', None),
            'exposure': ('exposure', None),
            'contrast': ('contrast', None),
            'dynamic_range': ('dynamic_range', None),
            'colorfulness': ('colorfulness', None),
            'edge_density': ('edge_density', None),
            'sharpness': ('sharpness', None),
            'entropy': ('entropy', None),
            'gaussian_noise_level': ('gaussian_noise_level', 'noise_level')  # Fallback to legacy
        }
        
        attribute_drifts = {}
        for metric_name, (key, fallback) in metric_extractors.items():
            ref_values = extract_metric(baseline_attr, key, fallback)
            cur_values = extract_metric(current_attr, key, fallback)
            
            if ref_values and cur_values:
                # Use PSI for drift detection (more stable than KL for distributions)
                try:
                    drift_score = self._calculate_psi(np.array(ref_values), np.array(cur_values))
                except:
                    # Fallback to KL divergence if PSI fails
                    drift_score = self._calculate_kl_divergence(ref_values, cur_values)
                attribute_drifts[metric_name] = drift_score
                print(f"   {metric_name:20s} Drift (PSI): {drift_score:.4f}")
            else:
                attribute_drifts[metric_name] = 0.0
        
        # Store all attribute drifts
        drift_metrics['attribute_drifts'] = attribute_drifts
        # Overall attribute drift (average of all metrics)
        drift_metrics['attribute_drift_overall'] = np.mean(list(attribute_drifts.values())) if attribute_drifts else 0.0
        
        # Legacy metrics for backward compatibility
        ref_sizes = extract_metric(baseline_attr, 'size')
        cur_sizes = extract_metric(current_attr, 'size')
        drift_metrics['size_drift'] = self._calculate_psi(np.array(ref_sizes), np.array(cur_sizes)) if ref_sizes and cur_sizes else 0
        drift_metrics['noise_drift'] = attribute_drifts.get('gaussian_noise_level', 0)
        drift_metrics['sharpness_drift'] = attribute_drifts.get('sharpness', 0)
        
        # Embedding drift (compare distributions even if files are different)
        if baseline_emb and current_emb:
            print("\n🧠 Embedding Drift (Multi-Metric Analysis):")
            print("-" * 80)
            
            # Cross-dataset comparison: always use all embeddings
            ref_emb_list = [baseline_emb[f]['embedding'] for f in baseline_emb]
            cur_emb_list = [current_emb[f]['embedding'] for f in current_emb]
            
            if ref_emb_list and cur_emb_list:
                ref_emb_array = np.array(ref_emb_list)
                cur_emb_array = np.array(cur_emb_list)
                
                # Use ensemble approach for robust drift detection
                embedding_drift_metrics = self._calculate_embedding_drift_ensemble(
                    ref_emb_array, cur_emb_array
                )

                # Round-11 (Track B) — wire ``detector`` parameter so
                # operators can request a single metric rather than the
                # weighted ensemble. Mapping uses the *normalized*
                # per-metric scores so every option stays in [0, 1].
                # ``default`` and the legacy ``mmd`` CLI default both
                # keep the historical ensemble behaviour.
                _strategy = (detector or "default").lower()
                _STRATEGIES = {
                    "default": embedding_drift_metrics["ensemble_score"],
                    "ensemble": embedding_drift_metrics["ensemble_score"],
                    "mmd": embedding_drift_metrics["normalized_scores"]["mmd_multiscale"],
                    "mean_shift": embedding_drift_metrics["normalized_scores"]["mean_shift"],
                    "wasserstein": embedding_drift_metrics["normalized_scores"]["wasserstein"],
                    "psi": embedding_drift_metrics["normalized_scores"]["psi"],
                    "cosine": embedding_drift_metrics["normalized_scores"]["cosine_distance"],
                }
                if _strategy not in _STRATEGIES:
                    return {
                        "status": "error",
                        "error_code": "unsupported_detector",
                        "modality": "image",
                        "message": (
                            f"vision plugin does not support detector={detector!r}. "
                            f"supported: {sorted(_STRATEGIES.keys())}"
                        ),
                    }

                # Store detailed metrics — keep full breakdown so callers
                # who picked one strategy can still inspect the others.
                drift_metrics['embedding_drift'] = float(_STRATEGIES[_strategy])
                drift_metrics['embedding_drift_detector'] = _strategy
                drift_metrics['embedding_drift_detailed'] = embedding_drift_metrics
                
                # Print detailed metrics
                print(f"   📊 Metric Breakdown:")
                print(f"      MMD (single-scale):  {embedding_drift_metrics['mmd']:.4f}")
                print(f"      MMD (multi-scale):   {embedding_drift_metrics['mmd_multiscale']:.4f} ± {embedding_drift_metrics['mmd_std']:.4f}")
                print(f"      Mean Shift:          {embedding_drift_metrics['mean_shift']:.4f}")
                print(f"      Wasserstein Dist:    {embedding_drift_metrics['wasserstein']:.4f}")
                print(f"      PSI (avg):           {embedding_drift_metrics['psi']:.4f}")
                print(f"      PSI (max):           {embedding_drift_metrics['psi_max']:.4f}")
                print(f"      Cosine Distance:     {embedding_drift_metrics['cosine_distance']:.4f}")
                print(f"   ")
                print(f"   🎯 Normalized Scores:")
                for metric_name, score in embedding_drift_metrics['normalized_scores'].items():
                    weight = embedding_drift_metrics['weights'][metric_name]
                    print(f"      {metric_name:20s}: {score:.4f} (weight: {weight:.2f})")
                print(f"   ")
                print(f"   ⚖️  Ensemble Score:      {embedding_drift_metrics['ensemble_score']:.4f}")
            else:
                drift_metrics['embedding_drift'] = 0.0
                drift_metrics['embedding_drift_detailed'] = None
                print(f"   Embedding Drift: 0.0000 (no embeddings found)")
        
        # Overall score (weighted average: attributes 45%, embedding 55%)
        # Attributes: average of all 9 metrics
        attr_score = drift_metrics.get('attribute_drift_overall', 0)
        emb_score = drift_metrics.get('embedding_drift', 0)
        overall = 0.45 * attr_score + 0.55 * emb_score
        drift_metrics['overall_score'] = overall
        
        # Status determination
        if overall < threshold_warning:
            status = 'NORMAL'
        elif overall < threshold_critical:
            status = 'WARNING'
        else:
            status = 'CRITICAL'
        
        drift_metrics['status'] = status
        drift_metrics['timestamp'] = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        print(f"\n📊 Overall Drift Score: {overall:.4f}")
        print(f"   Status: {status}")
        
        # Save metrics
        metrics_file = output_path / 'metrics.json'
        with open(metrics_file, 'w') as f:
            json.dump(drift_metrics, f, indent=2)
        
        # Update timeline
        timeline_file = output_path / "timeline.tsv"
        with open(timeline_file, 'a') as f:
            f.write(f"{drift_metrics['timestamp']}\t{overall:.4f}\t{status}\t{len(added)}\t{len(removed)}\n")
        
        # Extract dataset names from paths
        ref_dataset_name = ref_dataset_path.name
        cur_dataset_name = cur_dataset_path.name
        
        # Generate drift plots
        self._generate_drift_plots(
            plot_dir, baseline_attr, current_attr, baseline_emb, current_emb, 
            common, drift_metrics, ref_dataset_name, cur_dataset_name
        )
        
        print(f"\n✅ Drift Detection Complete")
        print(f"   📄 Metrics: {metrics_file}")
        print(f"   📊 Plots: {plot_dir}")
        
        drift_metrics['modality'] = 'image'
        return drift_metrics
    
    # ===== Helper Methods =====
    
    def _save_attribute_plots_csv(self, plot_csv_dir, sizes, noise_levels, sharpness_vals, quality_scores):
        """Save attribute analysis plots as CSV for DVC"""
        import pandas as pd
        
        # Size distribution
        if sizes:
            size_hist, size_bins = np.histogram(sizes, bins=20)
            pd.DataFrame({
                'size_mb': [round((size_bins[i] + size_bins[i+1]) / 2, 2) for i in range(len(size_hist))],
                'count': size_hist
            }).to_csv(plot_csv_dir / 'size_distribution.csv', index=False)
        
        # Noise distribution
        if noise_levels:
            noise_hist, noise_bins = np.histogram(noise_levels, bins=20)
            pd.DataFrame({
                'noise_level': [round((noise_bins[i] + noise_bins[i+1]) / 2, 3) for i in range(len(noise_hist))],
                'count': noise_hist
            }).to_csv(plot_csv_dir / 'noise_distribution.csv', index=False)
        
        # Sharpness distribution
        if sharpness_vals:
            sharp_hist, sharp_bins = np.histogram(sharpness_vals, bins=20)
            pd.DataFrame({
                'sharpness': [round((sharp_bins[i] + sharp_bins[i+1]) / 2, 2) for i in range(len(sharp_hist))],
                'count': sharp_hist
            }).to_csv(plot_csv_dir / 'sharpness_distribution.csv', index=False)
        
        # Quality map (scatter)
        if noise_levels and sharpness_vals:
            pd.DataFrame({
                'noise_level': noise_levels,
                'sharpness': sharpness_vals
            }).to_csv(plot_csv_dir / 'quality_map.csv', index=False)
        
        # Quality score
        if quality_scores:
            score_hist, score_bins = np.histogram(quality_scores, bins=20)
            pd.DataFrame({
                'quality_score': [round((score_bins[i] + score_bins[i+1]) / 2, 2) for i in range(len(score_hist))],
                'count': score_hist
            }).to_csv(plot_csv_dir / 'quality_score.csv', index=False)
    
    def _save_clustering_plots_csv(self, plot_csv_dir, plot_images_dir, clustering_result, embeddings_data):
        """Save clustering analysis plots"""
        import pandas as pd
        from sklearn.decomposition import PCA
        
        # Get cluster labels from the correct key
        cluster_labels = clustering_result.get('cluster_labels', [])
        
        if not cluster_labels:
            print("⚠️ No cluster labels found, skipping clustering plots")
            return
        
        # Embedding 2D PCA
        pca_2d = PCA(n_components=2)
        pca_2d_result = pca_2d.fit_transform(embeddings_data['embeddings'])
        
        pd.DataFrame({
            'pc1': pca_2d_result[:, 0],
            'pc2': pca_2d_result[:, 1],
            'cluster': cluster_labels
        }).to_csv(plot_csv_dir / 'embedding_2d_scatter.csv', index=False)
        
        # Cluster distribution
        unique, counts = np.unique(cluster_labels, return_counts=True)
        pd.DataFrame({
            'cluster_id': [f"Cluster {i}" for i in unique],
            'count': counts
        }).to_csv(plot_csv_dir / 'cluster_distribution.csv', index=False)
        
        # 3D visualization (image)
        pca_3d = PCA(n_components=3)
        pca_3d_result = pca_3d.fit_transform(embeddings_data['embeddings'])
        
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')
        scatter = ax.scatter(
            pca_3d_result[:, 0],
            pca_3d_result[:, 1],
            pca_3d_result[:, 2],
            c=cluster_labels,
            cmap='viridis',
            alpha=0.6
        )
        ax.set_xlabel('PC1')
        ax.set_ylabel('PC2')
        ax.set_zlabel('PC3')
        ax.set_title('Embedding Space (PCA 3D)')
        plt.colorbar(scatter, label='Cluster')
        plt.savefig(plot_images_dir / 'embedding_pca_3d.png', dpi=100, bbox_inches='tight')
        plt.close()
    
    def _calculate_kl_divergence(self, p, q, bins=20):
        """Calculate KL divergence"""
        p_hist, edges = np.histogram(p, bins=bins, density=True)
        q_hist, _ = np.histogram(q, bins=edges, density=True)
        
        p_hist = p_hist + 1e-10
        q_hist = q_hist + 1e-10
        
        p_hist = p_hist / p_hist.sum()
        q_hist = q_hist / q_hist.sum()
        
        return float(np.sum(p_hist * np.log(p_hist / q_hist)))
    
    def _calculate_mmd(self, X, Y, gamma=1.0):
        """Calculate Maximum Mean Discrepancy with improved numerical stability"""
        # Use smaller sample if datasets are too large to avoid numerical issues
        if X.shape[0] > 1000:
            X = X[:1000]
        if Y.shape[0] > 1000:
            Y = Y[:1000]
            
        # Normalize data to improve numerical stability
        X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-8)
        Y = (Y - Y.mean(axis=0)) / (Y.std(axis=0) + 1e-8)
        
        XX = np.dot(X, X.T)
        YY = np.dot(Y, Y.T)
        XY = np.dot(X, Y.T)
        
        X_sqnorms = np.diagonal(XX)
        Y_sqnorms = np.diagonal(YY)
        
        def rbf_kernel(X_sqnorms, Y_sqnorms, XY):
            K = -2 * XY + X_sqnorms[:, None] + Y_sqnorms[None, :]
            # Clip to avoid overflow
            K = np.clip(K, -50, 50)
            return np.exp(-gamma * K)
        
        K_XX = rbf_kernel(X_sqnorms, X_sqnorms, XX)
        K_YY = rbf_kernel(Y_sqnorms, Y_sqnorms, YY)
        K_XY = rbf_kernel(X_sqnorms, Y_sqnorms, XY)
        
        m = X.shape[0]
        n = Y.shape[0]
        
        # More stable MMD calculation - avoid diagonal removal
        # Use upper triangular part to avoid double counting
        mmd = np.sum(np.triu(K_XX, k=1)) / (m * (m - 1) / 2)
        mmd += np.sum(np.triu(K_YY, k=1)) / (n * (n - 1) / 2)
        mmd -= 2 * K_XY.sum() / (m * n)
        
        # Ensure non-negative result
        return float(np.sqrt(max(mmd, 0)))
    
    def _calculate_psi(self, baseline, current, bins=10):
        """
        Calculate Population Stability Index (PSI)
        
        PSI measures the shift in distribution between two datasets.
        - PSI < 0.1: No significant change
        - 0.1 <= PSI < 0.25: Moderate change
        - PSI >= 0.25: Significant change
        
        Args:
            baseline: Baseline distribution (1D array)
            current: Current distribution (1D array)
            bins: Number of bins for histogram
        
        Returns:
            float: PSI value
        """
        # Create histogram bins
        min_val = min(baseline.min(), current.min())
        max_val = max(baseline.max(), current.max())
        edges = np.linspace(min_val, max_val, bins + 1)
        
        # Calculate histograms
        baseline_hist, _ = np.histogram(baseline, bins=edges)
        current_hist, _ = np.histogram(current, bins=edges)
        
        # Convert to proportions (add 1 to avoid division by zero)
        baseline_prop = (baseline_hist + 1) / (baseline_hist.sum() + bins)
        current_prop = (current_hist + 1) / (current_hist.sum() + bins)
        
        # Calculate PSI
        psi = np.sum((current_prop - baseline_prop) * np.log(current_prop / baseline_prop))
        
        return float(abs(psi))
    
    def _calculate_embedding_drift_ensemble(self, X, Y):
        """
        Calculate embedding drift using multiple metrics for robust detection
        
        This ensemble approach combines:
        1. Multi-scale MMD: Tests at different kernel bandwidths
        2. Mean Shift: Measures centroid movement (preserves magnitude)
        3. Wasserstein Distance: Earth mover's distance on projections
        4. PSI: Population Stability Index on PCA components
        5. Cosine Distance: Directional change of mean vectors
        
        Args:
            X: Baseline embeddings (n_samples, n_features)
            Y: Current embeddings (m_samples, n_features)
        
        Returns:
            dict: Dictionary containing all metrics and ensemble score
        """
        metrics = {}
        
        # Use smaller sample if datasets are too large
        if X.shape[0] > 1000:
            X = X[:1000]
        if Y.shape[0] > 1000:
            Y = Y[:1000]
        
        # Store original (non-normalized) data for some metrics
        X_orig = X.copy()
        Y_orig = Y.copy()
        
        # 1. Multi-scale MMD (test with different gamma values)
        gammas = [0.1, 0.5, 1.0, 2.0, 5.0]
        mmd_scores = []
        for gamma in gammas:
            try:
                mmd = self._calculate_mmd(X.copy(), Y.copy(), gamma=gamma)
                mmd_scores.append(mmd)
            except Exception as e:
                print(f"   Warning: MMD calculation failed for gamma={gamma}: {e}")
                mmd_scores.append(0.0)
        
        metrics['mmd'] = self._calculate_mmd(X.copy(), Y.copy(), gamma=1.0)  # Default
        metrics['mmd_multiscale'] = float(np.mean(mmd_scores))
        metrics['mmd_std'] = float(np.std(mmd_scores))
        
        # 2. Mean Shift (magnitude-preserving, no normalization)
        X_mean = X_orig.mean(axis=0)
        Y_mean = Y_orig.mean(axis=0)
        mean_shift = np.linalg.norm(X_mean - Y_mean)
        # Normalize by embedding dimension for interpretability
        metrics['mean_shift'] = float(mean_shift / np.sqrt(X_orig.shape[1]))
        
        # 3. Wasserstein Distance (on 1D projections)
        try:
            from scipy.stats import wasserstein_distance
            # Project to 1D using mean across features
            proj_X = X_orig.mean(axis=1)
            proj_Y = Y_orig.mean(axis=1)
            metrics['wasserstein'] = float(wasserstein_distance(proj_X, proj_Y))
        except Exception as e:
            print(f"   Warning: Wasserstein distance calculation failed: {e}")
            metrics['wasserstein'] = 0.0
        
        # 4. Population Stability Index (PSI) on PCA components
        try:
            from sklearn.decomposition import PCA
            n_components = min(10, X_orig.shape[1], X_orig.shape[0], Y_orig.shape[0])
            pca = PCA(n_components=n_components)
            X_reduced = pca.fit_transform(X_orig)
            Y_reduced = pca.transform(Y_orig)
            
            psi_scores = []
            # Calculate PSI for top components
            for dim in range(min(5, n_components)):
                psi = self._calculate_psi(X_reduced[:, dim], Y_reduced[:, dim])
                psi_scores.append(psi)
            
            metrics['psi'] = float(np.mean(psi_scores)) if psi_scores else 0.0
            metrics['psi_max'] = float(np.max(psi_scores)) if psi_scores else 0.0
        except Exception as e:
            print(f"   Warning: PSI calculation failed: {e}")
            metrics['psi'] = 0.0
            metrics['psi_max'] = 0.0
        
        # 5. Cosine Distance (directional change)
        X_mean_norm = np.linalg.norm(X_mean)
        Y_mean_norm = np.linalg.norm(Y_mean)
        if X_mean_norm > 0 and Y_mean_norm > 0:
            cos_sim = np.dot(X_mean, Y_mean) / (X_mean_norm * Y_mean_norm)
            metrics['cosine_distance'] = float(max(0, 1 - cos_sim))
        else:
            metrics['cosine_distance'] = 0.0
        
        # Ensemble Score (weighted average with normalization)
        # Define weights for each metric
        weights = {
            'mmd_multiscale': 0.30,
            'mean_shift': 0.25,
            'wasserstein': 0.20,
            'psi': 0.15,
            'cosine_distance': 0.10
        }
        
        # Normalize each metric to 0-1 range based on expected thresholds
        # These thresholds are empirically determined
        normalized_scores = {
            'mmd_multiscale': min(metrics['mmd_multiscale'] / 0.5, 1.0),
            'mean_shift': min(metrics['mean_shift'] / 0.1, 1.0),
            'wasserstein': min(metrics['wasserstein'] / 1.0, 1.0),
            'psi': min(metrics['psi'] / 0.25, 1.0),
            'cosine_distance': min(metrics['cosine_distance'], 1.0)
        }
        
        # Calculate weighted ensemble score
        ensemble_score = sum(
            weights[k] * normalized_scores[k] 
            for k in weights.keys()
        )
        
        metrics['ensemble_score'] = float(ensemble_score)
        metrics['normalized_scores'] = normalized_scores
        metrics['weights'] = weights
        
        return metrics
    
    def _create_placeholder_plots(self, plot_dir):
        """Create placeholder plots for baseline"""
        plot_names = [
            'size_drift.png',
            'noise_drift.png',
            'sharpness_drift.png',
            'quality_score_drift.png',
            'quality_score_boxplot.png',
            'quality_map_drift.png',
            'embedding_drift_3d.png',
            'drift_scores.png'
        ]
        
        for plot_name in plot_names:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, 'BASELINE\n(Waiting for drift analysis)', 
                   ha='center', va='center', fontsize=20, color='gray')
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            plt.savefig(plot_dir / plot_name, dpi=100, bbox_inches='tight')
            plt.close()
    
    def _generate_drift_plots(self, plot_dir, ref_attr, cur_attr, ref_emb, cur_emb, common, 
                              drift_metrics=None, ref_name='Reference', cur_name='Current'):
        """Generate comprehensive drift visualization plots
        
        Args:
            ref_name: Reference dataset name (e.g., 'test_data')
            cur_name: Current dataset name (e.g., 'test_yolo_sample')
        """
        import seaborn as sns
        from sklearn.decomposition import PCA
        import pandas as pd
        
        # Create legend labels with dataset names
        ref_label = f'Reference ({ref_name})'
        cur_label = f'Current ({cur_name})'
        
        # Extract attributes
        if common:
            # Same dataset comparison
            ref_sizes = [ref_attr[f]['size'] for f in common if f in ref_attr and 'size' in ref_attr[f]]
            cur_sizes = [cur_attr[f]['size'] for f in common if f in cur_attr and 'size' in cur_attr[f]]
            ref_noise = [ref_attr[f]['noise_level'] for f in common if f in ref_attr and 'noise_level' in ref_attr[f]]
            cur_noise = [cur_attr[f]['noise_level'] for f in common if f in cur_attr and 'noise_level' in cur_attr[f]]
            ref_sharp = [ref_attr[f]['sharpness'] for f in common if f in ref_attr and 'sharpness' in ref_attr[f]]
            cur_sharp = [cur_attr[f]['sharpness'] for f in common if f in cur_attr and 'sharpness' in cur_attr[f]]
        else:
            # Cross-dataset comparison
            ref_sizes = [ref_attr[f]['size'] for f in ref_attr if 'size' in ref_attr[f]]
            cur_sizes = [cur_attr[f]['size'] for f in cur_attr if 'size' in cur_attr[f]]
            ref_noise = [ref_attr[f]['noise_level'] for f in ref_attr if 'noise_level' in ref_attr[f]]
            cur_noise = [cur_attr[f]['noise_level'] for f in cur_attr if 'noise_level' in cur_attr[f]]
            ref_sharp = [ref_attr[f]['sharpness'] for f in ref_attr if 'sharpness' in ref_attr[f]]
            cur_sharp = [cur_attr[f]['sharpness'] for f in cur_attr if 'sharpness' in cur_attr[f]]
        
        # 1. Size Distribution Comparison
        if ref_sizes and cur_sizes:
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.hist(ref_sizes, bins=30, alpha=0.6, label=ref_label, color='#3498db', density=True, edgecolor='black')
            ax.hist(cur_sizes, bins=30, alpha=0.6, label=cur_label, color='#e74c3c', density=True, edgecolor='black')
            ax.set_xlabel('File Size (MB)', fontsize=12)
            ax.set_ylabel('Density', fontsize=12)
            ax.set_title(f'File Size Distribution: {ref_name} vs {cur_name}', fontsize=14, fontweight='bold')
            ax.legend(fontsize=11)
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(plot_dir / 'size_drift.png', dpi=150, bbox_inches='tight')
            plt.close()
        
        # 2. Noise Distribution Comparison
        if ref_noise and cur_noise:
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.hist(ref_noise, bins=30, alpha=0.6, label=ref_label, color='#3498db', density=True, edgecolor='black')
            ax.hist(cur_noise, bins=30, alpha=0.6, label=cur_label, color='#e74c3c', density=True, edgecolor='black')
            ax.set_xlabel('Noise Level', fontsize=12)
            ax.set_ylabel('Density', fontsize=12)
            ax.set_title(f'Noise Distribution: {ref_name} vs {cur_name}', fontsize=14, fontweight='bold')
            ax.legend(fontsize=11)
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(plot_dir / 'noise_drift.png', dpi=150, bbox_inches='tight')
            plt.close()
        
        # 3. Sharpness Distribution Comparison
        if ref_sharp and cur_sharp:
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.hist(ref_sharp, bins=30, alpha=0.6, label=ref_label, color='#3498db', density=True, edgecolor='black')
            ax.hist(cur_sharp, bins=30, alpha=0.6, label=cur_label, color='#e74c3c', density=True, edgecolor='black')
            ax.set_xlabel('Sharpness', fontsize=12)
            ax.set_ylabel('Density', fontsize=12)
            ax.set_title(f'Sharpness Distribution: {ref_name} vs {cur_name}', fontsize=14, fontweight='bold')
            ax.legend(fontsize=11)
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(plot_dir / 'sharpness_drift.png', dpi=150, bbox_inches='tight')
            plt.close()
        
        # 4. Quality Map (Noise vs Sharpness scatter)
        if ref_noise and ref_sharp and cur_noise and cur_sharp:
            fig, ax = plt.subplots(figsize=(12, 10))
            ax.scatter(ref_noise, ref_sharp, alpha=0.5, s=80, c='#3498db', 
                      label=ref_label, edgecolors='darkblue', linewidth=0.5)
            ax.scatter(cur_noise, cur_sharp, alpha=0.5, s=80, c='#e74c3c', 
                      label=cur_label, edgecolors='darkred', linewidth=0.5)
            
            # 중앙값 선
            all_noise = ref_noise + cur_noise
            all_sharp = ref_sharp + cur_sharp
            ax.axhline(y=np.median(all_sharp), color='gray', linestyle='--', alpha=0.5, label='Median Sharpness')
            ax.axvline(x=np.median(all_noise), color='gray', linestyle='--', alpha=0.5, label='Median Noise')
            
            ax.set_xlabel('Noise Level', fontsize=12)
            ax.set_ylabel('Sharpness', fontsize=12)
            ax.set_title(f'Quality Map: {ref_name} vs {cur_name}', fontsize=14, fontweight='bold')
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(plot_dir / 'quality_map_drift.png', dpi=150, bbox_inches='tight')
            plt.close()
        
        # 5. Boxplot Comparison
        if ref_sizes and cur_sizes and ref_noise and cur_noise and ref_sharp and cur_sharp:
            df_data = []
            for val in ref_sizes:
                df_data.append({'Metric': 'Size', 'Dataset': ref_label, 'Value': val})
            for val in cur_sizes:
                df_data.append({'Metric': 'Size', 'Dataset': cur_label, 'Value': val})
            for val in ref_noise:
                df_data.append({'Metric': 'Noise', 'Dataset': ref_label, 'Value': val})
            for val in cur_noise:
                df_data.append({'Metric': 'Noise', 'Dataset': cur_label, 'Value': val})
            for val in ref_sharp:
                df_data.append({'Metric': 'Sharpness', 'Dataset': ref_label, 'Value': val})
            for val in cur_sharp:
                df_data.append({'Metric': 'Sharpness', 'Dataset': cur_label, 'Value': val})
            
            df = pd.DataFrame(df_data)
            
            fig, ax = plt.subplots(figsize=(14, 7))
            sns.boxplot(data=df, x='Metric', y='Value', hue='Dataset', ax=ax, palette=['#3498db', '#e74c3c'])
            ax.set_title(f'Attribute Comparison: {ref_name} vs {cur_name}', fontsize=14, fontweight='bold')
            ax.set_ylabel('Value', fontsize=12)
            ax.set_xlabel('Metric', fontsize=12)
            ax.legend(title='Dataset', fontsize=10)
            ax.grid(True, alpha=0.3, axis='y')
            plt.tight_layout()
            plt.savefig(plot_dir / 'quality_score_boxplot.png', dpi=150, bbox_inches='tight')
            plt.close()
        
        # 6. Embedding 3D PCA
        if ref_emb and cur_emb:
            if common:
                ref_emb_list = [ref_emb[f]['embedding'] for f in common if f in ref_emb]
                cur_emb_list = [cur_emb[f]['embedding'] for f in common if f in cur_emb]
            else:
                ref_emb_list = [ref_emb[f]['embedding'] for f in ref_emb]
                cur_emb_list = [cur_emb[f]['embedding'] for f in cur_emb]
            
            if ref_emb_list and cur_emb_list:
                ref_emb_array = np.array(ref_emb_list)
                cur_emb_array = np.array(cur_emb_list)
                
                # PCA 3D
                all_embeddings = np.vstack([ref_emb_array, cur_emb_array])
                pca = PCA(n_components=3)
                pca_result = pca.fit_transform(all_embeddings)
                
                ref_pca = pca_result[:len(ref_emb_array)]
                cur_pca = pca_result[len(ref_emb_array):]
                
                fig = plt.figure(figsize=(14, 10))
                ax = fig.add_subplot(111, projection='3d')
                
                ax.scatter(ref_pca[:, 0], ref_pca[:, 1], ref_pca[:, 2],
                          c='#3498db', alpha=0.6, s=50, label=ref_label, 
                          edgecolors='darkblue', linewidth=0.5)
                ax.scatter(cur_pca[:, 0], cur_pca[:, 1], cur_pca[:, 2],
                          c='#e74c3c', alpha=0.6, s=50, label=cur_label,
                          edgecolors='darkred', linewidth=0.5)
                
                ax.set_xlabel(f'PC1 ({pca.explained_variance_ratio_[0]*100:.1f}%)', fontsize=11)
                ax.set_ylabel(f'PC2 ({pca.explained_variance_ratio_[1]*100:.1f}%)', fontsize=11)
                ax.set_zlabel(f'PC3 ({pca.explained_variance_ratio_[2]*100:.1f}%)', fontsize=11)
                ax.set_title(f'Embedding Distribution: {ref_name} vs {cur_name}', fontsize=14, fontweight='bold')
                ax.legend(fontsize=12)
                ax.view_init(elev=20, azim=45)
                
                plt.tight_layout()
                plt.savefig(plot_dir / 'embedding_drift_3d.png', dpi=150, bbox_inches='tight')
                plt.close()
        
        # 7. Drift Scores Bar Chart
        if drift_metrics:
            metrics = {
                'Size': drift_metrics.get('size_drift', 0),
                'Noise': drift_metrics.get('noise_drift', 0),
                'Sharpness': drift_metrics.get('sharpness_drift', 0),
                'Embedding': drift_metrics.get('embedding_drift', 0) * 100,  # Scale for visibility
                'Overall': drift_metrics.get('overall_score', 0)
            }
            
            fig, ax = plt.subplots(figsize=(12, 7))
            
            colors = ['#27ae60' if v < 0.15 else '#f39c12' if v < 0.25 else '#e74c3c' 
                      for v in metrics.values()]
            
            bars = ax.bar(metrics.keys(), metrics.values(), color=colors, 
                         edgecolor='black', linewidth=1.5, alpha=0.8)
            
            # 임계값 선
            ax.axhline(y=0.15, color='#f39c12', linestyle='--', linewidth=2, 
                      label='Warning Threshold (0.15)', alpha=0.7)
            ax.axhline(y=0.25, color='#e74c3c', linestyle='--', linewidth=2, 
                      label='Critical Threshold (0.25)', alpha=0.7)
            
            # 값 레이블
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.3f}',
                       ha='center', va='bottom', fontsize=11, fontweight='bold')
            
            # 상태 표시
            status = drift_metrics.get('status', 'UNKNOWN')
            status_color = {'NORMAL': '#27ae60', 'WARNING': '#f39c12', 'CRITICAL': '#e74c3c'}.get(status, 'gray')
            ax.text(0.98, 0.98, f'Status: {status}', 
                   transform=ax.transAxes, fontsize=14, fontweight='bold',
                   verticalalignment='top', horizontalalignment='right',
                   bbox=dict(boxstyle='round', facecolor=status_color, alpha=0.3))
            
            ax.set_ylabel('Drift Score', fontsize=12)
            ax.set_xlabel('Metric', fontsize=12)
            ax.set_title('Drift Scores by Metric', fontsize=14, fontweight='bold')
            ax.legend(fontsize=10, loc='upper left')
            ax.grid(True, alpha=0.3, axis='y')
            plt.tight_layout()
            plt.savefig(plot_dir / 'drift_scores.png', dpi=150, bbox_inches='tight')
            plt.close()
        
        # 8. Quality Score Drift (Violin Plot)
        if ref_sizes and cur_sizes and ref_noise and cur_noise and ref_sharp and cur_sharp:
            # 품질 점수 계산 (간단한 공식: sharpness / (1 + noise))
            ref_quality = [s / (1 + n) for s, n in zip(ref_sharp, ref_noise)]
            cur_quality = [s / (1 + n) for s, n in zip(cur_sharp, cur_noise)]
            
            df_quality = pd.DataFrame({
                'Quality Score': ref_quality + cur_quality,
                'Dataset': [ref_label]*len(ref_quality) + [cur_label]*len(cur_quality)
            })
            
            fig, ax = plt.subplots(figsize=(10, 7))
            sns.violinplot(data=df_quality, x='Dataset', y='Quality Score', hue='Dataset',
                          ax=ax, palette=['#3498db', '#e74c3c'], legend=False)
            ax.set_title(f'Quality Score: {ref_name} vs {cur_name}', fontsize=14, fontweight='bold')
            ax.set_ylabel('Quality Score (Sharpness / (1 + Noise))', fontsize=11)
            ax.grid(True, alpha=0.3, axis='y')
            plt.tight_layout()
            plt.savefig(plot_dir / 'quality_score_drift.png', dpi=150, bbox_inches='tight')
            plt.close()
        
        print("   📊 Drift visualizations generated")
    
    
    def _get_current_image_files(self, input_path: Path, formats: tuple) -> list:
        """
        Get current image files from directory.
        Supports:
        - Flat structure: data/*.jpg
        - YOLO structure: data/train/images/*.jpg
        - Nested datasets: data/dataset1/train/images/*.jpg
        - Multiple datasets: data/dataset1/..., data/dataset2/...
        """
        image_files = []
        
        # Recursively find all image files
        # This handles all possible structures
        for fmt in formats:
            image_files.extend(list(input_path.rglob(f"*{fmt}")))
        
        return image_files

    @hookimpl
    def ddoc_get_metadata(self) -> Dict[str, Any]:
        """Return plugin metadata"""
        return {
            "name": "ddoc-plugin-vision",
            "version": "0.1.0",
            "description": "Vision analysis plugin for image datasets",
            "hooks": ["eda_run", "drift_detect", "ddoc_supported_detectors"],
            "modalities": ["image"]
        }

    @hookimpl
    def ddoc_supported_detectors(self) -> Dict[str, Any]:
        """Round-13 (Gap 5) — declare the detector strategies this
        plugin honours so the CLI can validate ``--detector`` upfront.
        Mirrors the runtime ``_SUPPORTED_DETECTORS`` set inside
        ``drift_detect`` (Round-11)."""
        return {
            "modality": "image",
            "default": "ensemble",
            "supported": [
                "default", "ensemble", "mmd", "mean_shift",
                "wasserstein", "psi", "cosine",
            ],
            "notes": (
                "5-metric ensemble (multi-scale MMD + mean shift + 1-D "
                "wasserstein + PSI-on-PCA + cosine). All values map to a "
                "[0, 1]-normalized score; ``default``/``ensemble`` are "
                "the weighted sum, the rest pick a single metric."
            ),
        }

