from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Literal, Tuple


Variant = Literal["baseline", "treatment"]


@dataclass
class TelemetryPoint:
    time_min: int
    channel_id: str
    qber: float
    key_rate: float
    is_attack: bool
    attack_type: str  # e.g. intercept_resend, jamming, misconfiguration, benign


@dataclass
class Alert:
    timestamp_min: int
    channel_id: str
    alert_id: str
    model_score: float
    sim_attack_type: str
    severity: str  # low/medium/high/critical or "na" for baseline


@dataclass
class Incident:
    incident_id: str
    variant: Variant
    workload_id: str
    channel_ids: List[str]
    start_min: int
    end_min: int
    alerts: List[Alert]


# ---------------------------------------------------------------------------
# Telemetry generation utilities
# ---------------------------------------------------------------------------


def generate_telemetry(
    seed: int,
    workload_id: str,
    channels: List[str],
    total_minutes: int,
) -> List[TelemetryPoint]:
    """Generate deterministic synthetic telemetry for all workloads.

    This is a simplified stand-in for the Chapter 6 simulator and Chapter 10
    detection pipeline inputs. The patterns are chosen to loosely align with
    the incident scenarios described in the specification.
    """

    rng = random.Random(seed)
    telemetry: List[TelemetryPoint] = []

    # Defaults – mostly benign
    for t in range(total_minutes):
        for ch in channels:
            base_qber = 0.01 + 0.01 * rng.random()
            base_key_rate = 1.0 + 0.2 * rng.random()
            telemetry.append(
                TelemetryPoint(
                    time_min=t,
                    channel_id=ch,
                    qber=base_qber,
                    key_rate=base_key_rate,
                    is_attack=False,
                    attack_type="benign",
                )
            )

    # Now overlay specific scenario-like patterns for channels
    # Eavesdropping on channel_1 between 30 and 90 minutes
    for tp in telemetry:
        if tp.channel_id == "channel_1" and 30 <= tp.time_min <= 90:
            tp.qber = 0.12 + 0.03 * rng.random()
            tp.key_rate = max(0.5, tp.key_rate - 0.3 * rng.random())
            tp.is_attack = True
            tp.attack_type = "intercept_resend"

    # Jamming burst on channels 2 and 3 between 120 and 135 minutes
    for tp in telemetry:
        if tp.channel_id in {"channel_2", "channel_3"} and 120 <= tp.time_min <= 135:
            tp.qber = 0.2 + 0.1 * rng.random()
            tp.key_rate = max(0.1, tp.key_rate - 0.7 * rng.random())
            tp.is_attack = True
            tp.attack_type = "jamming"

    # Maintenance on channel_4 between 150 and 180 minutes: noisy but benign
    for tp in telemetry:
        if tp.channel_id == "channel_4" and 150 <= tp.time_min <= 180:
            tp.qber = 0.08 + 0.05 * rng.random()
            tp.key_rate = max(0.3, tp.key_rate - 0.4 * rng.random())
            # Mark as non-attack maintenance
            tp.is_attack = False
            tp.attack_type = "maintenance"

    return telemetry


# ---------------------------------------------------------------------------
# Alert generation
# ---------------------------------------------------------------------------


def _compute_model_score(tp: TelemetryPoint) -> float:
    """Simple heuristic model score based on QBER and key rate.

    Higher QBER and lower key rate imply higher anomaly scores.
    """

    # Normalize qber (assuming 0-0.25) and key rate (0-1.5) into [0,1]
    qber_score = min(1.0, max(0.0, tp.qber / 0.25))
    key_rate_score = 1.0 - min(1.0, max(0.0, tp.key_rate / 1.5))
    base_score = 0.6 * qber_score + 0.4 * key_rate_score
    # Slight boost if attack is simulated
    if tp.is_attack:
        base_score = min(1.0, base_score + 0.15)
    return base_score


def _severity_from_score(score: float) -> str:
    if score < 0.3:
        return "low"
    if score < 0.55:
        return "medium"
    if score < 0.8:
        return "high"
    return "critical"


def generate_alerts(
    telemetry: List[TelemetryPoint],
    variant: Variant,
    score_threshold: float,
    seed: int,
    workload_id: str,
) -> List[Alert]:
    """Generate alerts for either baseline or treatment.

    Baseline vs treatment differences:
    - Baseline uses a single threshold and marks severity as "na".
    - Treatment uses the same threshold for alert emission but also computes
      a SOC-style severity level.
    """

    rng = random.Random(seed)
    alerts: List[Alert] = []

    for idx, tp in enumerate(telemetry):
        score = _compute_model_score(tp)
        if score < score_threshold:
            continue

        # Some small randomized jitter in timestamp within the minute (not
        # affecting integer-minute resolution used by metrics).
        timestamp_min = tp.time_min
        alert_id = f"{workload_id}-{variant}-{tp.channel_id}-{idx}"

        if variant == "baseline":
            severity = "na"
            sim_attack_type = "unknown"
        else:
            severity = _severity_from_score(score)
            sim_attack_type = tp.attack_type

        # Add a small chance for spurious alerts around borderline scores
        if score_threshold <= score < score_threshold + 0.05:
            if rng.random() < 0.3:
                score += 0.02

        alerts.append(
            Alert(
                timestamp_min=timestamp_min,
                channel_id=tp.channel_id,
                alert_id=alert_id,
                model_score=score,
                sim_attack_type=sim_attack_type,
                severity=severity,
            )
        )

    return alerts


# ---------------------------------------------------------------------------
# Incident grouping and analyst triage simulation
# ---------------------------------------------------------------------------


def group_alerts_into_incidents(
    alerts: List[Alert],
    variant: Variant,
    workload_id: str,
) -> List[Incident]:
    """Group alerts into incidents.

    - Baseline: naive grouping – any alerts within a 15-minute rolling window
      per channel become a single incident.
    - Treatment: more structured grouping by attack type and severity threshold
      (medium or above) across correlated channels.
    """

    incidents: List[Incident] = []

    if not alerts:
        return incidents

    # Sort by time
    alerts_sorted = sorted(alerts, key=lambda a: (a.timestamp_min, a.channel_id))

    if variant == "baseline":
        window = 15
        current_incident_alerts: List[Alert] = []
        current_start = alerts_sorted[0].timestamp_min
        current_channels: List[str] = []

        for alert in alerts_sorted:
            if alert.timestamp_min - current_start > window:
                # Close previous incident
                if current_incident_alerts:
                    incident_id = f"{workload_id}-baseline-{len(incidents)}"
                    end_min = (
                        current_incident_alerts[-1].timestamp_min
                        if current_incident_alerts
                        else current_start
                    )
                    incidents.append(
                        Incident(
                            incident_id=incident_id,
                            variant=variant,
                            workload_id=workload_id,
                            channel_ids=sorted(set(current_channels)),
                            start_min=current_start,
                            end_min=end_min,
                            alerts=list(current_incident_alerts),
                        )
                    )
                current_incident_alerts = [alert]
                current_start = alert.timestamp_min
                current_channels = [alert.channel_id]
            else:
                current_incident_alerts.append(alert)
                current_channels.append(alert.channel_id)

        if current_incident_alerts:
            incident_id = f"{workload_id}-baseline-{len(incidents)}"
            end_min = (
                current_incident_alerts[-1].timestamp_min
                if current_incident_alerts
                else current_start
            )
            incidents.append(
                Incident(
                    incident_id=incident_id,
                    variant=variant,
                    workload_id=workload_id,
                    channel_ids=sorted(set(current_channels)),
                    start_min=current_start,
                    end_min=end_min,
                    alerts=list(current_incident_alerts),
                )
            )
    else:
        # Treatment: group by (attack type, severity category) and proximity
        window = 20
        # Bucket by (sim_attack_type, severity)
        buckets: Dict[Tuple[str, str], List[Alert]] = {}
        for alert in alerts_sorted:
            key = (alert.sim_attack_type, alert.severity)
            buckets.setdefault(key, []).append(alert)

        for key, bucket_alerts in buckets.items():
            if not bucket_alerts:
                continue
            bucket_alerts.sort(key=lambda a: (a.timestamp_min, a.channel_id))
            current_incident_alerts: List[Alert] = []
            current_start = bucket_alerts[0].timestamp_min
            current_channels: List[str] = []

            for alert in bucket_alerts:
                if alert.timestamp_min - current_start > window:
                    if current_incident_alerts:
                        incident_id = (
                            f"{workload_id}-treatment-{key[0]}-{key[1]}-"
                            f"{len(incidents)}"
                        )
                        end_min = (
                            current_incident_alerts[-1].timestamp_min
                            if current_incident_alerts
                            else current_start
                        )
                        incidents.append(
                            Incident(
                                incident_id=incident_id,
                                variant=variant,
                                workload_id=workload_id,
                                channel_ids=sorted(set(current_channels)),
                                start_min=current_start,
                                end_min=end_min,
                                alerts=list(current_incident_alerts),
                            )
                        )
                    current_incident_alerts = [alert]
                    current_start = alert.timestamp_min
                    current_channels = [alert.channel_id]
                else:
                    current_incident_alerts.append(alert)
                    current_channels.append(alert.channel_id)

            if current_incident_alerts:
                incident_id = (
                    f"{workload_id}-treatment-{key[0]}-{key[1]}-{len(incidents)}"
                )
                end_min = (
                    current_incident_alerts[-1].timestamp_min
                    if current_incident_alerts
                    else current_start
                )
                incidents.append(
                    Incident(
                        incident_id=incident_id,
                        variant=variant,
                        workload_id=workload_id,
                        channel_ids=sorted(set(current_channels)),
                        start_min=current_start,
                        end_min=end_min,
                        alerts=list(current_incident_alerts),
                    )
                )

    return incidents


def simulate_analyst_triage(
    incidents: List[Incident],
    variant: Variant,
) -> Dict[str, bool]:
    """Simulate analyst triage outcome per incident.

    Returns a mapping incident_id -> success flag (resolved or not).

    The treatment variant has slightly better triage success heuristics,
    but we do not encode that difference into numeric metrics to avoid
    fabricating MTTR-like measurements that require real timing data.
    """

    outcomes: Dict[str, bool] = {}
    for inc in incidents:
        if not inc.alerts:
            outcomes[inc.incident_id] = False
            continue
        # Simple rule: if any alert has severity high/critical (or model_score
        # above a threshold in baseline), mark as resolved.
        if variant == "baseline":
            score_max = max(a.model_score for a in inc.alerts)
            outcomes[inc.incident_id] = score_max >= 0.7
        else:
            any_severe = any(a.severity in {"high", "critical"} for a in inc.alerts)
            outcomes[inc.incident_id] = any_severe
    return outcomes


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------


def compute_alert_volume_rate(
    alerts: List[Alert], total_minutes: int
) -> float:
    if total_minutes <= 0:
        return 0.0
    return float(len(alerts)) / float(total_minutes)


# ---------------------------------------------------------------------------
# Workload runners – each returns a list of evidence run dicts
# ---------------------------------------------------------------------------


def _run_single(
    workload_id: str,
    variant: Variant,
    run_id: str,
    seed: int,
    total_minutes: int,
) -> Dict:
    """Execute a single synthetic run and return an evidence run dict.

    This function is shared by workloads that have similar structure but
    may interpret scenarios differently.
    """

    channels = [f"channel_{i}" for i in range(1, 6)]
    telemetry = generate_telemetry(seed=seed, workload_id=workload_id, channels=channels, total_minutes=total_minutes)

    alerts = generate_alerts(
        telemetry=telemetry,
        variant=variant,
        score_threshold=0.35,
        seed=seed + 17,
        workload_id=workload_id,
    )

    incidents = group_alerts_into_incidents(alerts, variant=variant, workload_id=workload_id)
    outcomes = simulate_analyst_triage(incidents, variant=variant)

    # Compute at least one numeric metric – alert_volume_rate – directly.
    alert_volume_rate = compute_alert_volume_rate(alerts, total_minutes=total_minutes)

    # For this sandbox, success is defined as: at least one incident resolved
    success_flag = any(outcomes.values()) if outcomes else False

    run_record = {
        "variant": variant,
        "workload_id": workload_id,
        "run_id": run_id,
        "success": bool(success_flag),
        "metrics": {
            # Numeric metric required by contract; others intentionally omitted
            # because they cannot be measured faithfully in this offline sandbox.
            "alert_volume_rate": float(alert_volume_rate),
        },
        # Non-metric diagnostic information is allowed here
        "diagnostics": {
            "total_alerts": len(alerts),
            "total_incidents": len(incidents),
            "resolved_incidents": int(sum(1 for v in outcomes.values() if v)),
        },
    }
    return run_record


def run_workload_w1(
    variant: Variant,
    run_id_prefix: str,
    base_seed: int,
) -> List[Dict]:
    """Workload W1 – simulated quantum attack campaigns.

    For simplicity we run exactly one run per variant here, but the structure
    allows easy extension to multiple runs.
    """

    workload_id = "W1-simulated-quantum-attack-campaigns"
    total_minutes = 240
    run_id = f"{run_id_prefix}001"
    run_seed = base_seed + 1
    run_record = _run_single(
        workload_id=workload_id,
        variant=variant,
        run_id=run_id,
        seed=run_seed,
        total_minutes=total_minutes,
    )
    return [run_record]


def run_workload_w2(
    variant: Variant,
    run_id_prefix: str,
    base_seed: int,
) -> List[Dict]:
    """Workload W2 – simulated incident drills.

    We still rely on the same telemetry generator, which embeds incident-like
    structures consistent with the described scenarios, but we do not compute
    scenario-level metrics in this minimal sandbox.
    """

    workload_id = "W2-simulated-incident-drills"
    total_minutes = 240
    run_id = f"{run_id_prefix}001"
    run_seed = base_seed + 2
    run_record = _run_single(
        workload_id=workload_id,
        variant=variant,
        run_id=run_id,
        seed=run_seed,
        total_minutes=total_minutes,
    )
    return [run_record]


def run_workload_w3(
    variant: Variant,
    run_id_prefix: str,
    base_seed: int,
) -> List[Dict]:
    """Workload W3 – analyst triage simulation.

    This shares the same underlying synthetic environment, but is conceptually
    focused on analyst behavior. Here we only track the alert volume rate as a
    numerical metric; additional behavioral metrics would require richer
    interactive simulations.
    """

    workload_id = "W3-analyst-triage-simulation"
    total_minutes = 60
    run_id = f"{run_id_prefix}001"
    run_seed = base_seed + 3
    run_record = _run_single(
        workload_id=workload_id,
        variant=variant,
        run_id=run_id,
        seed=run_seed,
        total_minutes=total_minutes,
    )
    return [run_record]
