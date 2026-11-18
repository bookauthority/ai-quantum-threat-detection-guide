# Experiment: Chapter 10 – End-to-End Quantum-Aware Detection Pipeline

This project is a **self-contained, offline Python 3.11+ experiment** that
simulates and compares two quantum-aware threat detection pipelines:

- **Baseline** – batch-oriented detection over log files.
- **Treatment** – streaming-oriented detection with a sidecar-style model
  server and online feature store.

The goal is to provide an **executable, minimal, and deterministic** reference
implementation that exercises the core architectural ideas from the
specification while remaining lightweight enough for automated evaluation.

Key properties:

- Uses only the Python standard library (no external dependencies).
- Generates synthetic "quantum telemetry" and attack labels.
- Implements logically similar feature extraction for batch and streaming
  pipelines.
- Uses a tiny, deterministic anomaly model shared by both pipelines.
- Produces a machine-readable evidence file at `/evidence/results.json`
  following the required schema.
- Includes basic unit tests runnable via `python -m unittest`.

## Repository Layout

- `run.py` – Main entrypoint used by the evaluator. Runs the full experiment
  for all workloads and both pipeline variants and writes evidence.
- `requirements.txt` – Empty of runtime dependencies (standard library only).
- `pipelines/`
  - `common.py` – Shared data models, telemetry simulator, and utilities.
  - `baseline_batch.py` – Batch-oriented pipeline implementation.
  - `streaming_sidecar.py` – Streaming pipeline with in-process sidecar model
    server.
- `models/simple_model.py` – Small, deterministic anomaly scoring model.
- `tests/test_experiment.py` – Unit tests validating the evidence schema and
  basic behavioral properties.

## Conceptual Overview

This project **simulates** a simplified quantum network telemetry feed. It is
not physically accurate, but is structured to mirror the chapter's concerns:

- Telemetry events contain fields such as `link_id`, `sim_time`, `key_rate`,
  and `qber` (quantum bit error rate).
- Workloads encode three scenarios:
  - `WL1-normal-traffic`: no attacks, low noise.
  - `WL2-mixed-attacks`: injected attack intervals per link.
  - `WL3-burst-and-failure-resilience`: bursts and a simulated model server
    restart.
- Both pipelines use the same feature definition: simple rolling statistics
  over fixed-duration time windows per link.
- Both pipelines share a trivial, deterministic anomaly score model that looks
  for elevated QBER and depressed key rate relative to normal.

### Baseline Pipeline (Batch)

The baseline imitates a periodic batch job:

1. The simulator writes all telemetry events and ground-truth attack labels
   into in-memory lists (in a real system they would be files).
2. The batch pipeline groups timestamps into fixed windows
   (e.g., 10 seconds) per link.
3. Within each window it computes aggregate features and sends them through
   the shared model.
4. Alerts are produced if scores exceed the decision threshold.
5. Simple metrics are computed:
   - Number of windows processed.
   - Number of alerts.
   - Latency-like statistic based on simulated times
     (`alert_time - event_time` from the simulator time base).

### Treatment Pipeline (Streaming + Sidecar)

The treatment imitates a streaming architecture with sidecar inference:

1. The simulator yields events in timestamp order.
2. A streaming worker ingests events one by one, maintaining per-link
   sliding windows and an in-memory feature store.
3. When a window closes, the worker calls the **sidecar model server** through
   an in-process function call that mimics an RPC boundary.
4. Alerts are produced immediately when scores exceed the threshold.
5. The treatment measures the same basic metrics as the baseline, along with
   a rough event throughput statistic.

To stay within sandbox constraints, the **sidecar server is not a real HTTP
service** but a logically separate component with a clear API.

## Evidence Output Contract

`run.py` must be executed from the project root. It will:

1. Run at least one **baseline** and one **treatment** instance for each of the
   three workloads:
   - `WL1-normal-traffic`
   - `WL2-mixed-attacks`
   - `WL3-burst-and-failure-resilience`
2. Collect metrics for each `(variant, workload)` pair.
3. Write a JSON file at:

   ```text
   $BOOKMAS_EVIDENCE_DIR/results.json
   ```

   The environment variable `BOOKMAS_EVIDENCE_DIR` will be provided by the
   evaluator. If it is missing, `run.py` will default to `/evidence`.

The JSON structure is:

```json
{
  "chapter": 10,
  "experiment_id": "exp-ch10-e2e-quantum-aware-detection-pipeline-v1",
  "environment": {
    "os": "<string>",
    "python": "<string>"
  },
  "runs": [
    {
      "variant": "baseline" or "treatment",
      "workload_id": "WL1-normal-traffic" | "WL2-mixed-attacks" | "WL3-burst-and-failure-resilience",
      "run_id": "<unique string>",
      "success": true or false,
      "metrics": {
        "<metric_name>": <finite number>,
        "...": <number>
      }
    }
  ],
  "notes": "<optional string>"
}
``

Constraints enforced by the code and tests:

- `chapter` is the integer `10`.
- `experiment_id` matches exactly the specification.
- Every `metrics` value is a **JSON number** (Python `int` or `float`).
- At least one metric is produced per run (e.g.,
  `windows_processed`, `alerts_emitted`, `median_latency_ms`, `throughput_events_per_second`).
- At least one **baseline** and one **treatment** run are present for **each**
  workload.


## Running the Experiment

From the project root (where `run.py` lives):

```bash
# Optional: set evidence directory (will be created if missing)
export BOOKMAS_EVIDENCE_DIR=/evidence

# Run the full experiment
python run.py

# The evidence will be written to
#   $BOOKMAS_EVIDENCE_DIR/results.json
```

You can inspect the output with any JSON viewer. A small snippet will look
similar to:

```json
{
  "chapter": 10,
  "experiment_id": "exp-ch10-e2e-quantum-aware-detection-pipeline-v1",
  "environment": {
    "os": "posix",
    "python": "3.11.9"
  },
  "runs": [
    {
      "variant": "baseline",
      "workload_id": "WL1-normal-traffic",
      "run_id": "baseline_WL1-normal-traffic_run1",
      "success": true,
      "metrics": {
        "windows_processed": 54,
        "alerts_emitted": 0,
        "median_latency_ms": 950.0
      }
    },
    {
      "variant": "treatment",
      "workload_id": "WL1-normal-traffic",
      "run_id": "treatment_WL1-normal-traffic_run1",
      "success": true,
      "metrics": {
        "windows_processed": 54,
        "alerts_emitted": 0,
        "median_latency_ms": 100.0,
        "throughput_events_per_second": 1200.0
      }
    }
  ],
  "notes": "..."
}
```

Values above are merely illustrative; the actual metrics are computed at
runtime from the simulation.

## Running Tests

Tests use only the Python standard library (`unittest`). From the project
root, run:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The tests validate:

- That `run.py` produces a `results.json` file with the required schema when
  invoked in a temporary evidence directory.
- That all metrics are numeric.
- That all three workloads have at least one baseline and one treatment run.

## Design Notes and Simplifications

- **Quantum-telemetry physics**: The simulator uses simplified stochastic
  processes for `key_rate` and `qber`. It is intentionally lightweight rather
  than physically realistic.
- **Timing model**: Latency metrics are computed strictly in simulator time:
  we use `sim_time` for events and windows and assume alerts are emitted at the
  window end time.
- **Resource metrics**: True CPU/memory utilization are not measured due to
  sandbox limitations; they are therefore **omitted** from the `metrics`
  mapping to respect the "no fabricated metrics" requirement.
- **Resilience / restarts**: WL3 injects a synthetic "restart" of the model
  sidecar by temporarily disabling scoring for some events. This affects
  latency and count metrics but does not rely on real processes.

This project is intended as a didactic, reproducible starting point, not as a
production-ready quantum threat detection system.
