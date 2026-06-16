from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "sample"


def load_json(filename: str) -> list[dict[str, Any]]:
    path = DATA_DIR / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []
