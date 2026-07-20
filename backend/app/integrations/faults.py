import json
import os
import time
from pathlib import Path
from typing import Any


class IntegrationUnavailable(RuntimeError):
    def __init__(self, system: str, kind: str, message: str):
        super().__init__(message)
        self.system = system
        self.kind = kind


def _state_path() -> Path:
    configured = os.getenv("CHAOS_STATE_PATH")
    return Path(configured) if configured else Path(__file__).resolve().parents[3] / "chaos" / "state.json"


def read_fault_state() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return {"latency": {}, "revoked": [], "stale_hours": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"latency": {}, "revoked": [], "stale_hours": {}}


def apply_faults(system: str, timeout_seconds: float | None = None) -> int:
    state = read_fault_state()
    latency = float(state.get("latency", {}).get(system, 0.0))
    if latency > 0:
        if timeout_seconds is not None and latency >= timeout_seconds:
            time.sleep(min(timeout_seconds, 30.0))
            raise IntegrationUnavailable(system, "timeout", f"{system} exceeded the {timeout_seconds:.1f}s latency budget")
        time.sleep(min(latency, 30.0))
    if system in state.get("revoked", []):
        raise IntegrationUnavailable(system, "access_revoked", f"{system} returned HTTP 403")
    return max(0, int(state.get("stale_hours", {}).get(system, 0)))
