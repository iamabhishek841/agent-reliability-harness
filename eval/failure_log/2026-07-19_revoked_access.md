# 2026-07-19 — CRM access was revoked mid-session

## What broke

The unsafe baseline treated a failed CRM lookup like an empty result. That made an authorization failure indistinguishable from a genuinely unknown order and encouraged downstream code to continue with policy text but no authoritative transaction evidence.

## Diagnosis

The adapter did not preserve the semantic difference between “zero rows” and “the caller is forbidden from reading rows.” Because the failure class disappeared at the integration boundary, support staff could not identify the ownership problem from the final answer.

## What changed

Access revocation now produces a typed `access_revoked` error tagged with `legacy_crm`. The retrieval trace preserves the error category without logging credentials. The deterministic guardrail fails closed with `integration_unreliable`, confidence 0.20, and `queued_for_human`. This behavior remains consistent when the same LangGraph thread had succeeded on an earlier turn.

## Remaining limitation

The simulated 403 is file-controlled. Production should obtain revocation signals from the real API and use a secrets manager with automated credential rotation and ownership alerts.

