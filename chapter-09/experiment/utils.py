import json
import math
import os
import random
from typing import Any, List


def set_global_seed(seed: int) -> None:
    """Set global random seed for reproducibility.

    Uses Python's built-in random module only.
    """
    random.seed(seed)


def sigmoid(x: float) -> float:
    # Numerically stable-ish sigmoid
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(x)
        return z / (1.0 + z)


def dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def mse(a: List[float], b: List[float]) -> float:
    n = float(len(a))
    if n == 0.0:
        return 0.0
    return sum((x - y) ** 2 for x, y in zip(a, b)) / n


def save_json(obj: Any, path: str) -> None:
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
