import json
import os
import tempfile
import types
import unittest

import run as experiment_run


class TestChapter7Experiment(unittest.TestCase):
    def test_run_produces_valid_evidence(self) -> None:
        # Use a temporary directory for evidence
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["BOOKMAS_EVIDENCE_DIR"] = tmpdir
            # Execute main() directly
            experiment_run.main()

            evidence_path = os.path.join(tmpdir, "results.json")
            self.assertTrue(os.path.exists(evidence_path), "results.json not created")

            with open(evidence_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Top-level checks
            self.assertIsInstance(data, dict)
            self.assertEqual(data.get("chapter"), 7)
            self.assertEqual(
                data.get("experiment_id"),
                "exp-ch7-quantum-telemetry-to-ml-ready-datasets-v1",
            )
            self.assertIn("environment", data)
            self.assertIsInstance(data["environment"].get("os"), str)
            self.assertIsInstance(data["environment"].get("python"), str)

            runs = data.get("runs")
            self.assertIsInstance(runs, list)
            self.assertGreaterEqual(len(runs), 6)  # 3 workloads * (baseline + treatment)

            # Track presence of baseline/treatment per workload
            workloads = {
                "W1_5s_sliding_windows_binary_attack_detection": {"baseline": 0, "treatment": 0},
                "W2_event_centered_eavesdropping_vs_clean": {"baseline": 0, "treatment": 0},
                "W3_multiclass_attack_type_classification": {"baseline": 0, "treatment": 0},
            }

            for r in runs:
                self.assertIn(r.get("variant"), ("baseline", "treatment"))
                wid = r.get("workload_id")
                self.assertIn(wid, workloads)
                workloads[wid][r["variant"]] += 1
                self.assertIsInstance(r.get("run_id"), str)
                self.assertIsInstance(r.get("success"), bool)
                metrics = r.get("metrics")
                self.assertIsInstance(metrics, dict)
                # all metric values must be numbers
                for k, v in metrics.items():
                    self.assertIsInstance(
                        v,
                        (int, float),
                        msg=f"Metric {k} has non-numeric type {type(v)}",
                    )

            # Ensure at least one baseline and one treatment for each workload
            for wid, counts in workloads.items():
                self.assertGreaterEqual(
                    counts["baseline"], 1, f"No baseline run recorded for {wid}"
                )
                self.assertGreaterEqual(
                    counts["treatment"], 1, f"No treatment run recorded for {wid}"
                )


if __name__ == "__main__":
    unittest.main()
