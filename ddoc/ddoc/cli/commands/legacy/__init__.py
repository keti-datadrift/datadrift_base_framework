"""
Legacy v1.x commands (DEPRECATED)

This module contains all v1.x commands that are deprecated in v2.0
and will be removed in v2.1.

Structure:
- dataset.py: Dataset management commands (add, commit, status, etc.)
- experiment.py: Experiment commands (run, list, show, compare, etc.)  
- lineage.py: Lineage tracking commands
- deprecated.py: Top-level deprecated commands (commit, checkout, log, etc.)
"""

# Import all legacy commands from the full module
# This allows gradual migration without breaking existing imports
from .full import (
    # Dataset commands
    dataset_add_command,
    dataset_list_command,
    dataset_commit_command,
    dataset_status_command,
    dataset_unstage_command,
    dataset_tag_list_command,
    dataset_tag_rename_command,
    dataset_timeline_command,
    dataset_checkout_command,
    
    # Experiment commands
    exp_run_command,
    exp_list_command,
    exp_show_command,
    exp_compare_command,
    exp_status_command,
    exp_best_command,
    
    # Lineage commands
    lineage_show_command,
    lineage_graph_command,
    lineage_overview_command,
    lineage_impact_command,
    lineage_dependencies_command,
    lineage_dependents_command,
    
    # Deprecated top-level commands
    commit,
    checkout,
    log,
    status,
    alias_cmd,
    diff,
    init_old,
)

__all__ = [
    # Dataset
    'dataset_add_command',
    'dataset_list_command',
    'dataset_commit_command',
    'dataset_status_command',
    'dataset_unstage_command',
    'dataset_tag_list_command',
    'dataset_tag_rename_command',
    'dataset_timeline_command',
    'dataset_checkout_command',
    
    # Experiment
    'exp_run_command',
    'exp_list_command',
    'exp_show_command',
    'exp_compare_command',
    'exp_status_command',
    'exp_best_command',
    
    # Lineage
    'lineage_show_command',
    'lineage_graph_command',
    'lineage_overview_command',
    'lineage_impact_command',
    'lineage_dependencies_command',
    'lineage_dependents_command',
    
    # Deprecated
    'commit',
    'checkout',
    'log',
    'status',
    'alias_cmd',
    'diff',
    'init_old',
]

