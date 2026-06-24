"""Clear Zooplus alert spam state after a bad scrape run."""
from __future__ import annotations

import json
from pathlib import Path

STATE = Path(__file__).resolve().parent.parent / "state.json"


def scrub(entry: dict) -> None:
    entry.pop("last_alert_price", None)
    for alt in entry.get("alternatives", {}).values():
        if isinstance(alt, dict):
            alt.pop("last_alert_price", None)
    for mp in entry.get("multipacks", {}).values():
        if isinstance(mp, dict):
            mp.pop("last_alert_unit_price", None)
            mp.pop("last_alert_price", None)


def main() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    touched = 0
    for key, entry in state.items():
        if not isinstance(entry, dict) or not key.endswith("|zooplus"):
            continue
        before = json.dumps(entry, sort_keys=True)
        scrub(entry)
        if json.dumps(entry, sort_keys=True) != before:
            touched += 1
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Cleared Zooplus alert markers on {touched} state entries")


if __name__ == "__main__":
    main()
