# Standard Refund Eligibility

Policy owner: Customer Operations. Version 2025.1. Effective 2025-01-01.

An order recorded as delivered or completed may receive an automated refund when the request is made within 30 calendar days of the delivery timestamp. The order must have a verifiable order reference, currency, amount, and delivery date. The refundable value must not exceed USD 1,000 or the local-currency equivalent. The order must not be marked final sale, regulated, disputed, subject to chargeback, or already refunded.

The system must cite the order record and at least one current policy source. If any required fact is absent, contradictory, older than the permitted freshness threshold, or supplied only by the customer without system confirmation, the request must be escalated. A confidence score is not a substitute for evidence. Automated approval is prohibited when an integration is unavailable.

