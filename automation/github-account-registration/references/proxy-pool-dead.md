# Proxy pool dead for GitHub signup

## Signal
Batch log repeats for every account:
```text
proxy host:port signup status=403 ok=False
…
result={'ok': False, 'reason': 'no_proxy_opens_signup'}
BATCH DONE success=0/N
```

This is **not** captcha, IMAP, or PAT failure. Form never opens.

## Proven example
- Date: 2026-07-25
- Command: `batch_create.py 10 --delay 25` on domain `<REDACTED>`
- Result: **0/10** — all 10 proxies in `proxy.txt` returned signup GET **403**
- Screen `github-autoreg` exited after `BATCH DONE` (normal one-shot)

## Fix before rerun
1. Probe each candidate:
   - OK = HTTP 200 + `authenticity_token` + octocaptcha iframe present on `https://github.com/signup`
2. Prefer **Webshare** (or other GH-friendly residential) over Webnovel DC / ProxyScrape-style
3. Rewrite `github-autoreg/proxy.txt` with only form-OK proxies first
4. Optional: keep bad list aside; do not burn full batch on known-403 pool
5. Rerun batch only after ≥1 proxy opens form live

## Operator note
User may say leave batch in screen unattended — still **preflight proxy** when starting a new mass run if last log was all `no_proxy_opens_signup`.
