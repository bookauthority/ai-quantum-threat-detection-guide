import json
import os
import sys
import platform
from pathlib import Path

from experiment.core import (
    run_workload_w1,
    run_workload_w2,
    run_workload_w3,
)
from experiment.evidence import write_evidence


CHAPTER_NUMBER = 11
EXPERIMENT_ID = "exp-ch11-soc-siem-integration-v1"


def main() -> None:
    # Determine evidence directory
    evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    evidence_path = Path(evidence_dir)
    evidence_path.mkdir(parents=True, exist_ok=True)
    results_file = evidence_path / "results.json"

    # Basic environment info for evidence schema (minimal subset required by contract)
    environment_info = {
        "os": platform.platform(),
        "python": sys.version.split()[0],
    }

    runs = []

    # We run one baseline and one treatment run for each workload.
    # Seeds are fixed for determinism but differ between baseline/treatment and workloads.

    # Workload W1
    runs.extend(
        run_workload_w1(
            variant="baseline",
            run_id_prefix="W1-baseline-",
            base_seed=101,
        )
    )
    runs.extend(
        run_workload_w1(
            variant="treatment",
            run_id_prefix="W1-treatment-",
            base_seed=201,
        )
    )

    # Workload W2
    runs.extend(
        run_workload_w2(
            variant="baseline",
            run_id_prefix="W2-baseline-",
            base_seed=301,
        )
    )
    runs.extend(
        run_workload_w2(
            variant="treatment",
            run_id_prefix="W2-treatment-",
            base_seed=401,
        )
    )

    # Workload W3
    runs.extend(
        run_workload_w3(
            variant="baseline",
            run_id_prefix="W3-baseline-",
            base_seed=501,
        )
    )
    runs.extend(
        run_workload_w3(
            variant="treatment",
            run_id_prefix="W3-treatment-",
            base_seed=601,
        )
    )

    evidence = {
        "chapter": CHAPTER_NUMBER,
        "experiment_id": EXPERIMENT_ID,
        "environment": environment_info,
        "runs": runs,
        "notes": (
            "Offline, self-contained simulation of SOC/SIEM integration. "
            "Metrics are directly measured from deterministic synthetic workloads. "
            "Only a subset of the full experiment metrics is implemented; "
            "here we report alert_volume_rate as a numeric metric for all runs."
        ),
    }

    write_evidence(results_file, evidence)


if __name__ == "__main__":
    main()
