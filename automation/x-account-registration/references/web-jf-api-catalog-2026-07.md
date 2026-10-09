# X classic + Join Flow API catalog (2026-07)

Structural only — no secrets. Full vault twin: `Research/X Web JF API Catalog.md`.  
Code: `/root/x-autoreg` (`register.py`, `probe_jf_api.py`). Dumps: `data/jf_*`, `data/jf_act_*`.

## Classic onboarding (still responds)

Hosts: `api.twitter.com`, `api.x.com`, `twitter.com/i/api`, `x.com/i/api`.

| Method | Path | Result |
|--------|------|--------|
| POST | `/1.1/guest/activate.json` | guest_token OK |
| POST | `/1.1/onboarding/task.json?flow_name=signup` | flow_token + graph OK |
| POST | `/1.1/onboarding/task.json` (Signup) | **366 Missing data** |
| POST | `/1.1/onboarding/callback.json?...` | 200, does not fix 366 |
| POST | `/1.1/flow/viewer.json` | client_event 200, does not fix 366 |
| GET | `https://twitter.com/i/js_inst?native=true&native_js=true` | js_inst blob |

Graph may include: `Signup`, `SignupSettingsListEmail` (not only NonEU), `SignupReview`, `ArkoseEmail`/`ArkosePhone`, email/phone verification, SSO subtasks.

## Join Flow UI

```text
https://x.com/i/flow/signup → https://x.com/i/jf/onboarding/web?mode=signup
```

JF bodies: **binary custom blobs** (`text/plain`, often gzip) — not classic JSON task.

## JF endpoints (live)

Prefix: `https://x.com/i/jfapi` (also `twitter.com`).

| Path | Notes |
|------|--------|
| `GET/POST /i/jfapi/onboarding/web/landing` | landing blob |
| `GET /i/jfapi/onboarding/web?mode=signup` | signup landing |
| `GET /i/jfapi/onboarding` | larger route/string blob |
| `.../web/actions/begin_login` | needs username_or_email |
| `.../web/actions/begin_signup_phone` | phone path |
| `.../web/actions/begin_signup_sso` | Google/Apple |
| `.../web/actions/begin_signup_email` | **exists**; unknown email → app/phone pivot |
| `.../web/actions/begin_signup` | 404 |
| `.../onboarding/actions` (+ `?isPhone=`) | 400 Bad input (envelope unknown) |
| `.../actions/sso?ssoType=google\|apple` | 200 |
| `.../actions/resendcode` | 400 Bad input |
| `.../signup/verify_email` under jfapi | 404 in probes |

### begin_signup_email probe

```http
POST /i/jfapi/onboarding/web/actions/begin_signup_email
Content-Type: application/json
Authorization: Bearer <public web>
x-guest-token: <gt>
x-client-transaction-id: <txid>
Referer: https://x.com/i/jf/onboarding/web?mode=signup

{"email":"user@example.com"}
```

Same pivot for <HANDLE_REDACTED> / gmail / outlook.

### Common headers

```text
Authorization: Bearer <public web bearer in register.py>
x-guest-token
x-client-transaction-id
x-twitter-active-user: yes
Referer/Origin: https://x.com/...
chrome124-class UA
```

## Probe tooling

```bash
cd /root/x-autoreg
.venv/bin/python probe_jf_api.py
.venv/bin/python register.py 1   # classic path debug only
```
