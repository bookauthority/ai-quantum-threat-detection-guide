from __future__ import annotations

from typing import Dict, Any

# Experiment identifier from the specification
EXPERIMENT_ID = "exp-ch7-quantum-telemetry-to-ml-ready-datasets-v1"

# Minimal configurations for three workloads, matching the spec identifiers.

WORKLOAD_CONFIGS: Dict[str, Dict[str, Any]] = {
    "W1_5s_sliding_windows_binary_attack_detection": {
        "window_type": "fixed_sliding_time_window",
        "window_length_seconds": 5.0,
        "window_stride_seconds": 1.0,
        "attack_coverage_threshold": 0.3,
        "label_mode": "binary_attack_vs_clean",
        "split_strategy": "run_based_split",
        "split_proportions": {"train": 0.6, "val": 0.2, "test": 0.2},
        "random_seed": 42,
    },
    "W2_event_centered_eavesdropping_vs_clean": {
        "window_type": "event_centered_window",
        "pre_event_duration_seconds": 10.0,
        "post_event_duration_seconds": 10.0,
        "event_filter": "attack_type == 'eavesdrop'",
        "label_mode": "binary_eavesdrop_vs_clean",
        "split_strategy": "run_based_split",
        "split_proportions": {"train": 0.6, "val": 0.2, "test": 0.2},
        "random_seed": 42,
    },
    "W3_multiclass_attack_type_classification": {
        "window_type": "fixed_sliding_time_window",
        "window_length_seconds": 5.0,
        "window_stride_seconds": 2.0,
        "label_mode": "multiclass_by_attack_type",
        "split_strategy": "run_based_split",  # simplified vs time_based
        "split_proportions": {"train": 0.6, "val": 0.2, "test": 0.2},
        "random_seed": 42,
    },
}
