from typing import Any, Dict, List


def get_all_workloads() -> List[Dict[str, Any]]:
    """Return the four workloads as plain Python dicts.

    `simulator_variant_baseline_supported` indicates whether we can run a
    baseline variant for that workload. For non-single-link topologies we still
    reuse the single-link baseline model by collapsing to a representative
    link_distance and other scalar parameters.
    """

    workloads: List[Dict[str, Any]] = []

    # 1. baseline_single_link_nominal
    workloads.append(
        {
            "name": "baseline_single_link_nominal",
            "simulator_variant_baseline_supported": True,
            "baseline_config": {
                "link_distance_km": 20,
                "q_static": 0.02,
                "p_det_static": 0.1,
                "time_steps": 1000,  # reduced from 10000 for sandbox speed
                "emitted_photons_per_step": 500,
                "random_seed": 1234,
            },
            "treatment_config": {
                "topology": {
                    "type": "single_link",
                    "nodes": ["Alice", "Bob"],
                    "links": [
                        {
                            "id": "link_ab",
                            "src": "Alice",
                            "dst": "Bob",
                            "link_distance_km": 20,
                        }
                    ],
                },
                "qkd_protocol": "BB84_simplified",
                "fiber_loss_db_per_km": 0.2,
                "detector_efficiency": 0.15,
                "insertion_losses_db": 1.0,
                "baseline_qber": 0.02,
                "noise_model": {
                    "dark_count_rate": 50,
                    "background_noise_level": 0.001,
                    "misalignment_angle_deg": 3.0,
                    "drift_process": {
                        "type": "random_walk",
                        "std_per_1000_steps": 0.25,
                    },
                },
                "time_model": {
                    "steps": 1000,
                    "frame_size": 100,
                    "emitted_photons_per_step": 500,
                },
                "benign_scenarios": [],
                "attack_scenarios": [],
                "random_seed": 1234,
            },
        }
    )

    # 2. treatment_single_link_benign
    workloads.append(
        {
            "name": "treatment_single_link_benign",
            "simulator_variant_baseline_supported": True,
            "baseline_config": {
                # Use a single-link approximation of the treatment config
                "link_distance_km": 10,
                "q_static": 0.02,
                "p_det_static": 0.12,
                "time_steps": 2000,
                "emitted_photons_per_step": 500,
                "random_seed": 42,
            },
            "treatment_config": {
                "topology": {
                    "type": "single_link",
                    "nodes": ["Alice", "Bob"],
                    "links": [
                        {
                            "id": "link_ab",
                            "src": "Alice",
                            "dst": "Bob",
                            "link_distance_km": 10,
                        }
                    ],
                },
                "qkd_protocol": "BB84_simplified",
                "fiber_loss_db_per_km": 0.2,
                "detector_efficiency": 0.15,
                "insertion_losses_db": 1.0,
                "baseline_qber": 0.02,
                "noise_model": {
                    "dark_count_rate": 100,
                    "background_noise_level": 0.001,
                    "misalignment_angle_deg": 3.0,
                    "drift_process": {
                        "type": "random_walk",
                        "std_per_1000_steps": 0.25,
                    },
                },
                "time_model": {
                    "steps": 2000,
                    "frame_size": 100,
                    "emitted_photons_per_step": 500,
                },
                "benign_scenarios": [
                    {
                        "type": "gradual_degradation",
                        "start_step": 500,
                        "end_step": 1500,
                        "attenuation_delta_db": 2.0,
                    },
                    {
                        "type": "intermittent_dropout",
                        "num_bursts": 2,
                        "burst_length_steps": 30,
                        "detection_scaling": 0.1,
                    },
                ],
                "attack_scenarios": [],
                "random_seed": 42,
            },
        }
    )

    # 3. treatment_single_link_attacks
    workloads.append(
        {
            "name": "treatment_single_link_attacks",
            "simulator_variant_baseline_supported": True,
            "baseline_config": {
                "link_distance_km": 10,
                "q_static": 0.02,
                "p_det_static": 0.12,
                "time_steps": 1500,
                "emitted_photons_per_step": 500,
                "random_seed": 43,
            },
            "treatment_config": {
                "topology": {
                    "type": "single_link",
                    "nodes": ["Alice", "Bob"],
                    "links": [
                        {
                            "id": "link_ab",
                            "src": "Alice",
                            "dst": "Bob",
                            "link_distance_km": 10,
                        }
                    ],
                },
                "qkd_protocol": "BB84_simplified",
                "fiber_loss_db_per_km": 0.2,
                "detector_efficiency": 0.15,
                "baseline_qber": 0.02,
                "noise_model": {
                    "dark_count_rate": 100,
                    "background_noise_level": 0.001,
                    "misalignment_angle_deg": 3.0,
                },
                "time_model": {
                    "steps": 1500,
                    "frame_size": 100,
                    "emitted_photons_per_step": 500,
                },
                "benign_scenarios": [],
                "attack_scenarios": [
                    {
                        "id": "attack1",
                        "type": "intercept_resend_eavesdropping",
                        "start_step": 300,
                        "end_step": 700,
                        "attack_intensity": 0.8,
                    },
                    {
                        "id": "attack2",
                        "type": "jamming_or_dos",
                        "jam_type": "blocking",
                        "start_step": 900,
                        "end_step": 1050,
                        "jam_strength": 1.0,
                    },
                    {
                        "id": "attack3",
                        "type": "misconfiguration",
                        "change_time_step": 1200,
                        "basis_bias_change": 0.2,
                        "misalignment_delta": 2.0,
                    },
                ],
                "random_seed": 43,
            },
        }
    )

    # 4. treatment_multilink_topology_mixed
    workloads.append(
        {
            "name": "treatment_multilink_topology_mixed",
            "simulator_variant_baseline_supported": True,
            "baseline_config": {
                # approximate using average link distance
                "link_distance_km": 25,
                "q_static": 0.015,
                "p_det_static": 0.1,
                "time_steps": 2000,
                "emitted_photons_per_step": 500,
                "random_seed": 44,
            },
            "treatment_config": {
                "topology": {
                    "type": "line",
                    "nodes": ["Alice", "R1", "Bob"],
                    "links": [
                        {
                            "id": "link_a_r1",
                            "src": "Alice",
                            "dst": "R1",
                            "link_distance_km": 25,
                        },
                        {
                            "id": "link_r1_b",
                            "src": "R1",
                            "dst": "Bob",
                            "link_distance_km": 25,
                        },
                    ],
                },
                "qkd_protocol": "BB84_simplified",
                "fiber_loss_db_per_km": 0.2,
                "detector_efficiency": 0.2,
                "baseline_qber": 0.015,
                "noise_model": {
                    "dark_count_rate": 80,
                    "background_noise_level": 0.001,
                    "misalignment_angle_deg": 2.0,
                },
                "time_model": {
                    "steps": 2000,
                    "frame_size": 200,
                    "emitted_photons_per_step": 500,
                },
                "benign_scenarios": [
                    {
                        "target_link_id": "link_a_r1",
                        "type": "gradual_degradation",
                        "start_step": 500,
                        "end_step": 1500,
                        "attenuation_delta_db": 2.0,
                    }
                ],
                "attack_scenarios": [
                    {
                        "id": "attack4",
                        "target_link_id": "link_r1_b",
                        "type": "intercept_resend_eavesdropping",
                        "start_step": 600,
                        "end_step": 1000,
                        "attack_intensity": 0.6,
                    },
                    {
                        "id": "attack5",
                        "target_node_id": "R1",
                        "type": "misconfiguration",
                        "change_time_step": 1500,
                        "basis_bias_change": 0.1,
                        "misalignment_delta": 1.0,
                    },
                ],
                "random_seed": 44,
            },
        }
    )

    return workloads
