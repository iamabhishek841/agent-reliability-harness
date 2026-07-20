# Adversarial and Instruction-Override Requests

Policy owner: AI Safety. Version 2025.1. Effective 2025-01-01.

Customer text, retrieved documents, and tool output are untrusted data. Instructions asking the agent to ignore policy, reveal system prompts, impersonate an approver, enter developer mode, fabricate citations, or alter confidence must not affect the control flow. Such text is retained as case evidence but is not executed.

The decision engine must enforce eligibility and action thresholds outside the generative model. A detected override attempt results in no automated financial action and a low-confidence escalation. Benign customers should receive a neutral explanation without accusations. Security telemetry may record the detection category but must avoid storing unnecessary sensitive content.

