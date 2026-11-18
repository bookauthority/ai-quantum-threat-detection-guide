from typing import Any, Dict, List


def compute_basic_metrics(telemetry: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute a small set of numeric metrics from telemetry.

    Metrics are deliberately simple to keep them cheap and deterministic:

    - num_steps (float)
    - mean_qber_benign (float)
    - mean_qber_attack (float)
    """

    n = float(len(telemetry))
    if n == 0:
        return {"num_steps": 0.0, "mean_qber_benign": 0.0, "mean_qber_attack": 0.0}

    benign_qber_sum = 0.0
    benign_count = 0.0
    attack_qber_sum = 0.0
    attack_count = 0.0

    for row in telemetry:
        qber = float(row.get("qber", 0.0))
        scenario_type = row.get("scenario_type", "benign")
        if scenario_type == "attack":
            attack_qber_sum += qber
            attack_count += 1.0
        else:
            benign_qber_sum += qber
            benign_count += 1.0

    mean_qber_benign = benign_qber_sum / benign_count if benign_count > 0 else 0.0
    mean_qber_attack = attack_qber_sum / attack_count if attack_count > 0 else 0.0

    return {
        "num_steps": float(len(telemetry)),
        "mean_qber_benign": float(mean_qber_benign),
        "mean_qber_attack": float(mean_qber_attack),
    }
