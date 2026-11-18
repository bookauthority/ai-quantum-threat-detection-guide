from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def write_evidence(path: Path, evidence: Dict[str, Any]) -> None:
    """Write evidence JSON atomically to the given path.

    The caller is responsible for constructing an object that conforms to
    the required runtime contract. This helper ensures safe writing.
    """

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2, sort_keys=True)
    tmp_path.replace(path)
