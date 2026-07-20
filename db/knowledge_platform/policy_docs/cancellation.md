# Cancellation Before Fulfillment

Policy owner: Fulfillment Operations. Version 2025.1. Effective 2025-01-01.

Orders may be cancelled automatically only before allocation to a fulfillment center. Processing, shipped, delivered, cancelled, chargeback, and fraud-review states are not eligible for automated cancellation through the refund workflow. A refund request for an undelivered order must be distinguished from a cancellation request.

When fulfillment state is unknown or stale, the agent must not promise cancellation. It should explain the uncertainty and escalate. Once delivery is confirmed, the standard refund policy applies. Orders already cancelled require no second payment action; duplicate cancellation or refund attempts must be detected through an idempotency key.

