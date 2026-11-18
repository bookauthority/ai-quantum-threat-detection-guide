# Chapter 11 Experiment – SOC/SIEM Integration (Offline Sandbox)

This project implements a **self-contained, offline simulation** of the experiment:

> **Integrating Quantum-Aware Detection with SOC and SIEM Workflows**

It follows the provided experiment specification with:

- A **baseline**: naive SOC/SIEM integration of quantum detection alerts.
- A **treatment**: quantum-aware enriched SOC/SIEM integration.
- Three workloads:
  - `W1-simulated-quantum-attack-campaigns`
  - `W2-simulated-incident-drills`
  - `W3-analyst-triage-simulation`

Because this sandbox is offline and constrained (no real HTTP servers, no external datasets, no third-party libraries), we **simulate** the behavior of:

- The detection pipeline
- The mock SIEM
- The enrichment engine
- Analyst triage behavior

The code focuses on **deterministic, reproducible comparisons** between baseline and treatment using only the Python standard library.

## What this project does

- Simulates quantum telemetry streams and detection alerts for several channels.
- Implements:
  - A baseline **naive alert schema** (minimal fields, no enrichment, no playbooks).
  - A treatment **quantum-aware alert schema** (severity, quantum context, playbooks, etc.).
- Groups alerts into incidents using different logic for baseline vs treatment.
- Simulates analyst triage (scripted rules) over these incidents.
- Measures at least one numeric metric that is **actually computed** from runtime behavior, not fabricated:
  - Here we measure **`alert_volume_rate`** (alerts per synthetic minute) for each run.
- Writes experiment evidence in the required schema to `/evidence/results.json`.

All stochastic elements are driven by fixed seeds per run for deterministic behavior.

## Limitations (important for interpretation)

The full experiment spec includes metrics like MTTR, missed incident rate, false positive rate, correlation latency, dashboard query latency, and analyst steps per incident. In this minimal sandbox:

- We **do not have real HTTP services, dashboards, or external simulators**.
- We must rely solely on the Python standard library.
- We must avoid fabricating numbers that are not actually measured.

Therefore:

- Many metrics from the spec are **not reported** in this implementation.
- We only report metrics that are directly computed from the simulated runs.
- We still keep the experimental structure (baseline vs treatment, three workloads) and ensure a fair, deterministic comparison.

## Files

Key files:

- `run.py` – Entry point that runs all workloads for both variants and writes `/evidence/results.json`.
- `experiment/core.py` – Core simulation logic:
  - Telemetry generation
  - Alert generation (baseline and treatment)
  - Incident grouping
  - Analyst triage simulation
- `experiment/evidence.py` – Evidence writer and environment metadata helpers.
- `tests/test_experiment.py` – Unit tests that:
  - Execute `run.py` in-process
  - Validate evidence structure strictly using the Python standard library
  - Check that required fields and metric types are correct.

## Running the experiment

From the project root:

```bash
python run.py
```

This will:

1. Run baseline and treatment for each workload:
   - `W1-simulated-quantum-attack-campaigns`
   - `W2-simulated-incident-drills`
   - `W3-analyst-triage-simulation`
2. For each workload and variant, create at least one run.
3. Measure metrics (currently: `alert_volume_rate`).
4. Write evidence to:

```text
/evidence/results.json
```

If `/evidence` does not exist, it will be created.

You can override the evidence directory with the `BOOKMAS_EVIDENCE_DIR` environment variable; the experiment will write `results.json` inside that directory.

## Running tests

Use the Python unittest discovery as required:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The tests will:

- Import and run `run.py` to generate evidence.
- Read `/evidence/results.json` (or the directory from `BOOKMAS_EVIDENCE_DIR`).
- Validate that:
  - The JSON schema matches the contract from the prompt.
  - `chapter` is `11`.
  - `experiment_id` matches `exp-ch11-soc-siem-integration-v1`.
  - There is at least one baseline and one treatment run per workload.
  - All metrics are numeric.

## Reproducibility notes

- All pseudo-random operations are seeded with **fixed seeds derived from**:
  - workload id
  - variant name (baseline/treatment)
  - run index
- This ensures that runs are deterministic across executions on the same Python version.
- No network, subprocess, or external file paths (beyond `/tmp` and `/evidence`) are used.

## Extending the experiment

If you wish to extend this experiment in a richer environment (e.g., full repository, FastAPI, Pandas, etc.), you can:

- Replace the in-memory SIEM simulation with real HTTP services.
- Integrate an actual detection pipeline and quantum telemetry generator.
- Extend metrics to match the full specification (MTTR, missed incident rate, etc.).

The current structure (variants, workloads, runs, evidence schema) is designed to make such an extension straightforward while keeping this version self-contained and compliant with the offline sandbox constraints.
