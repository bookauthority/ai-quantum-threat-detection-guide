import json
import os
import platform
from typing import Any, Dict, List

from experiment.config import EXPERIMENT_ID, CHAPTER_NUMBER
from experiment.runner import run_all_experiments


def main() -> None:
    evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    results_path = os.path.join(evidence_dir, "results.json")

    runs = run_all_experiments()

    evidence: Dict[str, Any] = {
        "chapter": CHAPTER_NUMBER,
        "experiment_id": EXPERIMENT_ID,
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
        },
        "runs": runs,
        "notes": (
            "Sandboxed, dependency-free implementation using synthetic data and "
            "simple models; metrics are limited to accuracy/precision/recall and "
            "attack rate on small test splits."
        ),
    }

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
