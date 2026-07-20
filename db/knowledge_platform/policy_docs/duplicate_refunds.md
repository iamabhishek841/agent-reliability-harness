# Duplicate Refund Prevention

Policy owner: Payments Risk. Version 2025.1. Effective 2025-01-01.

Before an action is submitted, the system must check the order status and refund-request history for an existing paid, accepted, pending, or under-review refund. A matching request blocks a second automated action. The action service must use the stable order reference as an idempotency key and return the original result on retries.

An orphaned refund record, inconsistent order identifier, or missing external order reference requires investigation. It must not be assumed to mean that no refund exists. Duplicate customer rows are resolved only through explicit order linkage and normalized email as supporting evidence, not by selecting the first name match.

