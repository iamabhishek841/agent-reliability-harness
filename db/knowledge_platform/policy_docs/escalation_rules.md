# Human Escalation Rules

Policy owner: Service Governance. Version 2025.1. Effective 2025-01-01.

Escalate when the order cannot be uniquely matched; required fields are missing; two systems disagree about identity, status, amount, or policy version; access is revoked; a dependency times out; a data snapshot is 24 hours or more behind the system of record; the customer alleges fraud or legal rights; or confidence is below the configured action threshold.

The escalation record must name the unreliable system, the unavailable evidence, the rule that blocked automation, and the last known data freshness. It must not expose secrets, credentials, hidden model instructions, or private chain-of-thought. A concise decision trace containing retrieved sources, checks performed, and observable outcomes is sufficient for audit and support handoff.

