# Captcha Provider Debugging — GMGN Auto-Create (session 2026-08-06)

Real debugging transcript from hardening `/root/gmgn-bot/gmgn_autocreate.py`.
All facts below were observed live; keep this as a reference for diagnosing
"captcha won't solve" on this bot.

## Balance state at debugging time (~/.hermes/.env)

| Var | Key prefix | Balance | Verdict |
|-----|-----------|---------|---------|
| TWOCAPTCHA_API_KEY | `82d7c3c7…` | −$0.00126 | dead |
| TWOCAPTCHA_API_KEY_2 | `54081d9b…` | $0.088–0.124 | **WORKS** |
| TWOCAPTCHA_API_KEY_3 | `b9d54eed…` | $1.50 | **FAILS solve** (ERROR_CAPTCHA_UNSOLVABLE) |
| TWOCAPTCHA_API_KEY_4 | `f11f25a7…` | −$0.00146 | dead |
| TWOCAPTCHA_API_KEY_5 | `12787446…` | −$0.00041 | dead |
| TWOCAPTCHA_API_KEY_6 | `8673ea9a…` | −$0.00067 | dead |
| CAPSOLVER_API_KEY | `CAP-FE3471…` | $0.0001 | nearly dead |
| CAPSOLVER_API_KEY_2 | `CAP-143B25…` | $0 | dead |
| CAPSOLVER_API_KEY_3 | `CAP-742B0F…` | $6.66 | usable |
| CAPSOLVER_API_KEY_4 | `CAP-BD4876…` | $38.93 | **winner** |

Lesson: **a $1.50 2captcha key can be worse than a $0.09 key.** Balance alone
does not predict solve success. The bot must try keys until one returns a token.

## Failure modes observed

1. **`ERROR_CAPTCHA_UNSOLVABLE`** (`{"status":0,"request":"ERROR_CAPTCHA_UNSOLVABLE","error_text":"Workers could not solve the Captcha"}`)
   - Happens per-key; retrying the SAME key does not help.
   - Fix: move to the next key; do not loop the same key.
2. **Capsolver `HTTP Error 400`** — selecting the $0.0001 key (first "positive")
   then `createTask` fails. Fix: select max balance.
3. **`{"code":-100016,"message":"invalid login message"}`** — SIWE signature
   encoded base64 instead of base58 (see SKILL.md pitfalls).
4. **Timeout on `getTaskResult` / `res.php`** — provider queue is slow. Batch
   runs with `timeout 400-550` foreground may be cut; run batch in background
   (`terminal background=true, notify_on_complete=true`) instead of waiting.

## The enterprise trap (cost ~6 wasted runs)

HAR showed `recaptcha/enterprise/*` URLs → assumed reCAPTCHA Enterprise →
added `enterprise=1` (2captcha) + `ReCaptchaV2EnterpriseTaskProxyLess`
(Capsolver) → **ALL keys failed**, including ones that worked 10 minutes prior.
GMGN actually renders the standard v2 checkbox; the `/enterprise/` paths are
just the CDN host. Reverting to plain `userrecaptcha` + `ReCaptchaV2TaskProxyLess`
restored success.

## Final working architecture (in script)

```
solve_recaptcha(sitekey, action=None, retries=3)
  for attempt in 1..3:
    _solve_recaptcha_once():
      token = _solve_2captcha()          # all keys, balance desc, deduped, 60s each
      if token: return token
      return _solve_capsolver()          # max-balance key, ReCaptchaV2TaskProxyLess, 180s
    if token: return token
```

- `load_captcha_keys()` returns positive-balance keys sorted desc, **deduped**
  (env vars `_N` can hold duplicate values → same key tried 3× otherwise).
- `load_env()` reads bot-folder `.env` first, then merges `~/.hermes/.env`
  for both `TWOCAPTCHA_API_KEY*` and `CAPSOLVER_API_KEY*` (initial bug: only
  TWOCAPTCHA fell through, so Capsolver keys were invisible → "Capsolver key
  tidak ada di .env").

## Verified end-to-end result

After fixes: `bash batch.sh 1 --no-wait` → account created
(`GLQhBonU…`), captcha page solved by key `54081d9b…` after `b9d54eed…`
failed, register captcha solved by Capsolver after both 2captcha keys failed,
follow of 2 target wallets OK, saved to `accounts/gmgn_accounts.json`
(5 accounts total at end of session).
