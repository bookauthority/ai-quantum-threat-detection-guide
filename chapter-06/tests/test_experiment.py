import json
import os
import shutil
import tempfile
import types
import unittest

import run as experiment_run


class TestExperimentEvidence(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="evidence_")
        os.environ["BOOKMAS_EVIDENCE_DIR"] = self.tmpdir

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_run_produces_valid_evidence(self) -> None:
        # Run the experiment main function
        experiment_run.main()

        results_path = os.path.join(self.tmpdir, "results.json")
        self.assertTrue(os.path.exists(results_path), "results.json must be created")

        with open(results_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Top-level schema checks
        self.assertIsInstance(data, dict)
        self.assertIn("chapter", data)
        self.assertIn("experiment_id", data)
        self.assertIn("environment", data)
        self.assertIn("runs", data)

        self.assertEqual(data["chapter"], 6)
        self.assertEqual(data["experiment_id"], "exp-ch06-quantum-net-sim-env-v1")

        env = data["environment"]
        self.assertIsInstance(env, dict)
        self.assertIn("os", env)
        self.assertIn("python", env)
        self.assertIsInstance(env["os"], str)
        self.assertIsInstance(env["python"], str)

        runs = data["runs"]
        self.assertIsInstance(runs, list)
        self.assertGreaterEqual(len(runs), 1)

        # Check that every run has required fields and metrics are numeric
        variants_by_workload = {}
        for run in runs:
            self.assertIn("variant", run)
            self.assertIn("workload_id", run)
            self.assertIn("run_id", run)
            self.assertIn("success", run)
            self.assertIn("metrics", run)

            self.assertIn(run["variant"], ("baseline", "treatment"))
            self.assertIsInstance(run["workload_id"], str)
            self.assertIsInstance(run["run_id"], str)
            self.assertIsInstance(run["success"], bool)

            metrics = run["metrics"]
            self.assertIsInstance(metrics, dict)
            # Every metric value must be a number (no dicts/lists/None/bools)
            for key, value in metrics.items():
                self.assertIsInstance(
                    value,
                    (int, float),
                    msg=f"metric {key} must be numeric, got {type(value)}",
                )

            wl = run["workload_id"]
            variants_by_workload.setdefault(wl, set()).add(run["variant"])

        # Each workload must have at least one baseline and one treatment run
        for wl, variants in variants_by_workload.items():
            self.assertIn("baseline", variants, f"workload {wl} missing baseline run")
            self.assertIn("treatment", variants, f"workload {wl} missing treatment run")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
