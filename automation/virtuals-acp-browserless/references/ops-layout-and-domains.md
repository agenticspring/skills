# Virtuals browserless ops layout + domains

## Layout
```text
/root/virtuals-browserless/
  vbcli.py
  .env                 # IMAP + DOMAIN only (no PROXY_URL)
  data/proxy.txt       # file-based proxy pool
  api.txt              # ONLY status done_$10 keys
  accounts.txt
  exports/
  tmp_wallet_create/   # isolated wallet SIWE probes — never edit live batch here
```

## Proxy policy
- Seed from `/root/webnovel-tg-bot/proxy.txt`
- On first 429: rotate proxy immediately
- On rotate: new email + new OTP (never reuse OTP)
- Persist rotation in `data/proxy.txt`, not `.env`

## Domain matrix (proven)
| Domain | Login | Create | $10 |
|---|---|---|---|
| <REDACTED> | OK | OK when gate open | proven |
| <REDACTED> | OK | early OK / later 403-429 | early yes |
| <REDACTED> | OK | gated | no |
| <REDACTED> | OK | gated | no |

Prefer `<REDACTED>` for farming after create-gate pressure.

## Credit path recap
Email OTP → wallet → refresh Privy session → ACP verify → create agent → **POST console hermes+personal_assistant** → poll compute/account → create key → append api.txt only if done_$10.

Wallet SIWE alone: create agent possible; console 403 without email linked → $0.

## Live key check
If user asks whether an `acp-...` key has balance/content:
1. `GET https://compute.virtuals.io/v1/models` with Bearer key
2. optional tiny chat completion
3. compare local result JSON / accounts row for email+agent_id
