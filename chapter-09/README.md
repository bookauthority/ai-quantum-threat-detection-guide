# Experiment: exp-09-advanced-temporal-hybrid-modeling

This is a **self-contained, fully offline, synthetic** Python 3.11+ experiment project that approximates the intent of Chapter 9: *Advanced Modeling: Temporal and Hybrid Approaches*.

Because the original specification depends on external simulators, large deep-learning frameworks, and GPUs, this project instead:

- Generates **small synthetic datasets** that loosely mimic the three workloads (WL-1, WL-2, WL-3).
- Implements **lightweight baselines** and **advanced (treatment) models** using only the Python standard library.
- Runs a **deterministic, bounded training/evaluation loop** so it is safe and fast in a restricted sandbox.
- Produces evidence in a standard JSON format under `/evidence/results.json` (or `$BOOKMAS_EVIDENCE_DIR/results.json`).

The goal is not to faithfully reproduce real quantum-network behavior but to demonstrate:

- Handling **temporal sequences** vs. static windows.
- A **simple autoencoder-like model** vs. a static baseline under rare-event imbalance.
- A minimal **graph-style contextual model** vs. a static baseline.

All numeric metrics written to evidence are **actually computed** by this code. No external libraries, network calls, or shells are used.

## Layout

- `run.py` – Entry point that runs all workloads and writes evidence.
- `experiment/
  - __init__.py
  - data.py` – Synthetic data generators for three workloads.
  - `models.py` – Simple baseline and treatment models (linear/logistic classifiers and tiny neural nets implemented from scratch).
  - `training.py` – Deterministic training and evaluation utilities.
  - `utils.py` – Randomness control, math helpers, JSON helpers.
- `tests/test_experiment.py` – Unittests that validate the evidence schema and basic behavior.
- `requirements.txt` – Empty (no external dependencies, standard library only).

## Workloads

The real chapter defines three workloads; here we approximate them as follows:

1. **WL-1-SingleLink-Temporal-Attacks**
   - Baseline: `StaticBaselineClassifier` on window-aggregated vectors.
   - Treatment: `SimpleSequenceModel` that operates on short sequences.
   - Metric: simple accuracy on a held-out test set.

2. **WL-2-MultiLink-Topology-Context**
   - Interpreted as a small graph-style dataset: each sample has a feature vector plus a small context vector representing neighbors.
   - Baseline: `StaticBaselineClassifier` on local node features only.
   - Treatment: `GraphContextModel` that uses both local and neighbor-aggregated features.
   - Metric: accuracy on a held-out test set.

3. **WL-3-Rare-Attack-Events**
   - Imbalanced dataset (rare positives).
   - Baseline: `StaticBaselineClassifier` trained on all windows.
   - Treatment: `SimpleAutoencoderDetector` trained on negatives only, used as anomaly detector with a fixed threshold selected on a small validation subset.
   - Metric: accuracy on a held-out test set.

## Running the experiment

From the project root:

```bash
python run.py
```

This will:

1. Generate synthetic datasets for WL-1, WL-2, and WL-3.
2. Train and evaluate a baseline and a treatment model for each workload.
3. Collect numeric metrics (currently per-workload classification accuracy) for each run.
4. Write a JSON evidence file to:
   - `$BOOKMAS_EVIDENCE_DIR/results.json` if the environment variable is set, **or**
   - `/evidence/results.json` otherwise.

The JSON has the required schema:

```json
{
  "chapter": 9,
  "experiment_id": "exp-09-advanced-temporal-hybrid-modeling",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline",
      "workload_id": "WL-1-SingleLink-Temporal-Attacks",
      "run_id": "baseline-WL-1-SingleLink-Temporal-Attacks",
      "success": true,
      "metrics": {"accuracy": 0.87}
    },
    {
      "variant": "treatment",
      "workload_id": "WL-1-SingleLink-Temporal-Attacks",
      "run_id": "treatment-WL-1-SingleLink-Temporal-Attacks",
      "success": true,
      "metrics": {"accuracy": 0.90}
    }
    // ... similarly for WL-2 and WL-3
  ],
  "notes": "..."
}
```

Numeric values will differ run to run only if you change the code; by default we use fixed seeds for reproducibility.

## Running tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The tests check that:

- `run.py` creates an evidence JSON file in the expected location.
- The JSON adheres to the specified schema, including numeric metrics.
- At least one baseline and one treatment run exist per workload.

## Reproducibility and determinism

- All random number generation is done via the Python standard library `random` module and `math`, with **fixed seeds per workload/model**.
- There is no dependence on system time or external sources of entropy.
- The small dataset sizes and simple models ensure bounded runtimes well within typical sandbox limits.

## Limitations

- No external simulators, PyTorch, scikit-learn, or graph libraries are used.
- The models are **toy approximations** to the temporal, autoencoder, hybrid, and graph models described in the original chapter.
- Many complex metrics in the full chapter (AUROC, latency distributions, etc.) are **not** computed here to keep the project simple, dependency-free, and safe.

This project focuses on rigorously producing structurally correct experimental evidence, rather than faithfully modeling real quantum network behavior.
