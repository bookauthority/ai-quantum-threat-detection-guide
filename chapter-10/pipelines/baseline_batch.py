from __future__ import annotations

from typing import Dict, List

from .common import (
    SimulationData,
    WorkloadConfig,
    build_windows,
    is_attack_time,
    median,
    percentile,
    window_events,
    window_features,
)
from models.simple_model import score_window


def run_baseline_pipeline(
    workload: WorkloadConfig,
    simulation: SimulationData,
    model_threshold: float,
) -> Dict[str, float]:
    """Run a batch-style pipeline over the entire telemetry log.

    Returns a dict of numeric metrics. All metrics are computed based on
    simulator time and counts; no wall-clock measurements are fabricated.
    """

    events = simulation.events
    attacks = simulation.attacks

    windows_by_link = build_windows(events)

    latencies_ms: List[float] = []
    alerts = 0
    total_windows = 0

    for link_id, windows in windows_by_link.items():
        # Pre-filter events once per link for efficiency
        link_events = [e for e in events if e.link_id == link_id]

        for w_start, w_end in windows:
            wevs = window_events(link_events, w_start, w_end)
            feats = window_features(wevs)
            score = score_window(feats)
            total_windows += 1

            if score >= model_threshold:
                alerts += 1
                # For latency we use the window end as alert time and the
                # window start as event time. This is a simplification but is
                # consistent across pipelines.
                latency_ms = (w_end - w_start) * 1000.0
                latencies_ms.append(latency_ms)

    median_latency = median(latencies_ms)
    p95_latency = percentile(latencies_ms, 95.0)

    metrics: Dict[str, float] = {
        "windows_processed": float(total_windows),
        "alerts_emitted": float(alerts),
        "median_latency_ms": float(median_latency),
        "p95_latency_ms": float(p95_latency),
        "events_processed": float(len(events)),
    }

    # Simple approximation of false positive rate:
    # count alerts in windows whose center is outside any attack interval.
    fp_alerts = 0
    for link_id, windows in windows_by_link.items():
        link_events = [e for e in events if e.link_id == link_id]
        for w_start, w_end in windows:
            wevs = window_events(link_events, w_start, w_end)
            if not wevs:
                continue
            feats = window_features(wevs)
            score = score_window(feats)
            if score >= model_threshold:
                center = 0.5 * (w_start + w_end)
                if not is_attack_time(attacks, link_id, center):
                    fp_alerts += 1

    # Duration in hours in simulator time
    duration_hours = float(workload.duration_seconds) / 3600.0 if workload.duration_seconds > 0 else 0.0
    if duration_hours > 0.0:
        fp_rate_per_hour = fp_alerts / duration_hours
    else:
        fp_rate_per_hour = 0.0

    metrics["false_positive_rate_per_hour"] = float(fp_rate_per_hour)

    return metrics
