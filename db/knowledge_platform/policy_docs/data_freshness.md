# Data Freshness and Source Precedence

Policy owner: Enterprise Data. Version 2025.1. Effective 2025-01-01.

The legacy CRM is the system of record for customer, order, fulfillment, and refund-request facts. The knowledge platform is authoritative for published policy text and policy version. Each retrieved record must carry an updated or synced timestamp. A snapshot lag of 24 hours or more is materially stale for automated decisions.

When sources disagree, no model inference may reconcile the conflict silently. The workflow must identify the fields in conflict, prefer neither source outside its declared ownership, reduce confidence, and escalate. Cached policy content may be used for explanation during a short outage only when its version and effective dates are known; it may not authorize a payment action while freshness is unverified.

