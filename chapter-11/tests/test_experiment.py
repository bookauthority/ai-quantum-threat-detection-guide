import json
import os
import unittest
from pathlib import Path


class TestExperimentEvidence(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure a clean evidence directory under /evidence
        self.evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
        Path(self.evidence_dir).mkdir(parents=True, exist_ok=True)
        self.results_file = Path(self.evidence_dir) / "results.json"
        if self.results_file.exists():
            self.results_file.unlink()

    def _run_experiment(self) -> None:
        # Import and run the experiment entry point
        import run  # type: ignore

        run.main()

    def test_evidence_schema_and_metrics(self) -> None:
        # Run the experiment
        self._run_experiment()

        # Load evidence JSON
        self.assertTrue(self.results_file.exists(), "results.json was not created")
        with self.results_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Top-level required keys
        self.assertIn("chapter", data)
        self.assertIn("experiment_id", data)
        self.assertIn("environment", data)
        self.assertIn("runs", data)

        # Check chapter and experiment_id
        self.assertEqual(data["chapter"], 11)
        self.assertEqual(data["experiment_id"], "exp-ch11-soc-siem-integration-v1")

        # Environment subfields
        env = data["environment"]
        self.assertIn("os", env)
        self.assertIn("python", env)
        self.assertIsInstance(env["os"], str)
        self.assertIsInstance(env["python"], str)

        runs = data["runs"]
        self.assertIsInstance(runs, list)
        self.assertGreaterEqual(len(runs), 6)  # 3 workloads * 2 variants

        # Track baseline/treatment presence per workload
        workload_variants = {}

        for run in runs:
            # Required run-level keys
            self.assertIn("variant", run)
            self.assertIn("workload_id", run)
            self.assertIn("run_id", run)
            self.assertIn("success", run)
            self.assertIn("metrics", run)

            variant = run["variant"]
            workload_id = run["workload_id"]

            self.assertIn(variant, ["baseline", "treatment"])
            self.assertIsInstance(run["run_id"], str)
            self.assertIsInstance(run["success"], bool)

            # Record presence for per-workload checks
            workload_variants.setdefault(workload_id, set()).add(variant)

            metrics = run["metrics"]
            self.assertIsInstance(metrics, dict)

            # All metric values must be numeric (int or float)
            for key, value in metrics.items():
                self.assertIsInstance(
                    value,
                    (int, float),
                    msg=f"Metric {key} must be numeric, got {type(value)}",
                )

            # alert_volume_rate must exist and be numeric
            self.assertIn("alert_volume_rate", metrics)
            self.assertIsInstance(metrics["alert_volume_rate"], (int, float))

        # Ensure at least one baseline and one treatment run per workload
        expected_workloads = {
            "W1-simulated-quantum-attack-campaigns",
            "W2-simulated-incident-drills",
            "W3-analyst-triage-simulation",
        }
        self.assertTrue(
            expected_workloads.issubset(set(workload_variants.keys())),
            msg="Not all expected workloads are present in evidence runs",
        )
        for workload_id in expected_workloads:
            variants = workload_variants.get(workload_id, set())
            self.assertIn("baseline", variants, msg=f"Missing baseline for {workload_id}")
            self.assertIn("treatment", variants, msg=f"Missing treatment for {workload_id}")


if __name__ == "__main__":
    unittest.main()
