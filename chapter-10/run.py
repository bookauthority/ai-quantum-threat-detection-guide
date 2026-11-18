import json
import os
import sys
import platform
from typing import Dict, List

from pipelines.common import (
    WorkloadConfig,
    generate_workload,
)
from pipelines.baseline_batch import run_baseline_pipeline
from pipelines.streaming_sidecar import run_treatment_pipeline


EXPERIMENT_ID = "exp-ch10-e2e-quantum-aware-detection-pipeline-v1"
CHAPTER_NUMBER = 10


def get_evidence_dir() -> str:
    env_dir = os.getenv("BOOKMAS_EVIDENCE_DIR", "/evidence")
    os.makedirs(env_dir, exist_ok=True)
    return env_dir


def build_workloads() -> List[WorkloadConfig]:
    """Create the three workloads with modest sizes for sandbox execution.

    Durations are kept small to ensure bounded runtime while
    still exercising the logic.
    """

    # Simulated durations in seconds (shortened vs. spec for practicality)
    wl1 = WorkloadConfig(
        workload_id="WL1-normal-traffic",
        duration_seconds=120,
        has_attacks=False,
        bursty=False,
        description="Normal traffic, no attacks",
    )

    wl2 = WorkloadConfig(
        workload_id="WL2-mixed-attacks",
        duration_seconds=120,
        has_attacks=True,
        bursty=False,
        description="Mixed attacks with labeled intervals",
    )

    wl3 = WorkloadConfig(
        workload_id="WL3-burst-and-failure-resilience",
        duration_seconds=120,
        has_attacks=True,
        bursty=True,
        description="Bursts and simulated sidecar restart",
    )

    return [wl1, wl2, wl3]


def run_experiment() -> Dict:
    workloads = build_workloads()

    runs: List[Dict] = []

    # Use a fixed base seed for determinism; each workload increments
    base_seed = 12345

    for idx, wl in enumerate(workloads):
        seed = base_seed + idx
        sim_data = generate_workload(wl, seed=seed)

        # Baseline run
        baseline_run_id = f"baseline_{wl.workload_id}_run1"
        try:
            baseline_metrics = run_baseline_pipeline(
                workload=wl,
                simulation=sim_data,
                model_threshold=0.6,
            )
            baseline_success = True
        except Exception:
            baseline_metrics = {}
            baseline_success = False

        runs.append(
            {
                "variant": "baseline",
                "workload_id": wl.workload_id,
                "run_id": baseline_run_id,
                "success": baseline_success,
                "metrics": baseline_metrics,
            }
        )

        # Treatment run
        treatment_run_id = f"treatment_{wl.workload_id}_run1"
        try:
            treatment_metrics = run_treatment_pipeline(
                workload=wl,
                simulation=sim_data,
                model_threshold=0.6,
            )
            treatment_success = True
        except Exception:
            treatment_metrics = {}
            treatment_success = False

        runs.append(
            {
                "variant": "treatment",
                "workload_id": wl.workload_id,
                "run_id": treatment_run_id,
                "success": treatment_success,
                "metrics": treatment_metrics,
            }
        )

    evidence = {
        "chapter": CHAPTER_NUMBER,
        "experiment_id": EXPERIMENT_ID,
        "environment": {
            "os": os.name,
            "python": platform.python_version(),
        },
        "runs": runs,
        "notes": (
            "Metrics are computed from a deterministic simulation. "
            "Resource utilization metrics are omitted due to sandbox limitations."
        ),
    }

    return evidence


def main() -> None:
    evidence = run_experiment()

    evidence_dir = get_evidence_dir()
    output_path = os.path.join(evidence_dir, "results.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, sort_keys=False)

    # Write path to stdout for debuggability (not part of metrics)
    sys.stdout.write(f"Evidence written to {output_path}\n")


if __name__ == "__main__":
    main()
