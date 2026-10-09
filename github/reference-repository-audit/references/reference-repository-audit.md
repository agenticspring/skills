# Reference repository audit worksheet

## Source record

```text
URL:
Revision:
Branch:
Isolated checkout:
```

## Inventory

```text
Manifest/dependencies:
Entrypoints:
Wallet loading:
Scheduling:
Protocol adapters:
External APIs:
Auth/session:
```

## Irreversible-boundary scan

| Surface | Evidence | Classification | Reason/target boundary |
|---|---|---|---|
| Private-key loading |  | reject/adapt/diagnostic-only |  |
| Signing |  |  |  |
| Broadcast |  |  |  |
| Approval |  |  |  |
| Nonce/retry |  |  |  |
| Persistence/restart |  |  |  |
| JWT/session/cookies |  |  |  |
| GraphQL/persisted hashes |  |  |  |
| Allowlist fallback |  |  |  |
| RPC/HTML discovery |  |  |  |

## Useful patterns

- 

## Rejected patterns

- 

## Verification

```text
Native syntax check:
Runtime/build check (if safely possible):
Secrets/sessions/signatures/transactions used: no
Source/artifacts copied: none
```

## Decision

```text
adapt:
diagnostic-only:
defer:
reject:
next action:
```
