# Chaos controls

Run from the repository root while the stack is live:

```bash
python chaos/inject_latency.py --system legacy_crm --seconds 6
python chaos/revoke_access.py --system legacy_crm
python chaos/stale_sync.py --system knowledge_platform --hours 24
python chaos/reset.py
```

The backend reads `chaos/state.json` on every integration call. The file is gitignored, mounted into the container, and written atomically. A latency at or above `INTEGRATION_TIMEOUT_SECONDS`, revoked access, or 24-hour stale state must produce an escalation instead of an action.

