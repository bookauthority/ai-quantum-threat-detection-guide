from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class TelemetryEvent:
    sim_time: float  # seconds since start
    link_id: str
    key_rate: float
    qber: float


@dataclass
class AttackInterval:
    attack_id: str
    workload_id: str
    run_id: str
    attack_type: str
    link_id: str
    start_time: float
    end_time: float
    severity: str


@dataclass
class WorkloadConfig:
    workload_id: str
    duration_seconds: int
    has_attacks: bool
    bursty: bool
    description: str


@dataclass
class SimulationData:
    events: List[TelemetryEvent]
    attacks: List[AttackInterval]


WINDOW_SIZE = 10.0  # seconds
WINDOW_STEP = 5.0   # seconds


def generate_workload(workload: WorkloadConfig, seed: int) -> SimulationData:
    """Generate deterministic synthetic telemetry and attack intervals.

    We simulate 3 links. Each link emits events at a base rate. WL3
    occasionally increases rate to model bursts.
    """

    rng = random.Random(seed)

    link_ids = ["linkA", "linkB", "linkC"]
    base_rate_hz = 5  # events per second per link
    events: List[TelemetryEvent] = []
    attacks: List[AttackInterval] = []

    duration = float(workload.duration_seconds)

    # Define attack intervals per workload
    if workload.has_attacks:
        for li, link_id in enumerate(link_ids):
            midpoint = duration * 0.5
            span = duration * 0.2
            start = midpoint - span / 2.0 + li
            end = min(duration, start + span)
            attacks.append(
                AttackInterval(
                    attack_id=f"atk_{link_id}",
                    workload_id=workload.workload_id,
                    run_id="synthetic",
                    attack_type="intercept_resend" if li == 0 else "jamming",
                    link_id=link_id,
                    start_time=start,
                    end_time=end,
                    severity="medium",
                )
            )

    # Generate events
    t = 0.0
    while t < duration:
        for link_id in link_ids:
            # Bursty behavior for WL3
            rate = base_rate_hz
            if workload.bursty and (duration * 0.3 < t < duration * 0.6):
                rate = base_rate_hz * 4

            # For each discrete second, emit Poisson-like events
            num_events = max(1, int(rng.expovariate(1.0 / rate)))
            for _ in range(num_events):
                # Jitter within this 1-second bucket
                ts = min(duration, t + rng.random())

                # Base signal
                key_rate = rng.normalvariate(1.0, 0.05)
                qber = max(0.0, rng.normalvariate(0.02, 0.005))

                # Apply attack distortion if in interval
                in_attack = False
                for atk in attacks:
                    if atk.link_id == link_id and atk.start_time <= ts <= atk.end_time:
                        in_attack = True
                        break
                if in_attack:
                    # Higher qber, lower key rate
                    qber = max(0.02, qber + rng.uniform(0.05, 0.15))
                    key_rate = max(0.2, key_rate - rng.uniform(0.3, 0.7))

                events.append(
                    TelemetryEvent(
                        sim_time=ts,
                        link_id=link_id,
                        key_rate=key_rate,
                        qber=qber,
                    )
                )
        t += 1.0

    # Sort by simulated time for clarity
    events.sort(key=lambda e: (e.sim_time, e.link_id))

    return SimulationData(events=events, attacks=attacks)


def build_windows(events: List[TelemetryEvent]) -> Dict[str, List[Tuple[float, float]]]:
    """Compute fixed windows per link over the event time range.

    Returns mapping link_id -> list of (window_start, window_end).
    """

    by_link: Dict[str, List[TelemetryEvent]] = {}
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


def window_events(
    events: List[TelemetryEvent],
    window_start: float,
    window_end: float,
) -> List[TelemetryEvent]:
    """Return events whose sim_time lies in [window_start, window_end)."""

    return [e for e in events if window_start <= e.sim_time < window_end]


def window_features(events: List[TelemetryEvent]) -> Dict[str, float]:
    """Compute simple aggregate features for a window of events."""

    if not events:
        return {
            "count": 0.0,
            "mean_key_rate": 0.0,
            "mean_qber": 0.0,
        }

    n = float(len(events))
    sum_key = sum(e.key_rate for e in events)
    sum_qber = sum(e.qber for e in events)

    return {
        "count": n,
        "mean_key_rate": sum_key / n,
        "mean_qber": sum_qber / n,
    }


def is_attack_time(attacks: List[AttackInterval], link_id: str, ts: float) -> bool:
    for atk in attacks:
        if atk.link_id == link_id and atk.start_time <= ts <= atk.end_time:
            return True
    return False


def median(values: List[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    m = len(s) // 2
    if len(s) % 2 == 1:
        return s[m]
    return 0.5 * (s[m - 1] + s[m])


def mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / float(len(values))


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    if p <= 0:
        return min(values)
    if p >= 100:
        return max(values)
    s = sorted(values)
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    d0 = s[f] * (c - k)
    d1 = s[c] * (k - f)
    return d0 + d1
