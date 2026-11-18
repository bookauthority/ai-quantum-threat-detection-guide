from __future__ import annotations

from typing import Dict


def score_window(features: Dict[str, float]) -> float:
    """Deterministic anomaly score based on simple heuristics.

    The score increases when:
      - mean_qber is high
      - mean_key_rate is low

    Score range is roughly [0, 1+], but we do not enforce a strict bound.
    """

    count = float(features.get("count", 0.0))
    mean_key_rate = float(features.get("mean_key_rate", 0.0))
    mean_qber = float(features.get("mean_qber", 0.0))

    if count <= 0.0:
        return 0.0

    # Normalize qber and key_rate against expected nominal values
    qber_component = max(0.0, mean_qber - 0.02) * 10.0
    key_component = max(0.0, 1.0 - mean_key_rate)

    score = qber_component + key_component
    return float(score)
