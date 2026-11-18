# Chapter 6 Quantum Network Simulation Environment (Experiment Skeleton)

This mini project implements a **self-contained, standard-library-only** quantum
network telemetry simulator for reproducibility experiments.

It is **not** a physically-accurate QKD implementation. Instead, it encodes a
*toy but structured* model of quantum links, benign noise/failures, and simple
attacks, sufficient to:

- generate labeled per-time-step telemetry;
- compare a baseline vs. richer treatment simulator; and
- emit evidence in a fixed JSON schema for automated checks.

The design mirrors the specification in the prompt but omits external
dependencies (NumPy, pandas, pydantic, etc.) for sandbox compatibility.

## Layout

- `run.py` – orchestrates all workloads and writes evidence JSON to
  `$BOOKMAS_EVIDENCE_DIR/results.json`.
- `quantum_sim/` – simulator package
  - `__init__.py` – simple package marker
  - `baseline.py` – minimal baseline single-link simulator
  - `treatment.py` – richer treatment simulator with scenarios and attacks
  - `workloads.py` – configuration objects for the four workloads
  - `metrics.py` – shared metric computation helpers
  - `util.py` – simple RNG wrapper and helpers
- `tests/test_experiment.py` – unit tests for the evidence schema and basic
  simulator sanity.
- `requirements.txt` – intentionally empty of third-party runtime dependencies.

## Running the experiment

From the project root:

```bash
export BOOKMAS_EVIDENCE_DIR=/evidence  # or another writable directory
python run.py
```

This will:

1. Run each workload in **baseline** and **treatment** variants.
2. Compute a few numeric metrics from the produced telemetry
   (e.g., mean QBER over benign and attack windows when applicable).
3. Write `/evidence/results.json` (path controlled by the environment variable)
   with the following schema:

```json
{
  "chapter": 6,
  "experiment_id": "exp-ch06-quantum-net-sim-env-v1",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline" | "treatment",
      "workload_id": "baseline_single_link_nominal" | ...,
      "run_id": "string",
      "success": true,
      "metrics": {
        "mean_qber_benign": 0.0123,
        "num_steps": 10000
      },
      "notes": "optional non-metric notes"
    }
  ],
  "notes": "optional global notes"
}
```

Only **actual measured numeric quantities** appear inside `metrics`.

## Running tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The tests will:

- run `run.py` in-process to generate evidence in a temporary directory;
- load and validate `results.json` against the required structure;
- check that each workload has at least one baseline and one treatment run.

## Model overview

### Baseline simulator

- Single QKD-like link, no topology.
- Time is discrete steps; per step we simulate:
  - `emitted_photons` (fixed per workload),
  - `detected_photons` using a Bernoulli/binomial approximation,
  - `error_bits` using a fixed bit-flip probability `q_static`,
  - `qber = error_bits / max(detected_photons, 1)`.
- Runs only the `baseline_single_link_nominal` configuration.

### Treatment simulator

- Supports simple topologies: `single_link` and `line` (trusted repeater).
- Distinguishes *benign* vs *attack* scenario windows.
- Models:
  - attenuation as a function of distance and fiber loss in dB/km;
  - detector efficiency;
  - baseline QBER plus misalignment-driven noise;
  - simple random-walk drift on misalignment for benign runs;
  - benign failures: gradual degradation and intermittent dropouts;
  - attacks: intercept-resend, jamming/blocking, and misconfiguration.

Telemetry per step includes at least:

- `time_step`, `frame_id`, `link_id`,
- `scenario_type` ("benign" or "attack"), `attack_name` (or `None`),
- `emitted_photons`, `detected_photons`, `error_bits`, `qber`,
- `sifted_key_bits`, `secret_key_bits_estimated`,
- `channel_loss_db`, `link_distance_km`, `fiber_loss_db_per_km`,
- `detector_efficiency`, `background_noise_level`, `misalignment_angle`,
- `dropout_flag`, `calibration_event_flag`.

### Metrics

Within this sandbox we keep metrics modest and cheap to compute. For each run:

- `num_steps` – total number of telemetry rows.
- `mean_qber_benign` – average QBER over benign time steps.
- `mean_qber_attack` – average QBER over attack time steps (0 if none).

These are sufficient to distinguish baseline vs. treatment and benign vs.
attack behavior without relying on external libraries.

## Limitations

- This implementation avoids non-standard libraries entirely, so it uses
  home-grown data structures (lists of dicts) instead of pandas/NumPy.
- Physical realism is intentionally simplified to keep runtimes small and code
  readable while still capturing qualitatively useful behaviors for security
  analytics and ML experimentation.
