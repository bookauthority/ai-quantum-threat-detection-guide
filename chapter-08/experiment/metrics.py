from __future__ import annotations

from typing import Dict, Iterable, List, Tuple


def confusion_counts(y_true: Iterable[int], y_pred: Iterable[int]) -> Tuple[int, int, int, int]:
    tp = fp = tn = fn = 0
    for yt, yp in zip(y_true, y_pred):
        if yp == 1 and yt == 1:
            tp += 1
        elif yp == 1 and yt == 0:
            fp += 1
        elif yp == 0 and yt == 0:
            tn += 1
        elif yp == 0 and yt == 1:
            fn += 1
    return tp, fp, tn, fn


def basic_binary_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, float]:
    tp, fp, tn, fn = confusion_counts(y_true, y_pred)
    total = tp + fp + tn + fn
    if total == 0:
        accuracy = 0.0
    else:
        accuracy = float(tp + tn) / float(total)

    if tp + fp == 0:
        precision = 0.0
    else:
        precision = float(tp) / float(tp + fp)

    if tp + fn == 0:
        recall = 0.0
    else:
        recall = float(tp) / float(tp + fn)

    attack_rate = float(tp + fn) / float(total) if total > 0 else 0.0

    return {
        "accuracy": float(accuracy),
        "precision_attack": float(precision),
        "recall_attack": float(recall),
        "attack_rate": float(attack_rate),
    }
