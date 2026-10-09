# Domain matrix + wallet email gate (2026-07-22/23)

## Domains

| Domain | Login OTP | Create agent | Free $10 |
|---|---|---|---|
| `<REDACTED>` | ✅ | ✅ when not gated | ✅ proven later |
| `<REDACTED>` | ✅ | ✅ earlier / gated later | ✅ earlier samples |
| `<REDACTED>` | ✅ | often gated | 0 in later tests |
| `<REDACTED>` | ✅ | 403/429 under gate | 0 |

Prefer **`<REDACTED>`** for Virtuals ops batches.  
Webnovel may still treat <HANDLE_REDACTED> as retired for *Webnovel* creates — that is separate.

## Create gate (not auth)

Auth can fully succeed while create fails:

```text
OTP/wallet/verify/GET /agents = OK
POST /agents = 403 Forbidden then 429 Rate limit
retry-after ≈ 86392s (~24h)
```

Stop burning the proxy pool when many IPs show the same pattern.

## Wallet-only free credit gate

Wallet SIWE can create agents, but console enable is email-gated:

```text
POST /agents/{id}/console
→ 403 Please link an email to your account before creating a Console agent
compute remains limit=0
```

Free $10 path remains:

```text
email OTP (or email linked) → create agent → POST /console hermes+personal_assistant → compute/account limit=10
```

## Ops layout reminder

```text
.env            secrets only
data/proxy.txt  proxies
api.txt         only done_$10 keys
tmp_wallet_create/  temp wallet probes; do not touch vbcli mid-batch
```
