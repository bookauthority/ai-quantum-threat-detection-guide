from typing import Any, Dict, List, Optional

from .util import RNG, binomial


def _compute_channel_loss_db(link_distance_km: float, fiber_loss_db_per_km: float, insertion_losses_db: float) -> float:
    return fiber_loss_db_per_km * link_distance_km + insertion_losses_db


def _detection_probability(channel_loss_db: float, detector_efficiency: float) -> float:
    # Convert loss in dB to linear transmission factor
    transmission = 10 ** (-channel_loss_db / 10.0)
    return transmission * detector_efficiency


def _secret_key_bits_estimate(sifted: int, qber: float) -> float:
    # Very rough approximation: secret fraction ~(1 - 2*qber) clipped at 0
    frac = max(0.0, 1.0 - 2.0 * qber)
    return float(sifted) * frac


def _apply_benign_scenarios(step: int, link_id: str, base_loss_db: float, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
    loss_delta = 0.0
    dropout_scaling = 1.0
    dropout_flag = False
    calibration_flag = False

    for sc in scenarios:
        stype = sc.get("type")
        target_link = sc.get("target_link_id")
        if target_link is not None and target_link != link_id:
            continue

        if stype == "gradual_degradation":
            start = int(sc["start_step"])
            end = int(sc["end_step"])
            if start <= step <= end:
                total_delta = float(sc["attenuation_delta_db"])
                fraction = (step - start) / max(1, end - start)
                loss_delta += total_delta * fraction
        elif stype == "intermittent_dropout":
            # model bursts starting at deterministic offsets using simple pattern
            num_bursts = int(sc["num_bursts"])
            burst_len = int(sc["burst_length_steps"])
            scale = float(sc["detection_scaling"])
            total_span = max(1, num_bursts * burst_len * 2)
            pos = step % total_span
            for b in range(num_bursts):
                b_start = b * burst_len * 2
                b_end = b_start + burst_len
                if b_start <= pos < b_end:
                    dropout_scaling = min(dropout_scaling, scale)
                    dropout_flag = True
        elif stype == "calibration_event":
            start = int(sc["start_step"])
            end = int(sc["end_step"])
            if start <= step <= end:
                calibration_flag = True
    return {
        "loss_db": base_loss_db + loss_delta,
        "detection_scaling": dropout_scaling,
        "dropout_flag": dropout_flag,
        "calibration_event_flag": calibration_flag,
    }


def _attack_effects(step: int, link_id: str, base_qber: float, base_det_prob: float, misalignment_deg: float, attack_scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
    scenario_type = "benign"
    attack_name: Optional[str] = None
    qber = base_qber
    det_prob = base_det_prob
    misalignment = misalignment_deg

    for sc in attack_scenarios:
        sc_type = sc.get("type")
        target_link = sc.get("target_link_id")
        target_node = sc.get("target_node_id")
        if target_link is not None and target_link != link_id:
            continue
        if target_node is not None:
            # for this simplified model we ignore node-targeted vs link-targeted
            pass

        if sc_type == "intercept_resend_eavesdropping":
            start = int(sc["start_step"])
            end = int(sc["end_step"])
            if start <= step <= end:
                intensity = float(sc.get("attack_intensity", 0.5))
                qber = base_qber + 0.05 * intensity
                scenario_type = "attack"
                attack_name = "intercept_resend_eavesdropping"
        elif sc_type == "jamming_or_dos":
            start = int(sc["start_step"])
            end = int(sc["end_step"])
            if start <= step <= end:
                jam_type = sc.get("jam_type", "blocking")
                strength = float(sc.get("jam_strength", 1.0))
                if jam_type == "blocking":
                    det_prob = base_det_prob * max(0.0, 1.0 - strength)
                else:
                    # noisy: increase qber
                    qber = base_qber + 0.1 * strength
                scenario_type = "attack"
                attack_name = "jamming_or_dos"
        elif sc_type == "misconfiguration":
            change_step = int(sc["change_time_step"])
            if step >= change_step:
                delta = float(sc.get("misalignment_delta", 0.0))
                misalignment = misalignment_deg + delta
                qber = base_qber + 0.01 * (abs(delta) / 2.0)
                scenario_type = "attack"
                attack_name = "misconfiguration"

    return {
        "scenario_type": scenario_type,
        "attack_name": attack_name,
        "qber": qber,
        "det_prob": det_prob,
        "misalignment": misalignment,
    }


def simulate_treatment(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    topology = config["topology"]
    links = topology["links"]
    fiber_loss_db_per_km = float(config.get("fiber_loss_db_per_km", 0.2))
    insertion_losses_db = float(config.get("insertion_losses_db", 1.0))
    detector_efficiency = float(config.get("detector_efficiency", 0.15))
    baseline_qber = float(config.get("baseline_qber", 0.02))
    noise_model = config.get("noise_model", {})
    background_noise_level = float(noise_model.get("background_noise_level", 0.0))
    misalignment_deg_base = float(noise_model.get("misalignment_angle_deg", 0.0))
    drift = noise_model.get("drift_process")

    time_model = config["time_model"]
    steps = int(time_model["steps"])
    frame_size = max(1, int(time_model.get("frame_size", 1)))
    emitted_per_step = int(time_model["emitted_photons_per_step"])

    benign_scenarios = list(config.get("benign_scenarios", []))
    attack_scenarios = list(config.get("attack_scenarios", []))

    rng = RNG(int(config["random_seed"]))

    telemetry: List[Dict[str, Any]] = []

    # simple per-link misalignment with drift
    misalignment_per_link = {link["id"]: misalignment_deg_base for link in links}

    for step in range(steps):
        frame_id = step // frame_size

        # update drift
        if drift and drift.get("type") == "random_walk":
            std_per_1000 = float(drift.get("std_per_1000_steps", 0.0))
            step_std = std_per_1000 / 1000.0
            for lid in misalignment_per_link:
                misalignment_per_link[lid] += rng.gauss(0.0, step_std)

        for link in links:
            link_id = link["id"]
            src = link["src"]
            dst = link["dst"]
            distance = float(link["link_distance_km"])

            base_loss_db = _compute_channel_loss_db(distance, fiber_loss_db_per_km, insertion_losses_db)

            benign_effect = _apply_benign_scenarios(step, link_id, base_loss_db, benign_scenarios)
            loss_db = benign_effect["loss_db"]
            det_scaling = benign_effect["detection_scaling"]

            base_det_prob = _detection_probability(loss_db, detector_efficiency) * det_scaling

            base_misalignment = misalignment_per_link[link_id]
            base_qber = baseline_qber + 0.001 * abs(base_misalignment)

            attack_effect = _attack_effects(step, link_id, base_qber, base_det_prob, base_misalignment, attack_scenarios)
            scenario_type = attack_effect["scenario_type"]
            attack_name = attack_effect["attack_name"]
            qber = attack_effect["qber"]
            det_prob = max(0.0, min(1.0, attack_effect["det_prob"]))
            misalignment_now = attack_effect["misalignment"]

            emitted = emitted_per_step
            detected = binomial(emitted, det_prob, rng)
            if detected > 0:
                error_bits = binomial(detected, max(0.0, min(0.5, qber)), rng)
            else:
                error_bits = 0
            qber_measured = float(error_bits) / float(detected) if detected > 0 else 0.0

            sifted = detected // 2
            secret_bits = _secret_key_bits_estimate(sifted, qber_measured)

            record: Dict[str, Any] = {
                "time_step": step,
                "frame_id": frame_id,
                "link_id": link_id,
                "topology_node_src": src,
                "topology_node_dst": dst,
                "scenario_id": scenario_type if attack_name is None else attack_name,
                "scenario_type": scenario_type,
                "attack_name": attack_name,
                "emitted_photons": emitted,
                "detected_photons": detected,
                "dark_counts": 0,
                "error_bits": error_bits,
                "qber": qber_measured,
                "sifted_key_bits": sifted,
                "secret_key_bits_estimated": secret_bits,
                "channel_loss_db": loss_db,
                "link_distance_km": distance,
                "fiber_loss_db_per_km": fiber_loss_db_per_km,
                "detector_efficiency": detector_efficiency,
                "background_noise_level": background_noise_level,
                "misalignment_angle": misalignment_now,
                "dropout_flag": benign_effect["dropout_flag"],
                "calibration_event_flag": benign_effect["calibration_event_flag"],
            }
            telemetry.append(record)

    return telemetry


def run_treatment_workload(workload: Dict[str, Any]) -> List[Dict[str, Any]]:
    config = workload["treatment_config"]
    return simulate_treatment(config)
