---
name: x-account-registration
description: "Automate X/Twitter account registration (CLI-first) — onboarding task flow, js_instrumentation, x-client-transaction-id, Arkose FunCaptcha, email OTP, skip-phone policy."
version: 0.1.0
author: spring
platforms: [linux]
metadata:
  hermes:
    tags: [X, Twitter, signup, register, Arkose, FunCaptcha, onboarding]
    related_skills: [captcha-manager, x-premium-gift, browserless-web-automation, email-link-registration-automation]
---

# X / Twitter Account Registration

Use when building or debugging **X (Twitter) account creation** automation — CLI mass register, onboarding API, FunCaptcha/Arkose, email verification, phone-skip policy.

Canonical WIP project: `/root/x-autoreg` (`register.py`, `captcha_arkose.py`, `probe_jf_api.py`).

**Archive status (2026-07-21):** paused by user — resume only on explicit “lanjutkan / gas” for X. Prefer mobile HTTP Canary/HAR path next; web JF email is app/phone pivot under SKIP_PHONE.

## User defaults (Dez)

| Item | Policy |
|------|--------|
| Email | Same catch-all domain as Webnovel (`<REDACTED>`) |
| Phone | **Skip** if X requires SMS/phone — do not buy numbers unless user says otherwise |
| Proxy | Prefer **Webshare** for X probes; webnovel list backup — “sama aja” ≠ always WN DC |
| IMAP | **`/root/cf-tuyul/.env`** (same Webnovel/GitHub); empty local `IMAP_PASS` is normal |
| Interface | **CLI first**; TG bot only if explicitly requested |
| Captcha | FunCaptcha/Arkose only **after** Signup leaves 366; do not burn solvers earlier |

## Proven building blocks (2026-07-20)

1. **Guest token**  
   `POST https://api.twitter.com/1.1/guest/activate.json`  
   Bearer: public web bearer  
   Header: `x-client-transaction-id` recommended

2. **Begin signup flow**  
   `POST .../1.1/onboarding/task.json?flow_name=signup`  
   Returns `flow_token` + subtask graph including:
   - `Signup`, `SignupSettingsListEmailNonEU`, `SignupReview`
   - `ArkoseEmail` / `ArkosePhone`
   - `EmailVerification` / `PhoneVerification`

3. **`x-client-transaction-id` (mandatory for modern X API)**  
   - Package: `XClientTransaction` / `x_client_transaction.ClientTransaction`
   - Needs homepage HTML (`meta[name=twitter-site-verification]`) + ondemand JS URL from page
   - Generate per request: `generate_transaction_id(method, path)`  
   - Browser traffic includes this on guest activate / onboarding

4. **`js_instrumentation` (mandatory before Signup submit)**  
   - Fetch: `https://twitter.com/i/js_inst?native=true&native_js=true`
   - Script computes `{rf: {...}, s: "..."}` then does `window.location = "/?result=" + JSON.stringify(...)`
   - **Node alone fails** (`window is not defined`); evaluate in Playwright
   - Capture result by rewriting `window.location = "/?result=" + JSON.stringify(` → `window.__JS_INST_RESULT = (`
   - Pass as `sign_up.js_instrumentation.response` = **JSON string** of that object

5. **Captcha type on email path**  
   - Subtask `ArkoseEmail` → `web_modal.url` on `mobile.twitter.com/i/ocf_arkose_challenge`
   - Query has `data=` blob; public key often env `X_ARKOSE_PUBLIC_KEY` (may rotate)
   - Solver: FunCaptcha task (not reCAPTCHA). Prefer proxy-bound when register uses proxy.  
   - Module sketch: `/root/x-autoreg/captcha_arkose.py`

## APK reverse 2026-09-07 (X 12.23.1-prod.01) — CONFIRMED structures

APK: `/root/x-autoreg/X_12.23.1-prod.01_APKPure.xapk` → extract → jadx semua dex
(`/root/x-autoreg/apk_extracted/dex_splits/jadx_classes*/`).

### Retrofit API interface — `com/x/http/k.java`
```
POST /1.1/onboarding/task.json               (TaskRequest → TaskResponse)
POST /1.1/onboarding/begin_verification.json (BeginVerificationRequest → BeginVerificationResponse)
GET  /i/users/email_available.json?email=&lang= → EmailAvailableResponse
```
Base URL modern: `https://api.x.com/` (bukan api.twitter.com).

### Thrift JSON field names (dari Moshi JsonAdapter — PASTI snake_case)
```
TaskRequest:            flow_name, flow_token, subtask_inputs, input_flow_data, sim_country_code, subtask_versions
SignupInput:            link, name, email, phone_number, birthday(OcfDate), js_instrumentation, ignore_birthday
EnterEmailInput:        link, email, discoverability_value, setting_responses
EmailVerificationInput: link, code, email
BeginVerificationRequest: flow_token (REQUIRED), display_name, email, phone
```

### Login client location (obfuscated, method decompile gagal)
`com/x/login/core/w0.java` (task executor), `com/x/login/subtasks/signup/`, `enteremail/`, `phoneverification/`.

### Live probe (2026-09-07)
- Guest activate ✅ butuh GET x.com dulu (cookie guest_id) sebelum POST activate.
- Bearer web chunk = sama dgn register.py (`...AGWWjCpTnA`).
- `task.json?flow_name=signup` → 366 "flow name signup:no_employee is currently not accessible"
  = flow di-lock untuk guest tanpa device signal/attestation. App kirim device attestation
  (`AttestationInput`/`AppAttestationSubtask` ada di thrift) — ini gap utama web vs app.
- Flow probe matrix (guest, tanpa attestation): `signup` → 366 BLOCKED;
  `login` → 500 internal (code 131); no-flow-name / empty → 200 tapi subtasks kosong;
  nama flow asal (`signup_flow`, `create_account`, `registration`) → 366 "no flow by name".
  Server cuma gate flow `signup` yang asli; jangan kejar nama flow tebakan.
- **Attestation = Play Integrity / hardware keystore** — bukan header yang bisa
  di-spoof dari Python murni. Bypass "kaya daftar di Android" butuh app beneran:
  emulator + Frida hook `AttestationSubtask`, atau HAR dari device asli.

## Current blockers (do not claim E2E success)

As of **2026-07-26** tested Google SSO path end-to-end:

| Path | Result |
|------|--------|
| Google SSO web flow (CloakBrowser) | ✅ reaches phone gate |
| Google email/password | ✅ |
| Workspace ToS (first login) | ✅ click "Saya memahami" |
| OAuth consent (Indonesian "Lanjutkan") | ✅ |
| Redirect back to X | ✅ |
| DOB modal (signup_dob) | ✅ select adult DOB via `<select>` |
| Discoverability gate | ✅ click "Tidak sekarang" (clear cookie banner first) |
| **Phone gate** | ❌ "Masukkan nomor telepon Anda" — terminal if SKIP_PHONE |
| auth_token / ct0 cookie check | ❌ never reached — phone gate blocks |

**Web create methods (2026-07-26 recheck):**
| Method | Web result |
|---|---|
| Phone SMS | ✅ |
| Google SSO | ✅ — reaches onboarding but phone-gated |
| Apple SSO | ✅ (presumed, untested) |
| Email OTP full in browser | ❌ |
| Custom domain email-only | ❌ |

### Google SSO onboarding steps (in order)
1. `signup_dob` — "Kapan ulang tahun anda?" — select adult DOB
2. `discoverability_gate` — "Hubungkan dengan teman yang Anda kenal" — click "Tidak sekarang"
   *Trap: cookie banner covers button; accept cookies first*
3. `phone_gate` — "Masukkan nomor telepon Anda" — terminal

### Google OAuth button locale (Indonesian)
- Accept cookies: "Terima semua kuki"
- Next/Continue: "Berikutnya"
- I understand: "Saya memahami"
- Continue (consent): "Lanjutkan"
- Not now: "Tidak sekarang"

### Google SSO pitfalls
- Cookie banner overlaps modal buttons — always accept cookies before clicking modal CTAs
- Google popup closes quickly after password submit — always poll `context.pages` for the X page
- `page.evaluate` on a closed Google page throws `TargetClosedError` — guard with `p.is_closed()`
- OAuth consent button text varies by locale (Indonesian "Lanjutkan" vs English "Continue")
- **Phone gate is terminal** for skip-phone policy — no workaround found

### Archived paths (2026-07-21)
| Path | Result |
|------|--------|
| Guest + begin + js_inst + txid | ✅ |
| API `Signup` submit (email) | ❌ still **`366 Missing data`** |
| JF API `/i/jfapi/onboarding/web*` | binary/protobuf blobs |
| Email OTP full in browser | ❌ app-pivot only |

**Mobile UI (user screenshots):** email path still exists (“Masukkan alamat email Anda” + verification code). Plain HTTP Canary on `com.twitter.android` often fails SSL pin — need Frida/root or HAR from patched device.

**VPS note:** ~8GB RAM / ~16GB free / no swap — OK for static APK reverse + HAR analysis; **tight** for full Android emulator while production bots run.

Until that changes, **do not report mass register as working**.  
See `references/366-resume-2026-07-21.md`, `references/web-support-matrix-2026-07.md`, `references/web-jf-api-catalog-2026-07.md`, vault `Research/X Web JF API Catalog.md`.

## CLI shape (desired)

```bash
cd /root/x-autoreg
# hermes venv has playwright + XClientTransaction
PYTHONPATH=. /usr/local/lib/hermes-agent/venv/bin/python3 register.py 1
python register.py 3 --delay 60
```

Outputs (when success exists):
- `accounts.txt` → `email:password:user_id:username`
- `sessions/<email>.json` → cookies (`auth_token`, `ct0`) + proxy

## Recommended next reverse steps

1. **Do not thrash web JF** hoping email-OTP returns — recheck already consistent.
2. Prefer **mobile email capture**: HTTP Canary/Frida HAR of app email signup (user screenshots prove email OTP UI).
3. Or static APK reverse (`jadx`) for onboarding endpoints if traffic pinned.
4. Diff mobile/browser HAR vs classic `Signup` payload if classic path still used anywhere.
5. Confirm Arkose public key from live modal only after Signup advances past 366 / mobile challenge.
6. After email OTP: password → username → save cookies (mirror Webnovel sticky-session pattern).

## Pitfalls

- **Login docs ≠ signup** — `twitter-api-client` login flow (`LoginJsInstrumentationSubtask`) is different from `Signup`.
- **Empty `{}` js_inst fails** — must execute real `js_inst` blob.
- **Proxyless FunCaptcha** may fail if signup is proxied (same class of bug as Webnovel `11306`).
- **Phone-first / app-pivot UI** is product policy on tested nets, not a flaky clicker bug.
- **Custom domain is not specially blocked on web** — Gmail/Outlook unknown emails get the same app/phone pivot.
- **Do not loop SMS solvers** when user said skip phone.
- **Dual domain cookies** (`.x.com` / `.twitter.com`) can confuse cookie jars — prefer explicit domain or `get_dict()`.
- **Plain Canary on stock X APK** often fails SSL pin — “ga bisa” is expected without Frida/root.
- User archived X until free time — only resume on explicit lanjut/gas.

## References

- `references/apk-jadx-reverse-workflow.md` — reusable APK→endpoint reverse recipe: jadx `JADX_OPTS` trap, per-dex decode, Retrofit + Moshi `*JsonAdapter` mining for wire field names, guest-token ordering, static-vs-runtime caveats
- `references/x-signup-flow-2026-07.md` — live reverse notes, headers, subtasks, blockers
- `references/366-resume-2026-07-21.md` — still 366 on direct+Webshare
- `references/web-support-matrix-2026-07.md` / vault `Research/X Web Signup Support Matrix.md`
- `references/web-jf-api-catalog-2026-07.md` / vault `Research/X Web JF API Catalog.md`
- `references/mobile-capture-notes.md` / `references/resume-priority.md`
- `references/google-sso-x-onboarding-flow-2026-07.md` — Google SSO full flow to phone gate (2026-07-26)
- Companion: `captcha-manager` — key ranking / FunCaptcha provider notes
- Companion: `x-premium-gift` — X cookies/session patterns for *post-auth* product actions (not signup)

## Related overlap note

`x-premium-gift` covers gifting with existing cookies; this skill covers **account creation**. Keep separate.
