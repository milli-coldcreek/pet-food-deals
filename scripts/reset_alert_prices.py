"""Clear all last-alert markers so deals can fire again on the next run."""
from __future__ import annotations

import json
from pathlib import Path

STATE = Path(__file__).resolve().parent.parent / "state.json"


def scrub(entry: dict) -> int:
    cleared = 0
    if entry.pop("last_alert_price", None) is not None:
        cleared += 1
    for alt in entry.get("alternatives", {}).values():
        if isinstance(alt, dict) and alt.pop("last_alert_price", None) is not None:
            cleared += 1
    for mp in entry.get("multipacks", {}).values():
        if not isinstance(mp, dict):
            continue
        if mp.pop("last_alert_unit_price", None) is not None:
            cleared += 1
        if mp.pop("last_alert_price", None) is not None:
            cleared += 1
    return cleared


def main() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    cleared = 0
    for entry in state.values():
        if isinstance(entry, dict):
            cleared += scrub(entry)
    STATE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Cleared {cleared} last-alert marker(s) from state.json")


if __name__ == "__main__":
    main()
