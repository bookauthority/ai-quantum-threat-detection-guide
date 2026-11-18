# Chapter 7 Experiment: From Quantum Telemetry to ML-Ready Datasets

This self-contained project implements a simplified, fully deterministic version of the Chapter 7 experiment:

> **From Quantum Telemetry to ML-Ready Datasets**

It compares a **baseline** naive telemetry export pipeline with a more structured **treatment** pipeline that performs windowing, feature engineering, labeling, and splitting.

The implementation is offline and synthetic: instead of loading simulator outputs from Chapter 6, it generates reproducible fake quantum and classical telemetry and scenario metadata locally. Both baseline and treatment operate on the **same generated raw data** to allow a fair comparison.

The project is designed to run inside a restricted sandbox with only the Python standard library available at runtime.

## Contents

- `run.py` – Main entry point. Generates synthetic raw telemetry, runs baseline and treatment pipelines for all workloads, and writes experiment evidence JSON to `/evidence/results.json`.
- `experiment/__init__.py` – Package marker.
- `experiment/config.py` – Hard-coded workload configurations, approximating the chapter spec.
- `experiment/data_gen.py` – Deterministic synthetic quantum/classical telemetry and scenario metadata generator.
- `experiment/pipelines.py` – Baseline and treatment dataset construction logic, including windowing, feature engineering, labeling, and splitting.
- `experiment/metrics.py` – Simple helper functions to compute basic numeric metrics and data quality summaries.
- `tests/test_experiment.py` – Unit tests that validate the evidence schema and basic behavior.
- `requirements.txt` – Empty runtime dependency list (standard library only as required).

## Execution Contract

The chapter framework expects that running the experiment produces a JSON evidence file at a path given by the `BOOKMAS_EVIDENCE_DIR` environment variable. This project implements that contract.

### Evidence Schema (runtime contract)

`run.py` writes a JSON file at:

```text
${BOOKMAS_EVIDENCE_DIR:-/evidence}/results.json
```

with this structure:

```json
{
  "chapter": 7,
  "experiment_id": "exp-ch7-quantum-telemetry-to-ml-ready-datasets-v1",
  "environment": {
    "os": "...",
    "python": "..."
  },
  "runs": [
    {
      "variant": "baseline" | "treatment",
      "workload_id": "W1_5s_sliding_windows_binary_attack_detection" | "W2_event_centered_eavesdropping_vs_clean" | "W3_multiclass_attack_type_classification",
      "run_id": "<unique-string>",
      "success": true | false,
      "metrics": {
        "num_samples_train": 123,
        "num_samples_val": 45,
        "num_samples_test": 67
      }
    }
  ],
  "notes": "optional text notes"
}
```

Constraints:

- At least **one baseline and one treatment run per workload** are recorded.
- Every `metrics` value is a **JSON number** (no strings, booleans, objects, arrays, or nulls).
- Any textual explanations, environment metadata, or other non-numeric information live **outside** `metrics`.
- Only metrics actually measured during execution are included; nothing is fabricated.

## Pipelines Overview

The implementation reflects the detailed chapter design in a simplified but faithful way.

### Synthetic Data

- Multiple `run_id`s, each with:
  - Telemetry table of rows with:
    - `timestamp` (float seconds)
    - `run_id`, `link_id`
    - Quantum metrics: `qber`, `key_rate`, `loss_db`, `quantum_alarm`
    - Classical metrics: `if_util`, `pkt_drop_rate`, `jitter`, `cpu_load`, `mem_util`
    - Ground-truth `attack_flag`, `attack_type` (string or "clean")
  - Scenario metadata:
    - `attack_intervals` per link with `attack_type`, `start`, `end`.

The generator uses only `random` from the standard library with a fixed seed for reproducibility.

### Baseline Pipeline

For each workload:

1. Use the same set of synthetic runs as the treatment.
2. Load telemetry rows.
3. Drop rows missing required fields (none in this synthetic implementation).
4. Keep a minimal subset of fields:
   - `timestamp`, `run_id`, `link_id`, `qber`, `key_rate`, `loss_db`, `if_util`, `label_attack` (derived from `attack_flag`).
5. Forward-fill `label_attack` per `(run_id, link_id)` when missing (our generator always provides them, but the logic is implemented).
6. Perform naive random 70/15/15 split **by row** using a fixed RNG seed.
7. Count samples per split as metrics.

### Treatment Pipeline

Common treatment behavior for all workloads:

1. Select the same synthetic `run_id`s as baseline.
2. Build either **fixed sliding windows** or **event-centered windows** per configuration.
3. For each window, compute aggregate features:
   - Quantum: mean, std, min, max for `qber`, `key_rate`, `loss_db`.
   - Classical: mean, std for `if_util`, `pkt_drop_rate`, `jitter`, `cpu_load`, `mem_util`.
   - Temporal: `window_duration`, `sample_count`.
4. Label windows according to workload:
   - W1: binary attack vs clean based on coverage of any attack interval.
   - W2: windows around `eavesdrop` events vs matched clean windows.
   - W3: multiclass label by `attack_type` vs clean.
   - Uncertain windows (if ambiguity) are simply dropped in this implementation to keep logic simple but consistent.
5. Handle imbalance via **class counts only**; no resampling is performed, but this is sufficient for numeric comparison and schema illustration.
6. Deterministic splits:
   - For simplicity, treat all workloads with **run-based splits** (60/20/20 across whole windows per run) using a fixed RNG seed, so there is no temporal leakage across splits.
7. Export only in-memory structures; we measure dataset sizes as metrics and do not persist Parquet files in this simplified offline version.

## Metrics Implemented

Because the sandbox is restricted and we avoid external storage and heavy dependencies, we implement a subset of the chapter's full metric set:

For each run record in `runs`:

- `num_samples_train` – window or row count in the training split.
- `num_samples_val` – validation split count.
- `num_samples_test` – test split count.

These are sufficient to demonstrate fair comparison and validate the evidence wiring. Additional quality metrics are computed internally but **not** reported as numeric metrics if they require complex structures.

## How to Run

The sandbox harness typically calls `python run.py` and sets `BOOKMAS_EVIDENCE_DIR` to `/evidence`. You can simulate the run manually in a regular environment as follows:

```bash
export BOOKMAS_EVIDENCE_DIR=/evidence  # or any writable directory
python run.py
cat /evidence/results.json
```

The script will:

1. Generate synthetic raw data.
2. Run baseline and treatment for each of the three workloads.
3. Collect minimal numeric metrics.
4. Write the evidence JSON file.

## Testing

Tests are standard-library only and can be run via:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

They check that:

- `run.py` creates the evidence file at the requested location.
- The evidence JSON conforms to the required schema, including:
  - `chapter` is `7`.
  - `experiment_id` matches the provided specification.
  - There is at least one baseline and one treatment entry per workload.
  - All metrics values are JSON numbers.

## Notes

- No external simulator, Parquet/CSV I/O, or network access is used: everything is computed in memory with the standard library.
- While simplified, the treatment logic respects the core intent of the chapter: convert quantum/classical telemetry to windowed, labeled ML-ready samples and compare with a naive baseline.
