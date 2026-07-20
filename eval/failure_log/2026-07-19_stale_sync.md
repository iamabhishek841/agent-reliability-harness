# 2026-07-19 — Policy knowledge lagged the CRM by 24 hours

## What broke

The baseline retrieved semantically relevant chunks without considering when the knowledge snapshot was synchronized. A recently changed policy could therefore be absent while the agent cited an older version with high confidence.

## Diagnosis

Similarity was being treated as sufficient retrieval quality. The chunk schema had policy content but the decision path did not use effective and synchronization timestamps as control inputs.

## What changed

Policy documents and chunks now store effective, retired, version, and synchronized timestamps. The chaos layer can move the knowledge view backward by a controlled number of hours. Retrieved chunks carry `stale_hours`; a lag of 24 hours or more produces `stale_policy_data`, confidence 0.35, and human escalation. The trace still shows which version was retrieved so an operator can diagnose the mismatch.

## Remaining limitation

The harness uses a single numeric lag. At scale, freshness should be measured per source partition and policy version, with change-data-capture watermarks and explicit consistency objectives.

