from __future__ import annotations

from typing import List, Dict, Any


def count_labels(rows: List[Dict[str, Any]], label_key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for r in rows:
        label = r.get(label_key)
        if label is None:
            continue
        counts[label] = counts.get(label, 0) + 1
    return counts
