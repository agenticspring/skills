# GitHub autoreg — E2E email + classic PAT (2026-07-21)

## IMAP (shared with Webnovel)
- Source of truth: **`/root/cf-tuyul/.env`**
- Keys: `IMAP_HOST`, `IMAP_PORT`, `IMAP_USER`, `IMAP_PASS` (app password, len ~19)
- `/root/webnovel-autoreg/.env` may list IMAP_USER but **IMAP_PASS empty** — still works for Webnovel because signup.py overrides from cf-tuyul
- github-autoreg `load_env()` must include cf-tuyul the same way
- User “pake sama webnovel” for mail = **cf-tuyul**, not invent new mailbox

### Mailbox quirks
- `LIST` may return Indonesian Gmail labels, e.g. `[Gmail]/Semua Email`, `[Gmail]/Spam`
- Selecting English `[Gmail]/All Mail` can fail: `BAD Could not parse command`
- Prefer: probe `LIST`, then `INBOX` + junk/spam equivalents; search `(TO "addr")` and `(TEXT "addr")` like Webnovel

## Email content after successful signup
- Subject: **`🚀 Your GitHub launch code`**
- From: `GitHub <noreply@github.com>`
- Body contains:
  - 8-digit launch code
  - Confirm URL: `https://github.com/account_verifications/confirm/<uuid>/<code>`
  - Alt: `https://github.com/account_verifications?verification=<uuid>&via_launch_code_email=true`

**Use the `/confirm/<uuid>/<code>` link** — more reliable than re-POSTing OTP to random forms on `/`.

## Login success checks
After confirm → `/login` → POST `/session`:
- Cookies: `logged_in`, `user_session`, `_gh_sess`, …
- HTML: `<meta name="user-login" content="<username>">` and/or `data-login="<username>"`
- Home must not be “Sign in” wall

## Classic PAT no-expiration
Form: `GET /settings/tokens/new` → `POST /settings/tokens`

### Proven create (works more reliably)
```
authenticity_token: <from form>
oauth_access[description]: nocaptcha-<user>-<ts>
oauth_access[default_expires_at]: none
oauth_access[custom_expires_at]: ""
# omit scopes first
```
Rebuild from form `<input>` list when possible; force expires to `none`; skip unchecked scope checkboxes.

Menu values: `7`, `30`, `60`, `90`, `custom`, **`none`**.

### Failures
- Missing/wrong expiration or incomplete form fields → **422** “Oh no · GitHub”
- Default hidden field may be `30` if UI not updated — must send **`none`** for non-expiring
- Sending scopes on some form states can also 422 — empty scopes are OK for public scrape

### Validation
```bash
curl -sD- -H "Authorization: token $TOK" -H "Accept: application/vnd.github+json" https://api.github.com/user | rg -i 'x-oauth-scopes|login'
curl -sH "Authorization: token $TOK" -H "Accept: application/vnd.github+json" https://api.github.com/rate_limit
```

### Spec check vs api-key-leak
| Need | Notes |
|---|---|
| classic `ghp_` | yes |
| no expiration | `default_expires_at=none` |
| public code search permission | empty scopes OK |
| high search/core quota | **not guaranteed** on new accounts |

### New-account limit reality (observed)
- Token valid, expiration none, scopes empty **or** with public_repo/read:user/user:email
- Still often **core limit 60**, **search limit 10**
- Code search may immediately rate-limit on aggressive queries
- Treat as “works but weak” until multiple aged tokens exist

## Artifact layout
```
accounts.txt          email:password:username:login_ok|login_ok_nocaptcha_pat|ok_pat:no_expiration
tokens.txt            ghp_…\tuser\temail\tno_expiration\tclassic\t…
sessions/<user>.json  cookies + proxy meta
logs/batch_screen.log batch progress (screen github-autoreg)
```

Optional: append `ghp_` to `/root/api-key-leak/data/tokens.txt` for harvester.
See `references/batch-ops.md` + `references/datadome-suppressed-path.md`.
