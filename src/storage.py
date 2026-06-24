from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE_PATH = ROOT / "state.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state(path: Path | None = None) -> Dict[str, Any]:
    state_path = path or DEFAULT_STATE_PATH
    if not state_path.exists():
        return {}
    with state_path.open(encoding="utf-8") as f:
        return json.load(f)


def save_state(state: Dict[str, Any], path: Path | None = None) -> None:
    state_path = path or DEFAULT_STATE_PATH
    with state_path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_product_state(state: Dict[str, Any], product_key: str) -> Dict[str, Any]:
    return state.setdefault(product_key, {})


def update_product_state(
    state: Dict[str, Any],
    product_key: str,
    *,
    price: float,
    baseline_price: Optional[float],
    last_alert_price: Optional[float] = None,
) -> None:
    entry = get_product_state(state, product_key)
    entry["last_price"] = price
    entry["last_checked"] = _now_iso()
    if baseline_price is not None:
        entry["baseline_price"] = baseline_price
    if last_alert_price is not None:
        entry["last_alert_price"] = last_alert_price
