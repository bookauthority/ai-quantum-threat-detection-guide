import random
from typing import List, Tuple

from .utils import set_global_seed


def _split_dataset(X, y, train_ratio: float, val_ratio: float):
    n = len(X)
    indices = list(range(n))
    random.shuffle(indices)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)
    train_idx = indices[:train_end]
    val_idx = indices[train_end:val_end]
    test_idx = indices[val_end:]

    def sel(idxs):
        return [X[i] for i in idxs], [y[i] for i in idxs]

    X_train, y_train = sel(train_idx)
    X_val, y_val = sel(val_idx)
    X_test, y_test = sel(test_idx)
    return X_train, y_train, X_val, y_val, X_test, y_test


def generate_wl1_temporal_dataset(
    n_samples: int = 300,
    seq_len: int = 20,
    n_features: int = 4,
) -> Tuple[List[List[List[float]]], List[int], List[List[List[float]]], List[int], List[List[List[float]]], List[int]]:
    """Synthetic temporal dataset for WL-1.

    Each sequence is length `seq_len` of `n_features` floats.
    Label 1 indicates an "attack" window with elevated mean on some features.
    """
    set_global_seed(100)
    X: List[List[List[float]]] = []
    y: List[int] = []

    for i in range(n_samples):
        is_attack = 1 if i % 2 == 0 else 0  # balanced classes, deterministic
        base_level = 0.0 if not is_attack else 1.0
        seq: List[List[float]] = []
        for t in range(seq_len):
            step = []
            for f in range(n_features):
                noise = random.gauss(0.0, 0.3)
                value = base_level + noise
                # inject temporal variation for attacks
                if is_attack and t > seq_len // 2 and f == 0:
                    value += 0.5
                step.append(value)
            seq.append(step)
        X.append(seq)
        y.append(is_attack)

    X_train, y_train, X_val, y_val, X_test, y_test = _split_dataset(X, y, 0.6, 0.2)
    return X_train, y_train, X_val, y_val, X_test, y_test


def generate_wl2_graph_dataset(
    n_nodes: int = 400,
    feature_dim: int = 3,
    neighbor_dim: int = 2,
):
    """Synthetic graph-style dataset for WL-2.

    Each sample is (local_features, neighbor_agg_features).
    Label depends on linear combination of both local and neighbor features.
    """
    set_global_seed(101)
    nodes = []
    labels: List[int] = []

    for i in range(n_nodes):
        local = [random.gauss(0.0, 1.0) for _ in range(feature_dim)]
        neighbor = [random.gauss(0.0, 1.0) for _ in range(neighbor_dim)]
        score = sum(local) + 0.8 * sum(neighbor)
        label = 1 if score > 0.5 else 0
        nodes.append((local, neighbor))
        labels.append(label)

    X_train, y_train, X_val, y_val, X_test, y_test = _split_dataset(nodes, labels, 0.6, 0.2)
    return X_train, y_train, X_val, y_val, X_test, y_test


def generate_wl3_rare_events_dataset(
    n_samples: int = 500,
    feature_dim: int = 5,
):
    """Synthetic imbalanced dataset for WL-3.

    Majority class 0 with one distribution; rare class 1 with shifted mean.
    """
    set_global_seed(102)
    X = []
    y: List[int] = []

    # About 5% positives
    n_pos = max(1, n_samples // 20)
    n_neg = n_samples - n_pos

    for _ in range(n_neg):
        vec = [random.gauss(0.0, 1.0) for _ in range(feature_dim)]
        X.append(vec)
        y.append(0)

    for _ in range(n_pos):
        # rare events shifted in one direction
        vec = [random.gauss(1.5, 1.0) for _ in range(feature_dim)]
        X.append(vec)
        y.append(1)

    X_train, y_train, X_val, y_val, X_test, y_test = _split_dataset(X, y, 0.6, 0.2)
    return X_train, y_train, X_val, y_val, X_test, y_test
