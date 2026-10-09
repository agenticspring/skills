# Observation-only alerts and recommendations

## Contract

An observation is keyed by a stable domain key and carries source, value, observed timestamp, and checked timestamp. The alert state retains the latest observation, a deterministic value fingerprint, and the last emitted-alert timestamp.

```text
same key + same fingerprint                    -> suppressed / duplicate
changed fingerprint inside cooldown            -> suppressed / cooldown
changed fingerprint after cooldown              -> alert / material_change=true
missing value                                  -> INSUFFICIENT_DATA / missing
checked_at - observed_at > max_age              -> INSUFFICIENT_DATA / stale
```

Update retained state even when the observation is missing or stale. Do not convert fetch failures into a synthetic changed value.

## Recommendation output

A recommendation is data, not an execution command. It must include:

```text
status: ACTIONABLE_OBSERVATION | NOT_ACTIONABLE | INSUFFICIENT_DATA
key, source
inputs
observedAtMs, checkedAtMs, ageMs, maxAgeMs
confidence
rationale[]
invalidationCriteria[]
```

Typical reasons:

```text
missing
stale
price_above_limit
budget_exceeded
offer_below_floor
```

`ACTIONABLE_OBSERVATION` means the observed inputs satisfy the configured analytical constraints only. It does not mean an order is executable. A later fulfillment path must re-fetch/revalidate the exact order, ownership, approvals, criteria, gas, and budget.

## Side-effect boundary

Alert/recommendation modules must not import signer or executor modules and must expose no `sign`, `execute`, `broadcast`, or action callback. Bot formatters may show reasoning and invalidation criteria, but action arrays remain empty. Alert workers only pass observations to the alert engine.

## Test matrix

- first valid observation emits one alert;
- identical observation is duplicate-suppressed;
- material change inside cooldown is cooldown-suppressed;
- material change after cooldown emits;
- missing/stale observations return `INSUFFICIENT_DATA` and remain retained;
- threshold and budget failures return explicit `NOT_ACTIONABLE` reasons;
- recommendations include all explainability fields;
- module/API inspection proves no signer/executor side-effect surface;
- formatter does not include calldata/signatures and returns no actions.
