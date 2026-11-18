import json
import os
import unittest


class TestExperimentEvidence(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure evidence directory exists
        self.evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
        os.makedirs(self.evidence_dir, exist_ok=True)

        # Run the experiment once if results.json is missing
        self.results_path = os.path.join(self.evidence_dir, "results.json")
        if not os.path.exists(self.results_path):
            import run as run_module

            run_module.main()

        with open(self.results_path, "r", encoding="utf-8") as f:
            self.evidence = json.load(f)

    def test_top_level_schema(self) -> None:
        ev = self.evidence
        self.assertIn("chapter", ev)
        self.assertIsInstance(ev["chapter"], int)

        self.assertIn("experiment_id", ev)
        self.assertIsInstance(ev["experiment_id"], str)

        self.assertIn("environment", ev)
        self.assertIsInstance(ev["environment"], dict)
        self.assertIn("os", ev["environment"])
        self.assertIn("python", ev["environment"])

        self.assertIn("runs", ev)
        self.assertIsInstance(ev["runs"], list)

    def test_runs_schema_and_metrics(self) -> None:
        runs = self.evidence["runs"]
        self.assertGreaterEqual(len(runs), 4)

        variants = set()
        workloads = set()

        for run in runs:
            self.assertIn("variant", run)
            self.assertIn(run["variant"], ("baseline", "treatment"))
            self.assertIn("workload_id", run)
            self.assertIsInstance(run["workload_id"], str)
            self.assertIn("run_id", run)
            self.assertIsInstance(run["run_id"], str)
            self.assertIn("success", run)
            self.assertIsInstance(run["success"], bool)
            self.assertIn("metrics", run)
            self.assertIsInstance(run["metrics"], dict)

            variants.add((run["variant"], run["workload_id"]))

            # All metric values must be finite numbers
            for key, value in run["metrics"].items():
                self.assertIsInstance(
                    value,
                    (int, float),
                    msg=f"Metric {key} must be numeric, got {type(value)}",
                )

        expected_pairs = {
            ("baseline", "wl-quantum-telemetry-per-record"),
            ("treatment", "wl-quantum-telemetry-per-record"),
            ("baseline", "wl-quantum-telemetry-windowed"),
            ("treatment", "wl-quantum-telemetry-windowed"),
        }
        self.assertTrue(
            expected_pairs.issubset(variants),
            msg=f"Missing some required variant/workload pairs: {expected_pairs - variants}",
        )


if __name__ == "__main__":
    unittest.main()
