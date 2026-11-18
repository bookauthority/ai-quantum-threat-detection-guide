import json
import os
import sys
import platform

from experiment.data import (
    generate_wl1_temporal_dataset,
    generate_wl2_graph_dataset,
    generate_wl3_rare_events_dataset,
)
from experiment.models import (
    StaticBaselineClassifier,
    SimpleSequenceModel,
    GraphContextModel,
    SimpleAutoencoderDetector,
)
from experiment.training import (
    train_classifier,
    evaluate_classifier,
    train_autoencoder_detector,
    evaluate_autoencoder_detector,
)
from experiment.utils import set_global_seed


EXPERIMENT_ID = "exp-09-advanced-temporal-hybrid-modeling"
CHAPTER = 9


def get_evidence_path() -> str:
    """Return path to evidence JSON file, honoring BOOKMAS_EVIDENCE_DIR.

    The directory is created if it does not exist.
    """
    base_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    try:
        os.makedirs(base_dir, exist_ok=True)
    except OSError:
        # If directory cannot be created, fall back to current directory.
        base_dir = "."
    return os.path.join(base_dir, "results.json")


def run_wl1() -> list:
    """Run baseline and treatment for WL-1 (temporal vs static)."""
    workload_id = "WL-1-SingleLink-Temporal-Attacks"

    # Generate deterministic dataset
    set_global_seed(42)
    train_seq, train_labels, val_seq, val_labels, test_seq, test_labels = (
        generate_wl1_temporal_dataset()
    )

    # Baseline uses window-aggregated features
    def aggregate_sequence(seq):
        # Simple mean over time dimension for each feature
        length = len(seq)
        if length == 0:
            return []
        dim = len(seq[0])
        sums = [0.0] * dim
        for t in seq:
            for i, v in enumerate(t):
                sums[i] += v
        return [s / float(length) for s in sums]

    train_X_baseline = [aggregate_sequence(s) for s in train_seq]
    val_X_baseline = [aggregate_sequence(s) for s in val_seq]
    test_X_baseline = [aggregate_sequence(s) for s in test_seq]

    # Baseline classifier
    baseline_model = StaticBaselineClassifier(input_dim=len(train_X_baseline[0]))
    train_classifier(
        baseline_model,
        train_X_baseline,
        train_labels,
        val_X_baseline,
        val_labels,
        epochs=30,
        lr=0.1,
    )
    baseline_accuracy = evaluate_classifier(baseline_model, test_X_baseline, test_labels)

    baseline_run = {
        "variant": "baseline",
        "workload_id": workload_id,
        "run_id": "baseline-" + workload_id,
        "success": True,
        "metrics": {"accuracy": float(baseline_accuracy)},
    }

    # Treatment: simple sequence model
    input_dim = len(train_seq[0][0])
    treatment_model = SimpleSequenceModel(input_dim=input_dim, hidden_dim=8)
    train_classifier(
        treatment_model,
        train_seq,
        train_labels,
        val_seq,
        val_labels,
        epochs=30,
        lr=0.05,
    )
    treatment_accuracy = evaluate_classifier(treatment_model, test_seq, test_labels)

    treatment_run = {
        "variant": "treatment",
        "workload_id": workload_id,
        "run_id": "treatment-" + workload_id,
        "success": True,
        "metrics": {"accuracy": float(treatment_accuracy)},
    }

    return [baseline_run, treatment_run]


def run_wl2() -> list:
    """Run baseline and treatment for WL-2 (graph context)."""
    workload_id = "WL-2-MultiLink-Topology-Context"

    set_global_seed(43)
    train_nodes, train_labels, val_nodes, val_labels, test_nodes, test_labels = (
        generate_wl2_graph_dataset()
    )

    # Each sample: (local_features, neighbor_features)
    train_local = [n[0] for n in train_nodes]
    val_local = [n[0] for n in val_nodes]
    test_local = [n[0] for n in test_nodes]

    # Baseline on local features only
    baseline_model = StaticBaselineClassifier(input_dim=len(train_local[0]))
    train_classifier(
        baseline_model,
        train_local,
        train_labels,
        val_local,
        val_labels,
        epochs=40,
        lr=0.1,
    )
    baseline_accuracy = evaluate_classifier(baseline_model, test_local, test_labels)

    baseline_run = {
        "variant": "baseline",
        "workload_id": workload_id,
        "run_id": "baseline-" + workload_id,
        "success": True,
        "metrics": {"accuracy": float(baseline_accuracy)},
    }

    # Treatment: graph context model uses local + neighbor aggregated features
    treatment_model = GraphContextModel(
        local_dim=len(train_nodes[0][0]), neighbor_dim=len(train_nodes[0][1])
    )
    train_classifier(
        treatment_model,
        train_nodes,
        train_labels,
        val_nodes,
        val_labels,
        epochs=40,
        lr=0.05,
    )
    treatment_accuracy = evaluate_classifier(treatment_model, test_nodes, test_labels)

    treatment_run = {
        "variant": "treatment",
        "workload_id": workload_id,
        "run_id": "treatment-" + workload_id,
        "success": True,
        "metrics": {"accuracy": float(treatment_accuracy)},
    }

    return [baseline_run, treatment_run]


def run_wl3() -> list:
    """Run baseline and treatment for WL-3 (rare events + autoencoder)."""
    workload_id = "WL-3-Rare-Attack-Events"

    set_global_seed(44)
    (
        train_X,
        train_labels,
        val_X,
        val_labels,
        test_X,
        test_labels,
    ) = generate_wl3_rare_events_dataset()

    # Baseline classifier trained on all data
    baseline_model = StaticBaselineClassifier(input_dim=len(train_X[0]))
    train_classifier(
        baseline_model,
        train_X,
        train_labels,
        val_X,
        val_labels,
        epochs=50,
        lr=0.1,
    )
    baseline_accuracy = evaluate_classifier(baseline_model, test_X, test_labels)

    baseline_run = {
        "variant": "baseline",
        "workload_id": workload_id,
        "run_id": "baseline-" + workload_id,
        "success": True,
        "metrics": {"accuracy": float(baseline_accuracy)},
    }

    # Treatment: autoencoder-style detector trained only on negatives
    treatment_model = SimpleAutoencoderDetector(input_dim=len(train_X[0]), hidden_dim=8)
    threshold = train_autoencoder_detector(
        treatment_model,
        train_X,
        train_labels,
        val_X,
        val_labels,
        epochs=50,
        lr=0.05,
    )
    treatment_accuracy = evaluate_autoencoder_detector(
        treatment_model, threshold, test_X, test_labels
    )

    treatment_run = {
        "variant": "treatment",
        "workload_id": workload_id,
        "run_id": "treatment-" + workload_id,
        "success": True,
        "metrics": {"accuracy": float(treatment_accuracy)},
    }

    return [baseline_run, treatment_run]


def main() -> int:
    runs = []

    # Execute workloads
    runs.extend(run_wl1())
    runs.extend(run_wl2())
    runs.extend(run_wl3())

    evidence = {
        "chapter": CHAPTER,
        "experiment_id": EXPERIMENT_ID,
        "environment": {
            "os": platform.platform(),
            "python": sys.version.split()[0],
        },
        "runs": runs,
        "notes": (
            "Synthetic, dependency-free approximation of Chapter 9 temporal "
            "and hybrid modeling experiment. Metrics are simple classification "
            "accuracies computed from lightweight models and datasets."
        ),
    }

    path = get_evidence_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, sort_keys=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
