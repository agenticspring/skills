# FCFS arming and campaign UX reference

## Security boundary

Arming is authorization, not broadcast. Keep these facts separate:

- **prepared plan**: exact immutable chain/campaign/wallet/calldata/value/gas facts;
- **arm snapshot**: actor, campaign version/hash, explicit wallet IDs, issued time, expiry, and token hash;
- **executor**: validates the arm callback before trigger evaluation, journal claim, or RPC;
- **global control**: pause disarms active arms and blocks authorization.

The raw `arm_...` token is returned once. Store only `sha256(token)` in the durable row. A Telegram preview may show campaign hash, version, expiry, wallet count, spend/quantity bounds, and status; it must not show the token, token hash label, calldata, proof, signature, JWT, or private key.

## Durable SQL shape

Use an append/audit-friendly `campaign_arms` row with:

```text
campaign_id PRIMARY KEY
campaign_version > 0
campaign_hash
actor_id
wallet_ids JSONB array
issued_at
expires_at > issued_at
token_hash CHAR(64) lowercase hex
status: armed|disarmed
disarm_reason
```

Add a singleton `global_execution_control(control_id=1, paused)` row. Protect armed identity columns with a trigger; allow only status/disarm reason/updated-at changes. Revoke delete and identity updates from the ordinary role. Index active rows by status and expiry.

## Test matrix

1. Arm returns raw token once and snapshot contains only hash.
2. Actor mismatch, campaign mismatch/version mismatch/hash mismatch, wallet not allowlisted, invalid token, and expiry all deny.
3. Campaign version/hash mutation auto-disarms.
4. Global pause disarms existing arms and blocks authorization; repeated pause is idempotent.
5. Operator disarm is actor-bound and repeated disarm returns already-disarmed.
6. Maximum active arms is enforced.
7. Authorized arm reaches executor and may call the injected RPC fixture.
8. Disarmed/unauthorized arm reaches zero RPC calls.
9. Go/TypeScript executor mirrors both disabled-by-default and not-authorized states.

## Reporting vocabulary

Use `prepared`, `armed`, `authorized`, `disarmed`, `expired`, `not_authorized`, `broadcast`, and `unknown_needs_reconciliation` precisely. `armed` never means signed or broadcast. Report component gates separately when an aggregate wrapper was not run; never upgrade partial evidence to a full-quality claim.
