# Customer Identity and Privacy

Policy owner: Privacy Office. Version 2025.1. Effective 2025-01-01.

Order lookup requires an order reference or a sufficiently verified customer identifier. Names alone are not unique and must not be used to select a customer record. Email comparison may be case-normalized, but duplicate customer rows remain a data-quality signal and should be disclosed in the internal trace.

Responses must minimize personal data. The chat interface may show the matched order reference, source system, status, amount, and relevant timestamps, but should not expose full addresses, payment details, credentials, or unrelated customer records. If identity is ambiguous, the system must ask for verification or escalate rather than guess.

