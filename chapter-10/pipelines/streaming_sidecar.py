from __future__ import annotations

from typing import Dict, List, Tuple

from .common import (
    SimulationData,
    WorkloadConfig,
    WINDOW_SIZE,
    WINDOW_STEP,
    is_attack_time,
    mean,
    median,
)
from models.simple_model import score_window


def _build_streaming_windows(events) -> Dict[str, List[Tuple[float, float]]]:
    """Build the same logical windows as in the batch pipeline.

    We recompute instead of importing to keep this module self-contained
    and to emphasize the shared window definition.
    """

    by_link: Dict[str, List] = {}
    for ev in events:
        by_link.setdefault(ev.link_id, []).append(ev)

    windows_by_link: Dict[str, List[Tuple[float, float]]] = {}
    for link_id, lev in by_link.items():
        if not lev:
            windows_by_link[link_id] = []
            continue
        start_time = lev[0].sim_time
        end_time = lev[-1].sim_time
        w_start = start_time
        link_windows: List[Tuple[float, float]] = []
        while w_start < end_time:
            w_end = w_start + WINDOW_SIZE
            link_windows.append((w_start, w_end))
            w_start += WINDOW_STEP
        windows_by_link[link_id] = link_windows

    return windows_by_link


class SidecarModelServer:
    """In-process mock of a sidecar model server.

    It exposes a method that would correspond to a network RPC in a real
    deployment. We keep it simple and deterministic.
    """

    def __init__(self, threshold: float) -> None:
        self.threshold = float(threshold)
        self.requests_handled = 0

    def score(self, features: Dict[str, float]) -> float:
        self.requests_handled += 1
        return score_window(features)


def run_treatment_pipeline(
    workload: WorkloadConfig,
    simulation: SimulationData,
    model_threshold: float,
) -> Dict[str, float]:
    """Run a streaming-style pipeline with an in-process sidecar model server.

    The event stream is the same as the batch input but processed in time
    order. We maintain per-link sliding windows and call the sidecar for each
    window.
    """

    events = simulation.events
    attacks = simulation.attacks

    sidecar = SidecarModelServer(threshold=model_threshold)

    # Precompute logical windows (treatment uses same scheme as baseline)
    windows_by_link = _build_streaming_windows(events)

    # Per-link buffers of (time, key_rate, qber)
    buffers: Dict[str, List[Tuple[float, float, float]]] = {link_id: [] for link_id in windows_by_link}

    alerts = 0
    latencies_ms: List[float] = []
    total_windows = 0

    # For WL3, simulate a sidecar restart by skipping scoring for windows
    # in a small interval in the middle of the run.
    simulate_restart = workload.bursty
    restart_start = float(workload.duration_seconds) * 0.45 if simulate_restart else None
    restart_end = float(workload.duration_seconds) * 0.5 if simulate_restart else None

    # Iterate events in time order, updating buffers and checking for
    # window closures whenever we advance past a window end.
    for ev in events:
        buf = buffers[ev.link_id]
        buf.append((ev.sim_time, ev.key_rate, ev.qber))

        # Drop events that are too old compared to the latest time to
        # limit buffer growth while preserving sliding window coverage.
        cutoff = ev.sim_time - WINDOW_SIZE * 2
        while buf and buf[0][0] < cutoff:
            buf.pop(0)

        # Process any windows for this link that end before or at ev.sim_time
        wlist = windows_by_link.get(ev.link_id, [])
        while wlist and wlist[0][1] <= ev.sim_time:
            w_start, w_end = wlist.pop(0)
            # Collect events in this time window from the buffer
            window_points = [p for p in buf if w_start <= p[0] < w_end]
            if not window_points:
                total_windows += 1
                continue

            count = float(len(window_points))
            mean_key = mean([p[1] for p in window_points])
            mean_qber = mean([p[2] for p in window_points])
            feats = {
                "count": count,
                "mean_key_rate": mean_key,
                "mean_qber": mean_qber,
            }

            total_windows += 1

            # Simulated restart: temporarily unavailable sidecar
            if simulate_restart and restart_start is not None and restart_end is not None:
                if restart_start <= w_end <= restart_end:
                    # Skip scoring; window is effectively dropped
                    continue

            score = sidecar.score(feats)
            if score >= model_threshold:
                alerts += 1
                latency_ms = (w_end - w_start) * 1000.0
                latencies_ms.append(latency_ms)

    median_latency = median(latencies_ms)
    p95_latency = 0.0
    if latencies_ms:
        lat_sorted = sorted(latencies_ms)
        k = int(0.95 * (len(lat_sorted) - 1))
        p95_latency = lat_sorted[k]

    metrics: Dict[str, float] = {
        "windows_processed": float(total_windows),
        "alerts_emitted": float(alerts),
        "median_latency_ms": float(median_latency),
        "p95_latency_ms": float(p95_latency),
        "events_processed": float(len(events)),
        # Throughput is computed as events per simulated second
        "throughput_events_per_second": (
            float(len(events)) / float(workload.duration_seconds)
            if workload.duration_seconds > 0
            else 0.0
        ),
        # Approximate telemetry loss rate: windows skipped due to simulated
        # restart divided by total windows.
    }

    if simulate_restart and restart_start is not None and restart_end is not None:
        # Recompute how many windows fall inside the restart interval
        skipped = 0
        total_for_loss = 0
        for link_id, wlist_all in _build_streaming_windows(events).items():
            for w_start, w_end in wlist_all:
                total_for_loss += 1
                if restart_start <= w_end <= restart_end:
                    skipped += 1
        if total_for_loss > 0:
            telemetry_loss_rate = skipped / float(total_for_loss)
        else:
            telemetry_loss_rate = 0.0
    else:
        telemetry_loss_rate = 0.0

    metrics["telemetry_loss_rate"] = float(telemetry_loss_rate)

    # Simple false positive rate analogous to baseline
    fp_alerts = 0
    for link_id, wlist_all in _build_streaming_windows(events).items():
        for w_start, w_end in wlist_all:
            center = 0.5 * (w_start + w_end)
            # Heuristic: assume that any alert-producing window had
            # similar score behavior here; we cannot reconstruct exactly
            # which windows produced alerts without more bookkeeping,
            # so we approximate by re-scoring.
            window_points = [
                (ev.sim_time, ev.key_rate, ev.qber)
                for ev in events
                if ev.link_id == link_id and w_start <= ev.sim_time < w_end
            ]
            if not window_points:
                continue
            count = float(len(window_points))
            mean_key = mean([p[1] for p in window_points])
            mean_qber = mean([p[2] for p in window_points])
            feats = {
                "count": count,
                "mean_key_rate": mean_key,
                "mean_qber": mean_qber,
            }
            score = score_window(feats)
            if score >= model_threshold and not is_attack_time(attacks, link_id, center):
                fp_alerts += 1

    duration_hours = float(workload.duration_seconds) / 3600.0 if workload.duration_seconds > 0 else 0.0
    if duration_hours > 0.0:
        fp_rate_per_hour = fp_alerts / duration_hours
    else:
        fp_rate_per_hour = 0.0

    metrics["false_positive_rate_per_hour"] = float(fp_rate_per_hour)

    return metrics
