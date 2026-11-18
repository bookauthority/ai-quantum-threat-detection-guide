from __future__ import annotations

import math
import random
from typing import Dict, List, Any, Tuple


def _generate_run(run_id: str, seed: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Generate synthetic telemetry rows and scenario metadata for a single run.

    The generation is deterministic given run_id and seed.
    """

    rng = random.Random(seed)
    num_links = 2
    # 200 seconds, 1 Hz sampling
    duration = 200
    rows: List[Dict[str, Any]] = []
    attack_intervals: List[Dict[str, Any]] = []

    for link_idx in range(num_links):
        link_id = f"link_{link_idx}"
        # Decide attack pattern for this link
        attack_mode = rng.choice(["clean", "eavesdrop", "jamming", "misconfig"])
        has_attack = attack_mode != "clean"
        if has_attack:
            start = rng.randint(40, 120)
            end = start + rng.randint(20, 50)
            end = min(end, duration - 1)
            attack_intervals.append(
                {
                    "link_id": link_id,
                    "attack_type": attack_mode,
                    "start": float(start),
                    "end": float(end),
                }
            )
        for t in range(duration):
            base_qber = 0.02 + 0.01 * math.sin(2 * math.pi * t / 60.0)
            base_key_rate = 1.0 + 0.2 * math.cos(2 * math.pi * t / 30.0)
            base_loss = 3.0 + 0.5 * math.sin(2 * math.pi * t / 45.0)
            base_if_util = 0.3 + 0.1 * math.sin(2 * math.pi * t / 50.0)
            base_pkt_drop = 0.01 + 0.005 * math.cos(2 * math.pi * t / 40.0)
            base_jitter = 2.0 + 0.5 * math.sin(2 * math.pi * t / 30.0)
            base_cpu = 0.4 + 0.1 * math.sin(2 * math.pi * t / 80.0)
            base_mem = 0.5 + 0.1 * math.cos(2 * math.pi * t / 90.0)

            attack_flag = False
            attack_type = "clean"
            quantum_alarm = 0
            if has_attack and start <= t <= end:
                attack_flag = True
                attack_type = attack_mode
                # Distort metrics depending on attack
                if attack_mode == "eavesdrop":
                    base_qber += 0.1
                    base_key_rate -= 0.3
                    quantum_alarm = 1
                elif attack_mode == "jamming":
                    base_loss += 2.0
                    base_qber += 0.05
                    base_pkt_drop += 0.05
                    quantum_alarm = 1
                elif attack_mode == "misconfig":
                    base_key_rate -= 0.5
                    base_if_util -= 0.1
                    quantum_alarm = 1

            # add small random noise
            qber = max(0.0, base_qber + rng.uniform(-0.005, 0.005))
            key_rate = max(0.0, base_key_rate + rng.uniform(-0.05, 0.05))
            loss_db = max(0.0, base_loss + rng.uniform(-0.1, 0.1))
            if_util = max(0.0, min(1.0, base_if_util + rng.uniform(-0.05, 0.05)))
            pkt_drop = max(0.0, base_pkt_drop + rng.uniform(-0.005, 0.005))
            jitter = max(0.0, base_jitter + rng.uniform(-0.2, 0.2))
            cpu_load = max(0.0, min(1.0, base_cpu + rng.uniform(-0.05, 0.05)))
            mem_util = max(0.0, min(1.0, base_mem + rng.uniform(-0.05, 0.05)))

            rows.append(
                {
                    "run_id": run_id,
                    "link_id": link_id,
                    "timestamp": float(t),
                    "qber": qber,
                    "key_rate": key_rate,
                    "loss_db": loss_db,
                    "if_util": if_util,
                    "pkt_drop_rate": pkt_drop,
                    "jitter": jitter,
                    "cpu_load": cpu_load,
                    "mem_util": mem_util,
                    "quantum_alarm": quantum_alarm,
                    "attack_flag": attack_flag,
                    "attack_type": attack_type,
                }
            )

    scenario_meta: Dict[str, Any] = {
        "run_id": run_id,
        "attack_intervals": attack_intervals,
    }

    return rows, scenario_meta


def generate_all_runs() -> Dict[str, Dict[str, Any]]:
    """Generate a small set of synthetic runs shared by baseline and treatment.

    Returns a dict keyed by run_id with keys:
      - "telemetry": list of row dicts
      - "scenario": scenario metadata dict
    """

    base_seed = 12345
    runs: Dict[str, Dict[str, Any]] = {}
    # Generate 5 synthetic runs
    for idx in range(5):
        run_id = f"run_{idx}"
        rows, scenario = _generate_run(run_id, base_seed + idx)
        runs[run_id] = {"telemetry": rows, "scenario": scenario}
    return runs
