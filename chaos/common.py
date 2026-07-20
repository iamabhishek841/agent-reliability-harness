import json
from datetime import UTC, datetime
from pathlib import Path

STATE = Path(__file__).with_name("state.json")
DEFAULT = {"latency": {}, "revoked": [], "stale_hours": {}, "updated_at": None}


def load() -> dict:
    if not STATE.exists():
        return dict(DEFAULT)
    try:
        return {**DEFAULT, **json.loads(STATE.read_text(encoding="utf-8"))}
    except json.JSONDecodeError:
        return dict(DEFAULT)


def save(state: dict) -> None:
    state["updated_at"] = datetime.now(UTC).isoformat()
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(STATE)

