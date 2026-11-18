import json
import os
import unittest


class TestExperimentEvidence(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure evidence directory is isolated for the test
        self.evidence_dir = os.path.abspath("./_test_evidence")
        os.makedirs(self.evidence_dir, exist_ok=True)
        os.environ["BOOKMAS_EVIDENCE_DIR"] = self.evidence_dir

    def tearDown(self) -> None:
        # Clean up evidence directory after tests
        try:
            path = os.path.join(self.evidence_dir, "results.json")
            if os.path.exists(path):
                os.remove(path)
            os.rmdir(self.evidence_dir)
        except OSError:
            # Directory may not be empty or removable; ignore in sandbox
            pass

    def _run_experiment(self):
        import run as experiment_run

        code = experiment_run.main()
        self.assertEqual(code, 0)

    def test_evidence_schema_and_content(self):
        self._run_experiment()
        path = os.path.join(self.evidence_dir, "results.json")
        self.assertTrue(os.path.exists(path), "Evidence file was not created")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Top-level keys
        self.assertIn("chapter", data)
        self.assertIn("experiment_id", data)
        self.assertIn("environment", data)
        self.assertIn("runs", data)

        self.assertEqual(data["chapter"], 9)
        self.assertEqual(
            data["experiment_id"], "exp-09-advanced-temporal-hybrid-modeling"
        )

        # Environment structure
        env = data["environment"]
        self.assertIsInstance(env, dict)
        self.assertIn("os", env)
        self.assertIn("python", env)
        self.assertIsInstance(env["os"], str)
        self.assertIsInstance(env["python"], str)

        runs = data["runs"]
        self.assertIsInstance(runs, list)
        self.assertGreaterEqual(len(runs), 6)  # 3 workloads * (baseline + treatment)

        workloads = {
            "WL-1-SingleLink-Temporal-Attacks": {"baseline": 0, "treatment": 0},
            "WL-2-MultiLink-Topology-Context": {"baseline": 0, "treatment": 0},
            "WL-3-Rare-Attack-Events": {"baseline": 0, "treatment": 0},
        }

        for run in runs:
            # Required fields
            self.assertIn("variant", run)
            self.assertIn("workload_id", run)
            self.assertIn("run_id", run)
            self.assertIn("success", run)
            self.assertIn("metrics", run)

            self.assertIn(run["workload_id"], workloads)
            self.assertIn(run["variant"], ("baseline", "treatment"))
            workloads[run["workload_id"]][run["variant"]] += 1

            # success is boolean
            self.assertIsInstance(run["success"], bool)

            # metrics is dict with numeric values
            metrics = run["metrics"]
            self.assertIsInstance(metrics, dict)
            self.assertGreaterEqual(len(metrics), 1)
            for key, value in metrics.items():
                # keys should be strings and values finite numbers
                self.assertIsInstance(key, str)
                self.assertIsInstance(
                    value, (int, float), f"Metric {key} must be numeric"
                )

        # Ensure at least one baseline and one treatment per workload
        for wid, counts in workloads.items():
            self.assertGreaterEqual(
                counts["baseline"], 1, f"No baseline run for workload {wid}"
            )
            self.assertGreaterEqual(
                counts["treatment"], 1, f"No treatment run for workload {wid}"
            )


if __name__ == "__main__":
    unittest.main()
