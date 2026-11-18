# Baseline AI Models for Quantum Network Anomaly Detection (Chapter 8)

This self-contained project implements a simplified, fully offline version of the Chapter 8 experiment:

> **Baseline AI Models for Quantum Network Anomaly Detection**

It is adapted for an execution sandbox with **no third-party packages** and **no network**, while preserving the structure of:

- Baseline vs. treatment variants
- Per-record vs. time-windowed workloads
- Unsupervised vs. supervised anomaly/attack detection
- Reproducible execution and evidence capture

Because we cannot install `scikit-learn` or other ML libraries here, all models and metrics are implemented from scratch using only the Python standard library.

## Contents

- `run.py` – Orchestrates the whole experiment and writes evidence to `/evidence/results.json`.
- `experiment/config.py` – Encodes the experiment specification (IDs, workloads, tasks) in code form.
- `experiment/data.py` – Generates deterministic synthetic quantum-network-like telemetry for two workloads:
  - Per-record telemetry
  - Time-windowed telemetry
- `experiment/models.py` – Implements simple baseline and treatment models:
  - Unsupervised: mean-variance anomaly scoring with fixed threshold
  - Supervised: one-dimensional threshold classifier
- `experiment/metrics.py` – Computes binary classification metrics used as shared numeric measurements.
- `experiment/runner.py` – Runs all combinations of (baseline/treatment) × (workload) and returns structured run results.
- `tests/test_experiment.py` – Verifies the evidence JSON schema and basic properties of the experiment.

## Experiment Shape (Sandbox Version)

This project is a minimal but principled approximation of the much richer spec described in the prompt. Key constraints and adaptations:

- **No external dependencies**: We cannot use scikit-learn, pandas, numpy, or plotting.
- **Synthetic data instead of chapter datasets**: We procedurally generate small data tables that resemble quantum telemetry (QBER, key rates, photon counts, channel loss, etc.) with embedded attack patterns.
- **Simple models** rather than true tree ensembles or One-Class SVM:
  - **Unsupervised baseline**: per-record z-score anomaly detector on a subset of features.
  - **Unsupervised treatment**: window-level anomaly detector with slightly richer feature set to emulate sequence modeling.
  - **Supervised baseline**: per-record threshold classifier on an engineered attack score.
  - **Supervised treatment**: window-level threshold classifier on window-aggregated attack score.

Despite simplification, we:

- Maintain the distinction between **baseline** (static features) and **treatment** (time-windowed features).
- Maintain two separate **workloads**:
  - `wl-quantum-telemetry-per-record`
  - `wl-quantum-telemetry-windowed`
- Produce **at least one run per variant per workload**.
- Record basic metrics from actual execution.

## Evidence Contract

`run.py` must write a JSON file to the directory given by `BOOKMAS_EVIDENCE_DIR` (default: `/evidence`):

```json
{
  "chapter": 8,
  "experiment_id": "exp-ch08-baseline-ai-models-quantum-anomaly-detection-v1",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline" or "treatment",
      "workload_id": "wl-quantum-telemetry-per-record" or "wl-quantum-telemetry-windowed",
      "run_id": "unique string",
      "success": true or false,
      "metrics": {
        "some_metric": 0.123,
        "another_metric": 5.0
      }
    },
    ... more runs ...
  ],
  "notes": "optional string"
}
```

Additional fields may be included, but every value inside each `metrics` object **must** be a finite JSON number.

### Metrics in This Sandbox

We compute a small, safe subset of metrics that can be implemented with the standard library:

- `accuracy` – overall accuracy on the test split.
- `precision_attack` – precision with attack class (1) as positive.
- `recall_attack` – recall with attack class (1) as positive.
- `attack_rate` – fraction of attack samples in the test data.

All metrics are derived from actual predictions on synthetic data produced at runtime; no values are fabricated.

## Running the Experiment

From the project root (where `run.py` lives):

```bash
python run.py
```

After the run, inspect the evidence file (inside the sandbox this path is writable and inspected by the validator):

```bash
cat /evidence/results.json
```

You should see multiple `runs` entries, including:

- `variant": "baseline", "workload_id": "wl-quantum-telemetry-per-record"`
- `variant": "treatment", "workload_id": "wl-quantum-telemetry-per-record"`
- `variant": "baseline", "workload_id": "wl-quantum-telemetry-windowed"`
- `variant": "treatment", "workload_id": "wl-quantum-telemetry-windowed"`

## Running Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The tests ensure that:

- `/evidence/results.json` exists after running `run.py`.
- The top-level keys are present.
- The `runs` array contains at least one baseline and one treatment run per workload.
- Every `metrics` value is a finite number (int or float), not null or a container type.

## Limitations vs. Full Chapter 8 Specification

- We do **not** load real datasets from a repository, nor do we implement IsolationForest, One-Class SVM, RandomForest, or GradientBoosting.
- We do **not** compute advanced metrics such as ROC AUC, PR AUC, F1, Brier score, or latency distributions, because they would require more extensive numerical tooling and/or large data.
- We do **not** generate notebooks or persistent model artifacts.

Nevertheless, this mini-project mirrors the logical design of the chapter and demonstrates:

- A clear mapping between specification concepts (workloads, variants) and actual code.
- Deterministic, reproducible results.
- A clean evidence file suitable for higher-level tooling to ingest.
