import json
import os
import shutil
import tempfile
import unittest
import run


class TestExperimentEvidence(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp(prefix="evidence_")
        os.environ["BOOKMAS_EVIDENCE_DIR"] = self.tmpdir

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        if "BOOKMAS_EVIDENCE_DIR" in os.environ:
            del os.environ["BOOKMAS_EVIDENCE_DIR"]

    def test_run_produces_valid_results(self) -> None:
        # Run the experiment, which should write results.json into tmpdir
        run.main()

        results_path = os.path.join(self.tmpdir, "results.json")
        self.assertTrue(os.path.exists(results_path), "results.json not created")

        with open(results_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Top-level checks
        self.assertEqual(data.get("chapter"), 10)
        self.assertEqual(
            data.get("experiment_id"),
            "exp-ch10-e2e-quantum-aware-detection-pipeline-v1",
        )
        self.assertIsInstance(data.get("environment"), dict)
        self.assertIn("os", data["environment"])
        self.assertIn("python", data["environment"])

        runs = data.get("runs")
        self.assertIsInstance(runs, list)
        self.assertGreaterEqual(len(runs), 6)  # at least 2 variants * 3 workloads

        # Workload coverage and metric shape
        workloads = {
            "WL1-normal-traffic",
            "WL2-mixed-attacks",
            "WL3-burst-and-failure-resilience",
        }
        coverage = {w: {"baseline": 0, "treatment": 0} for w in workloads}

        for run_rec in runs:
            self.assertIn(run_rec["variant"], ["baseline", "treatment"])
            self.assertIn(run_rec["workload_id"], workloads)
            self.assertIsInstance(run_rec.get("run_id"), str)
            self.assertIn("success", run_rec)
            self.assertIsInstance(run_rec["success"], bool)

            metrics = run_rec.get("metrics")
            self.assertIsInstance(metrics, dict)
            # At least one metric per run
            self.assertGreater(len(metrics), 0)
            for k, v in metrics.items():
                # Metrics must be numbers
                self.assertIsInstance(v, (int, float), msg=f"Metric {k} is non-numeric")

            coverage[run_rec["workload_id"]][run_rec["variant"]] += 1

        # Ensure at least one baseline and one treatment run per workload
        for w in workloads:
            self.assertGreaterEqual(
                coverage[w]["baseline"], 1, f"No baseline run for {w}"
            )
            self.assertGreaterEqual(
                coverage[w]["treatment"], 1, f"No treatment run for {w}"
            )


if __name__ == "__main__":
    unittest.main()
