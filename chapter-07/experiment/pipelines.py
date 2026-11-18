from __future__ import annotations

import math
import random
from typing import Dict, List, Any, Tuple


def _split_indices_run_based(run_ids: List[str], proportions: Dict[str, float], seed: int) -> Dict[str, List[str]]:
    rng = random.Random(seed)
    shuffled = list(run_ids)
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(proportions.get("train", 0.6) * n)
    n_val = int(proportions.get("val", 0.2) * n)
    train_ids = shuffled[:n_train]
    val_ids = shuffled[n_train:n_train + n_val]
    test_ids = shuffled[n_train + n_val:]
    return {"train": train_ids, "val": val_ids, "test": test_ids}


def run_baseline_pipeline(workload_id: str, cfg: Dict[str, Any], raw_runs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Naive per-row baseline pipeline.

    Returns a dict with sample counts per split.
    """

    rows: List[Dict[str, Any]] = []
    for run_id, bundle in raw_runs.items():
        for r in bundle["telemetry"]:
            label_attack = 1 if r.get("attack_flag") else 0
            rows.append(
                {
                    "run_id": r["run_id"],
                    "link_id": r["link_id"],
                    "timestamp": r["timestamp"],
                    "qber": r["qber"],
                    "key_rate": r["key_rate"],
                    "loss_db": r["loss_db"],
                    "if_util": r["if_util"],
                    "label_attack": label_attack,
                }
            )

    # random split by row: 70/15/15
    rng = random.Random(cfg.get("random_seed", 42))
    indices = list(range(len(rows)))
    rng.shuffle(indices)
    n = len(indices)
    n_train = int(0.7 * n)
    n_val = int(0.15 * n)
    train_idx = indices[:n_train]
    val_idx = indices[n_train:n_train + n_val]
    test_idx = indices[n_train + n_val:]

    num_train = len(train_idx)
    num_val = len(val_idx)
    num_test = len(test_idx)

    return {
        "run_id": f"{workload_id}_baseline",
        "success": True,
        "num_samples_train": num_train,
        "num_samples_val": num_val,
        "num_samples_test": num_test,
    }


def _build_fixed_windows(rows: List[Dict[str, Any]], window_length: float, window_stride: float) -> List[Dict[str, Any]]:
    # group by (run_id, link_id)
    by_group: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for r in rows:
        key = (r["run_id"], r["link_id"])
        by_group.setdefault(key, []).append(r)

    # sort each group by timestamp
    for key in by_group:
        by_group[key].sort(key=lambda x: x["timestamp"])

    windows: List[Dict[str, Any]] = []
    for (run_id, link_id), grp in by_group.items():
        if not grp:
            continue
        start_time = grp[0]["timestamp"]
        end_time = grp[-1]["timestamp"]
        w_start = start_time
        while w_start + window_length <= end_time + 1e-9:
            w_end = w_start + window_length
            samples = [r for r in grp if w_start <= r["timestamp"] < w_end]
            if samples:
                windows.append(_aggregate_window(run_id, link_id, w_start, w_end, samples))
            w_start += window_stride
    return windows


def _build_event_centered_windows(
    rows: List[Dict[str, Any]],
    scenario: Dict[str, Any],
    pre_dur: float,
    post_dur: float,
    attack_type_filter: str,
) -> List[Dict[str, Any]]:
    # group rows
    by_group: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for r in rows:
        key = (r["run_id"], r["link_id"])
        by_group.setdefault(key, []).append(r)
    for key in by_group:
        by_group[key].sort(key=lambda x: x["timestamp"])

    windows: List[Dict[str, Any]] = []
    for interval in scenario.get("attack_intervals", []):
        if interval.get("attack_type") != attack_type_filter:
            continue
        link_id = interval["link_id"]
        start = interval["start"]
        # center around start
        w_start = start - pre_dur
        w_end = start + post_dur
        if w_start < 0:
            w_start = 0.0
        for (run_id, l_id), grp in by_group.items():
            if l_id != link_id:
                continue
            samples = [r for r in grp if w_start <= r["timestamp"] <= w_end]
            if samples:
                windows.append(_aggregate_window(run_id, link_id, w_start, w_end, samples))
    return windows


def _aggregate_window(run_id: str, link_id: str, w_start: float, w_end: float, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    def stats(key: str) -> Tuple[float, float, float, float]:
        vals = [float(s[key]) for s in samples]
        n = len(vals)
        mean = sum(vals) / n
        var = sum((v - mean) ** 2 for v in vals) / n if n > 0 else 0.0
        std = math.sqrt(var)
        return mean, std, min(vals), max(vals)

    qber_mean, qber_std, qber_min, qber_max = stats("qber")
    kr_mean, kr_std, kr_min, kr_max = stats("key_rate")
    loss_mean, loss_std, loss_min, loss_max = stats("loss_db")
    iu_mean, iu_std, iu_min, iu_max = stats("if_util")
    pdr_mean, pdr_std, pdr_min, pdr_max = stats("pkt_drop_rate")
    jit_mean, jit_std, jit_min, jit_max = stats("jitter")
    cpu_mean, cpu_std, cpu_min, cpu_max = stats("cpu_load")
    mem_mean, mem_std, mem_min, mem_max = stats("mem_util")

    duration = w_end - w_start

    return {
        "run_id": run_id,
        "link_id": link_id,
        "window_start": w_start,
        "window_end": w_end,
        "window_duration": duration,
        "sample_count": len(samples),
        "q_qber_mean": qber_mean,
        "q_qber_std": qber_std,
        "q_qber_min": qber_min,
        "q_qber_max": qber_max,
        "q_key_rate_mean": kr_mean,
        "q_key_rate_std": kr_std,
        "q_key_rate_min": kr_min,
        "q_key_rate_max": kr_max,
        "q_loss_mean": loss_mean,
        "q_loss_std": loss_std,
        "q_loss_min": loss_min,
        "q_loss_max": loss_max,
        "c_if_util_mean": iu_mean,
        "c_if_util_std": iu_std,
        "c_if_util_min": iu_min,
        "c_if_util_max": iu_max,
        "c_pkt_drop_mean": pdr_mean,
        "c_pkt_drop_std": pdr_std,
        "c_pkt_drop_min": pdr_min,
        "c_pkt_drop_max": pdr_max,
        "c_jitter_mean": jit_mean,
        "c_jitter_std": jit_std,
        "c_jitter_min": jit_min,
        "c_jitter_max": jit_max,
        "c_cpu_mean": cpu_mean,
        "c_cpu_std": cpu_std,
        "c_cpu_min": cpu_min,
        "c_cpu_max": cpu_max,
        "c_mem_mean": mem_mean,
        "c_mem_std": mem_std,
        "c_mem_min": mem_min,
        "c_mem_max": mem_max,
        # placeholder for label
        "label": None,
    }


def _label_windows_binary_attack(windows: List[Dict[str, Any]], scenario_by_run: Dict[str, Dict[str, Any]], coverage_threshold: float) -> List[Dict[str, Any]]:
    labeled: List[Dict[str, Any]] = []
    for w in windows:
        run_id = w["run_id"]
        link_id = w["link_id"]
        w_start = w["window_start"]
        w_end = w["window_end"]
        total = w_end - w_start
        attack_cover = 0.0
        for interval in scenario_by_run[run_id].get("attack_intervals", []):
            if interval["link_id"] != link_id:
                continue
            a_start = interval["start"]
            a_end = interval["end"]
            overlap = max(0.0, min(w_end, a_end) - max(w_start, a_start))
            attack_cover += overlap
        frac = attack_cover / total if total > 0 else 0.0
        label = 1 if frac >= coverage_threshold else 0
        w2 = dict(w)
        w2["label"] = label
        labeled.append(w2)
    return labeled


def _label_windows_binary_eavesdrop(windows: List[Dict[str, Any]], scenario_by_run: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    labeled: List[Dict[str, Any]] = []
    for w in windows:
        run_id = w["run_id"]
        link_id = w["link_id"]
        w_start = w["window_start"]
        w_end = w["window_end"]
        total = w_end - w_start
        attack_cover = 0.0
        for interval in scenario_by_run[run_id].get("attack_intervals", []):
            if interval["link_id"] != link_id:
                continue
            if interval.get("attack_type") != "eavesdrop":
                continue
            a_start = interval["start"]
            a_end = interval["end"]
            overlap = max(0.0, min(w_end, a_end) - max(w_start, a_start))
            attack_cover += overlap
        frac = attack_cover / total if total > 0 else 0.0
        label = 1 if frac > 0 else 0
        w2 = dict(w)
        w2["label"] = label
        labeled.append(w2)
    return labeled


def _label_windows_multiclass(windows: List[Dict[str, Any]], scenario_by_run: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    labeled: List[Dict[str, Any]] = []
    for w in windows:
        run_id = w["run_id"]
        link_id = w["link_id"]
        w_start = w["window_start"]
        w_end = w["window_end"]
        assigned = "clean"
        max_cover = 0.0
        for interval in scenario_by_run[run_id].get("attack_intervals", []):
            if interval["link_id"] != link_id:
                continue
            a_start = interval["start"]
            a_end = interval["end"]
            overlap = max(0.0, min(w_end, a_end) - max(w_start, a_start))
            if overlap > max_cover:
                max_cover = overlap
                assigned = interval.get("attack_type", "clean")
        w2 = dict(w)
        w2["label"] = assigned
        labeled.append(w2)
    return labeled


def run_treatment_pipeline(workload_id: str, cfg: Dict[str, Any], raw_runs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    # Flatten telemetry rows for convenience
    all_rows: List[Dict[str, Any]] = []
    scenario_by_run: Dict[str, Dict[str, Any]] = {}
    for run_id, bundle in raw_runs.items():
        all_rows.extend(bundle["telemetry"])
        scenario_by_run[run_id] = bundle["scenario"]

    window_type = cfg.get("window_type")
    windows: List[Dict[str, Any]] = []

    if window_type == "fixed_sliding_time_window":
        windows = _build_fixed_windows(
            all_rows,
            cfg.get("window_length_seconds", 5.0),
            cfg.get("window_stride_seconds", 1.0),
        )
    elif window_type == "event_centered_window":
        # build per run using event metadata
        for run_id, bundle in raw_runs.items():
            rows = bundle["telemetry"]
            scenario = bundle["scenario"]
            windows.extend(
                _build_event_centered_windows(
                    rows,
                    scenario,
                    cfg.get("pre_event_duration_seconds", 10.0),
                    cfg.get("post_event_duration_seconds", 10.0),
                    "eavesdrop",
                )
            )
    else:
        windows = []

    label_mode = cfg.get("label_mode")
    if label_mode == "binary_attack_vs_clean":
        windows = _label_windows_binary_attack(
            windows, scenario_by_run, cfg.get("attack_coverage_threshold", 0.3)
        )
    elif label_mode == "binary_eavesdrop_vs_clean":
        windows = _label_windows_binary_eavesdrop(windows, scenario_by_run)
    elif label_mode == "multiclass_by_attack_type":
        windows = _label_windows_multiclass(windows, scenario_by_run)

    # deterministic run-based split: map windows to run_id
    proportions = cfg.get("split_proportions", {"train": 0.6, "val": 0.2, "test": 0.2})
    split_ids = _split_indices_run_based(sorted(raw_runs.keys()), proportions, cfg.get("random_seed", 42))

    train_count = 0
    val_count = 0
    test_count = 0

    for w in windows:
        run_id = w["run_id"]
        if run_id in split_ids["train"]:
            train_count += 1
        elif run_id in split_ids["val"]:
            val_count += 1
        else:
            test_count += 1

    return {
        "run_id": f"{workload_id}_treatment",
        "success": True,
        "num_samples_train": train_count,
        "num_samples_val": val_count,
        "num_samples_test": test_count,
    }
