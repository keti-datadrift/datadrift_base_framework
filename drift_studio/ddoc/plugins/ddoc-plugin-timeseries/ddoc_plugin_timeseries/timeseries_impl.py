"""
Time Series Analysis Plugin Implementation for ddoc

Provides hookimpl for:
- eda_run: Time series attribute analysis
- drift_detect: Drift detection between baseline and current time series datasets
"""
import os
import yaml
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

try:
    from ddoc.plugins.hookspecs import hookimpl
except ImportError:
    def hookimpl(func):
        return func

try:
    from scipy import stats
    from statsmodels.tsa.stattools import adfuller, kpss
    from statsmodels.tsa.seasonal import seasonal_decompose
except ImportError as e:
    print(f"Warning: Some dependencies not available: {e}")


class DOCTimeSeriesPlugin:
    """Time Series Analysis Plugin for ddoc"""
    
    def _load_ddoc_yaml(self, dataset_path: Path) -> Dict[str, Any]:
        """Load and validate ddoc.yaml from dataset directory"""
        yaml_path = dataset_path / "ddoc.yaml"
        if not yaml_path.exists():
            raise ValueError(f"ddoc.yaml not found in {dataset_path}")
        
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if config.get('modality') != 'timeseries':
            raise ValueError(f"Dataset {dataset_path} is not configured as timeseries modality")
        
        if 'csv_file' not in config:
            raise ValueError("ddoc.yaml must specify 'csv_file'")
        if 'timestamp_column' not in config:
            raise ValueError("ddoc.yaml must specify 'timestamp_column'")
        
        return config
    
    def _analyze_numeric_series(self, series: pd.Series) -> Dict[str, Any]:
        """Calculate numeric time series metrics"""
        if series.empty or series.isna().all():
            return {}
        
        series_clean = series.dropna()
        if series_clean.empty:
            return {}
        
        metrics = {
            'mean': float(series_clean.mean()),
            'variance': float(series_clean.var()),
            'skewness': float(stats.skew(series_clean)),
            'kurtosis': float(stats.kurtosis(series_clean))
        }
        
        # Trend, seasonality, residual (if enough data)
        if len(series_clean) >= 24:  # Minimum for decomposition
            try:
                decomposition = seasonal_decompose(series_clean, model='additive', period=min(12, len(series_clean)//2))
                metrics['trend_strength'] = float(np.var(decomposition.trend.dropna()) / (np.var(series_clean) + 1e-10))
                metrics['seasonal_strength'] = float(np.var(decomposition.seasonal.dropna()) / (np.var(series_clean) + 1e-10))
                metrics['residual_strength'] = float(np.var(decomposition.resid.dropna()) / (np.var(series_clean) + 1e-10))
            except:
                pass
        
        # Stationarity tests
        try:
            adf_result = adfuller(series_clean)
            metrics['adf_statistic'] = float(adf_result[0])
            metrics['adf_pvalue'] = float(adf_result[1])
            metrics['is_stationary_adf'] = adf_result[1] < 0.05
        except:
            pass
        
        try:
            kpss_result = kpss(series_clean, regression='c')
            metrics['kpss_statistic'] = float(kpss_result[0])
            metrics['kpss_pvalue'] = float(kpss_result[1])
            metrics['is_stationary_kpss'] = kpss_result[1] > 0.05
        except:
            pass
        
        return metrics
    
    def _analyze_categorical_series(self, series: pd.Series) -> Dict[str, Any]:
        """Calculate categorical time series metrics"""
        if series.empty:
            return {}
        
        value_counts = series.value_counts()
        frequencies = value_counts.to_dict()
        
        # Entropy
        probs = value_counts / len(series)
        entropy = -np.sum(probs * np.log2(probs + 1e-10))
        
        return {
            'frequencies': {str(k): int(v) for k, v in frequencies.items()},
            'entropy': float(entropy),
            'unique_count': len(value_counts)
        }
    
    def _compute_attributes_from_path(self, data_path) -> Dict[str, Any]:
        """Walk ``data_path`` for ``ddoc.yaml`` -declared timeseries
        datasets and compute the per-column attributes dict in-process.

        Round-6 (2026-05-08) — extracted from ``eda_run`` so that
        ``drift_detect`` path mode (where no analysis cache exists) can
        reuse the exact same attribute computation. Returns the same
        ``{<dataset>/<col>: {...metrics...}}`` shape that the cache
        would normally hold; empty dict when no datasets are found.
        """
        input_path = Path(data_path)
        if not input_path.exists() or not input_path.is_dir():
            return {}

        ts_datasets = []
        for item in input_path.iterdir():
            if not item.is_dir():
                continue
            yaml_path = item / "ddoc.yaml"
            if not yaml_path.exists():
                continue
            try:
                config = self._load_ddoc_yaml(item)
                if config.get('modality') == 'timeseries':
                    ts_datasets.append((item, config))
            except Exception as e:
                print(f"⚠️ Skipping {item}: {e}")

        all_attributes: Dict[str, Any] = {}
        for dataset_path, config in ts_datasets:
            csv_file = dataset_path / config['csv_file']
            if not csv_file.exists():
                continue
            timestamp_col = config['timestamp_column']
            numeric_cols = config.get('numeric_columns', [])
            categorical_cols = config.get('categorical_columns', [])
            try:
                df = pd.read_csv(csv_file)
                df[timestamp_col] = pd.to_datetime(df[timestamp_col])
                df = df.sort_values(timestamp_col)
            except Exception as e:
                print(f"⚠️ Error loading CSV: {e}")
                continue
            for col in numeric_cols:
                if col in df.columns:
                    key = f"{dataset_path.name}/{col}"
                    all_attributes[key] = self._analyze_numeric_series(df[col])
            for col in categorical_cols:
                if col in df.columns:
                    key = f"{dataset_path.name}/{col}"
                    all_attributes[key] = self._analyze_categorical_series(df[col])
        return all_attributes

    @hookimpl
    def eda_run(self, snapshot_id, data_path, data_hash, output_path, invalidate_cache=False):
        """Run EDA for time series datasets"""
        from ddoc.core.cache_service import get_cache_service

        cache_service = get_cache_service()
        output_path = Path(output_path)

        print(f"🚀 Time Series EDA Analysis Started")
        print(f"=" * 80)

        output_path.mkdir(parents=True, exist_ok=True)

        metrics = {
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'snapshot_id': snapshot_id,
            'data_hash': data_hash,
            'modality': 'timeseries'
        }

        all_attributes = self._compute_attributes_from_path(data_path)
        if not all_attributes:
            print("⚠️ No time series datasets found")
            return None

        # Save cache (only when we have a real data_hash — path mode
        # passes empty hash because no snapshot context exists, in
        # which case caching is the orchestrator's job).
        if all_attributes and data_hash:
            cache_service.save_analysis_cache(
                snapshot_id=snapshot_id,
                data_hash=data_hash,
                cache_type="attributes_timeseries",
                data=all_attributes
            )
        
        metrics['num_series'] = len(all_attributes)
        metrics_file = output_path / "metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        print(f"\n✅ Time Series Analysis Complete")
        
        return {
            "status": "success",
            "modality": "timeseries",
            "series_analyzed": len(all_attributes),
            "metrics_file": str(metrics_file),
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
        """Detect drift between two time series snapshots"""
        from ddoc.core.cache_service import get_cache_service
        
        cache_service = get_cache_service()
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Resolve baseline/current attribute dicts in three tiers:
        # 1. Explicit caches passed in cfg (snapshot mode, when the CLI
        #    pre-loaded them).
        # 2. Cache service lookup keyed by data_hash (works for both
        #    snapshot mode and warm path-mode caches).
        # 3. **Path-mode fallback (Round-6)** — compute attributes
        #    inline from data_path_*. This is what makes
        #    ``ddoc analyze drift --data-path-ref X --data-path-cur Y``
        #    actually work without any project / snapshot context.
        def _resolve(cfg_key, snap_id, data_hash, data_path):
            attrs = cfg.get(cfg_key)
            if attrs:
                return attrs
            attrs = cache_service.load_analysis_cache(
                snapshot_id=snap_id,
                data_hash=data_hash,
                cache_type="attributes_timeseries",
            )
            if attrs:
                return attrs
            if data_path:
                return self._compute_attributes_from_path(data_path)
            return None

        baseline_attr = _resolve(
            'baseline_cache', snapshot_id_ref, data_hash_ref, data_path_ref,
        )
        current_attr = _resolve(
            'current_cache', snapshot_id_cur, data_hash_cur, data_path_cur,
        )

        if not baseline_attr or not current_attr:
            return None
        
        drift_metrics = {
            'modality': 'timeseries',
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
        }
        
        # Calculate drift for each metric
        drift_scores = []
        for key in set(baseline_attr.keys()) & set(current_attr.keys()):
            baseline = baseline_attr[key]
            current = current_attr[key]
            
            # Compare numeric metrics
            for metric in ['mean', 'variance', 'skewness', 'kurtosis']:
                if metric in baseline and metric in current:
                    diff = abs(baseline[metric] - current[metric])
                    drift_scores.append(diff)
        
        drift_metrics['overall_score'] = float(np.mean(drift_scores)) if drift_scores else 0.0
        
        metrics_file = output_path / 'metrics.json'
        with open(metrics_file, 'w') as f:
            json.dump(drift_metrics, f, indent=2)
        
        return drift_metrics

