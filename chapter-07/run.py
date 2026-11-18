import json
import os
import platform
from typing import Any, Dict, List

from experiment.config import EXPERIMENT_ID, WORKLOAD_CONFIGS
from experiment.data_gen import generate_all_runs
from experiment.pipelines import run_baseline_pipeline, run_treatment_pipeline


def main() -> None:
    # Determine evidence output directory
    evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    evidence_path = os.path.join(evidence_dir, "results.json")

    # Generate deterministic synthetic raw data to be shared across all workloads
    raw_runs = generate_all_runs()

    runs_records: List[Dict[str, Any]] = []

    for workload_id, cfg in WORKLOAD_CONFIGS.items():
        # Baseline run
        baseline_result = run_baseline_pipeline(workload_id, cfg, raw_runs)
        runs_records.append(
            {
                "variant": "baseline",
                "workload_id": workload_id,
                "run_id": baseline_result["run_id"],
                "success": bool(baseline_result["success"]),
                "metrics": {
                    # metrics values must be numbers only
                    "num_samples_train": float(baseline_result["num_samples_train"]),
                    "num_samples_val": float(baseline_result["num_samples_val"]),
                    "num_samples_test": float(baseline_result["num_samples_test"]),
                },
            }
        )

        # Treatment run
        treatment_result = run_treatment_pipeline(workload_id, cfg, raw_runs)
        runs_records.append(
            {
                "variant": "treatment",
                "workload_id": workload_id,
                "run_id": treatment_result["run_id"],
                "success": bool(treatment_result["success"]),
                "metrics": {
                    "num_samples_train": float(treatment_result["num_samples_train"]),
                    "num_samples_val": float(treatment_result["num_samples_val"]),
                    "num_samples_test": float(treatment_result["num_samples_test"]),
                },
            }
        )

    evidence: Dict[str, Any] = {
        "chapter": 7,
        "experiment_id": EXPERIMENT_ID,
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
        },
        "runs": runs_records,
        "notes": "Synthetic, deterministic experiment for Chapter 7 baseline vs treatment dataset construction. Metrics are sample counts only.",
    }

    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
