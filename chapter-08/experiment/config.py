from dataclasses import dataclass
from typing import List


EXPERIMENT_ID = "exp-ch08-baseline-ai-models-quantum-anomaly-detection-v1"
CHAPTER_NUMBER = 8


@dataclass(frozen=True)
class Workload:
    workload_id: str
    description: str


WORKLOADS: List[Workload] = [
    Workload(
        workload_id="wl-quantum-telemetry-per-record",
        description=(
            "Per-record ML workload on synthetic quantum-network-like telemetry "
            "with static features."
        ),
    ),
    Workload(
        workload_id="wl-quantum-telemetry-windowed",
        description=(
            "Time-windowed workload with aggregated sequence-style features "
            "per link/direction window."
        ),
    ),
]


BASELINE_VARIANT = "baseline"
TREATMENT_VARIANT = "treatment"


def list_workload_ids() -> List[str]:
    return [w.workload_id for w in WORKLOADS]
