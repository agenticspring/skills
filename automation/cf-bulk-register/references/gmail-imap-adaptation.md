# Gmail IMAP adaptation of iAm-182/bluk-cf

The upstream repo verifies email via a temp-mail API (`src/email_generator.py`
+ `src/email_verifier.py`). To use a personal catch-all domain → Gmail, replace
that layer with IMAP polling.

## Files added / changed (in /root/bluk-cf)

### src/gmail_imap.py (NEW)
Drop-in IMAP fetcher. Key class `GmailIMAP`:
- `connect()` → `imaplib.IMAP4_SSL(imap_host).login(user, app_password.replace(" ",""))`
- `fetch_recent(target_email, since_ts, limit)` → searches UNSEEN, filters by `To:`
  header containing `target_email`, returns parsed dicts `{id, from, subject, to, text, html}`.
- `mark_seen(mail_id)` → sets `\Seen` flag.

### src/email_verifier_gmail.py (NEW)
`verify_cloudflare_email_gmail(page, email, gmail_user, gmail_app_password, imap_host, timeout, poll_interval)`:
- Reuses `extract_verification_link` from `email_verifier.py`.
- Polls GmailIMAP, opens the CF link in the same nodriver `page`, checks body for
  "verified"/"success" or redirect to dash.cloudflare.com (non-login).
- Returns `EmailVerifyResult(success, link)`.

### main.py (PATCHED)
In `create_account()`:
- Read `mail_mode = config.get("mail_mode", "temp_mail")`.
- If `gmail_imap`: `email = f"{username}@{random.choice(mail_domains)}"` (deterministic,
  no API call). Else legacy temp-mail path.
- At verify step: branch to `verify_cloudflare_email_gmail(...)` vs legacy.

In `uc.start(...)` call: add
```python
import os as _os
_chrome = _os.environ.get("CHROME_BIN", "/usr/bin/chromium-browser")
browser = await uc.start(headless=headless, lang="en-US", proxy=proxy,
    sandbox=False, browser_executable_path=_chrome,
    browser_args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage"])
```

### config.json (NEW)
Keys: `mail_mode:"gmail_imap"`, `gmail_user`, `gmail_app_password` (16-char app pw),
`imap_host:"imap.gmail.com"`, `mail_domains:["<REDACTED>"]`.

## Gotcha: .env format
Some setups store creds as `key: value` (colon) not `key=value`. Sync config.json
from it with a small python script rather than hand-editing twice.

## Failure mode to expect
With `mail_mode:"gmail_imap"` but the domain NOT yet set up in Cloudflare Email
Routing, signup reaches "✅ Turnstile solved" then fails:
`Signup failed: Redirect failed: https://dash.cloudflare.com/sign-up`
→ the form never leaves /sign-up because CF can't deliver/verify the email.
Fix: add domain to CF + enable catch-all → Gmail FIRST.
