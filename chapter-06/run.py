import json
import os
import sys
import platform
from typing import Any, Dict, List

from quantum_sim.workloads import (
    get_all_workloads,
)
from quantum_sim.baseline import run_baseline_workload
from quantum_sim.treatment import run_treatment_workload
from quantum_sim.metrics import compute_basic_metrics


EXPERIMENT_ID = "exp-ch06-quantum-net-sim-env-v1"
CHAPTER = 6


def get_environment_info() -> Dict[str, str]:
    return {
        "os": platform.platform(),
        "python": sys.version.replace("\n", " "),
    }


def main() -> None:
    evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    runs: List[Dict[str, Any]] = []

    workloads = get_all_workloads()

    for workload in workloads:
        workload_id = workload["name"]

        # Baseline variant (if supported by this workload)
        if workload["simulator_variant_baseline_supported"]:
            try:
                baseline_telemetry = run_baseline_workload(workload)
                baseline_metrics = compute_basic_metrics(baseline_telemetry)
                runs.append(
                    {
                        "variant": "baseline",
                        "workload_id": workload_id,
                        "run_id": f"{workload_id}_baseline",
                        "success": True,
                        "metrics": baseline_metrics,
                        "notes": "baseline run completed",
                    }
                )
            except Exception as exc:  # pragma: no cover - defensive
                runs.append(
                    {
                        "variant": "baseline",
                        "workload_id": workload_id,
                        "run_id": f"{workload_id}_baseline_error",
                        "success": False,
                        "metrics": {"num_steps": 0.0},
                        "notes": f"baseline run failed: {exc}",
                    }
                )

        # Treatment variant
        try:
            treatment_telemetry = run_treatment_workload(workload)
            treatment_metrics = compute_basic_metrics(treatment_telemetry)
            runs.append(
                {
                    "variant": "treatment",
                    "workload_id": workload_id,
                    "run_id": f"{workload_id}_treatment",
                    "success": True,
                    "metrics": treatment_metrics,
                    "notes": "treatment run completed",
                }
            )
        except Exception as exc:  # pragma: no cover - defensive
            runs.append(
                {
                    "variant": "treatment",
                    "workload_id": workload_id,
                    "run_id": f"{workload_id}_treatment_error",
                    "success": False,
                    "metrics": {"num_steps": 0.0},
                    "notes": f"treatment run failed: {exc}",
                }
            )

    evidence: Dict[str, Any] = {
        "chapter": CHAPTER,
        "experiment_id": EXPERIMENT_ID,
        "environment": get_environment_info(),
        "runs": runs,
        "notes": "All workloads executed in a lightweight offline sandbox; metrics are basic but derived from actual simulated telemetry.",
    }

    out_path = os.path.join(evidence_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)


if __name__ == "__main__":
    main()
