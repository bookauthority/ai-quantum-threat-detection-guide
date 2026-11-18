from typing import Any, Dict, List

from .util import RNG, binomial


def simulate_baseline(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Run the baseline single-link simulator.

    Telemetry fields are a subset of the richer treatment schema so they can be
    consumed uniformly in metric code.
    """

    steps = int(config["time_steps"])
    emitted_per_step = int(config["emitted_photons_per_step"])
    q_static = float(config["q_static"])
    p_det_static = float(config["p_det_static"])
    link_distance = float(config.get("link_distance_km", 0.0))
    rng = RNG(int(config["random_seed"]))

    telemetry: List[Dict[str, Any]] = []

    for t in range(steps):
        # simple hard failure: randomly at one step, no detections
        hard_fail = False
        if steps > 0 and rng.random() < 1.0 / max(steps, 1):
            hard_fail = True

        emitted = emitted_per_step
        if hard_fail:
            detected = 0
        else:
            detected = binomial(emitted, p_det_static, rng)

        error_bits = binomial(detected, q_static, rng) if detected > 0 else 0
        qber = float(error_bits) / float(detected) if detected > 0 else 0.0

        # baseline doesn't really use these fields; fill with neutral values
        record: Dict[str, Any] = {
            "time_step": t,
            "frame_id": t,  # 1:1 mapping for baseline
            "link_id": "baseline_link",
            "topology_node_src": "Alice",
            "topology_node_dst": "Bob",
            "scenario_id": "baseline",
            "scenario_type": "benign",
            "attack_name": None,
            "emitted_photons": emitted,
            "detected_photons": detected,
            "dark_counts": 0,
            "error_bits": error_bits,
            "qber": qber,
            "sifted_key_bits": detected // 2,
            "secret_key_bits_estimated": (detected // 2) * max(0.0, 1.0 - 2 * qber),
            "channel_loss_db": 0.0,
            "link_distance_km": link_distance,
            "fiber_loss_db_per_km": 0.0,
            "detector_efficiency": p_det_static,
            "background_noise_level": 0.0,
            "misalignment_angle": 0.0,
            "dropout_flag": hard_fail,
            "calibration_event_flag": False,
        }
        telemetry.append(record)

    return telemetry


def run_baseline_workload(workload: Dict[str, Any]) -> List[Dict[str, Any]]:
    config = workload["baseline_config"]
    return simulate_baseline(config)
