---
name: muse-meta-account-automation
description: Automate Muse.ai/Meta signup + invite redeem.
version: 1.0.0
author: spring
license: MIT
metadata:
  hermes:
    tags: [automation, playwright, meta, signup, invite-redeem, anti-bot]
    related_skills: [browserless-web-automation, stdlib-automation, email-link-registration-automation]
---

# Muse.ai (Meta) — Account Creation + Invite Redeem

## When to Use

- Creating Muse.ai accounts in bulk (farming / invite-redeem campaigns).
- Redeeming a Muse invite code across many fresh accounts.
- Debugging any Meta-native signup flow: hidden OTP input, `data-pel-click`
  buttons, the `auth.meta.com` card popup, or `403 csrfFailed`.
- Any Playwright job against `muse.ai` / `auth.meta.com`.

Do NOT use for generic browser automation — only the Meta/Muse flow and its
specific anti-bot quirks are covered here.

`muse.ai` is **Meta's AI agent product** (© Meta 2026), not a music tool. Auth is
Meta-native (`auth.meta.com`), heavily anti-bot. Working bot: `/root/projects/muse-bot/`
(`install.sh` / `setup.sh` / `run.sh` + `musebot_ui.py` engine).

## The 7-step flow (verified end-to-end)

```
1. email            input[placeholder*='email']  -> [data-pel-click='login_contact_continue_click']
2. 6-digit OTP      typed from email; input is class="sr-only"
3. name + birthday  TWO VARIANTS (see pitfalls)
4. disclosure       [data-pel-click='onboarding_disclosure_continue_click'] ("Get started")
5. age verify       [data-pel-click='onboarding_confirm_age_click'] -> NEW TAB
                    auth.meta.com/payments/checkout  (card / IG / FB)
6. app loads        chat with agent
7. redeem           ✅ API: POST /api/hatch/invite-code/redeem  (~2s, deterministic)
                    fallback UI: Ctrl+, -> General -> invite_redeem_open_click -> type -> Confirm
                    success: {"success":true,"redemptionStatus":"redeemed"}
                    UI success text: "Congratulations! Your code redemption was successful."
```

## Meta's own API (all plain JSON)

```
POST /api/auth/native/restart              {}
POST /api/auth/native/send-otp             {"contact_point":email,"region":"US"}
POST /api/auth/native/confirm-otp          {"otp_code":"123456"}
POST /api/auth/native/register-completion  {"date_of_birth":"1980-01-01",
                                            "tos_content_version":"ntm_create_account:default_v1_meta_account_v2+docs_v1"}
POST /api/auth/save-account
POST /api/hatch/accept-tos                 {"disclosure_version":"HATCH_ROW_v0","nux_type":"ROW",...}
POST /api/checkout/init                    {"amount":"1.00","currency":"USD","sessionId":"upl_...",
                                            "productId":"766358168544755","receiverId":"352501280694489"}
```

### Redeem + status endpoints (the important ones)

```
POST /api/hatch/invite-code/redeem   {"code":"XXXXXX","supportsRedemptionStatus":true}
  -> {"success":true,"redemptionStatus":"redeemed","waitlistStatus":"waitlisted"}
  headers: content-type: application/json, origin/referer https://muse.ai
  NOTE: no CSRF header needed (cookie session is enough)

GET  /api/hatch/invite               -> {"invite_state":"ELIGIBLE","show_gift":true,...}
POST /api/hatch/token
POST /api/hatch/vm/wake              (wakes the agent VM)
POST /api/auth/check
```

**Always prefer the redeem API over the settings UI.** The UI path was ~300s and
failed roughly half the time ("tombol redeem nggak ketemu"); the API is ~2s and
deterministic. Keep the UI as a fallback only.

`waitlistStatus: "waitlisted"` can accompany a *successful* redeem — the code is
consumed and the reward lands, but product access may still be waitlisted. Report
both fields; do not treat "redeemed" as "has access".

### Prove the redeem actually landed (the user will ask)

"Pastikan harus masuk redeemnya" — when the user needs certainty, never report success
off one unexamined response. Harden the redeem step:

- **Retry the API up to ~3x** and count the account redeemed **only** when the server
  confirms: `json.success is True`, or `redemptionStatus` in
  (`redeemed`, `already_redeemed`). Transient 401 / network error / timeout → wait a few
  seconds and retry; only after the retries are spent fall through to the UI path.
- **Log the raw response body per account** to a proof file
  (`redeemed_proof.txt`: `email|http_status|raw_json|timestamp`). That gives an auditable
  record instead of a claim, and makes "did it really go through" answerable later.
- **`GET /api/hatch/invite` is NOT a usable confirmation signal.** Verified from a HAR:
  `invite_state` reads `ELIGIBLE` both *before* and *after* a successful redeem, while
  only the redeem response carries `redemptionStatus: "redeemed"`. Do not build a
  post-redeem check on `invite_state` — it will look like a failure. The redeem response
  is authoritative.
- Label the outcome so the distinction shows in logs/notifications, e.g.
  `REDEEM TERKONFIRMASI server (success=true) | waitlisted`, not a bare "OK".

### Invite codes have a finite use budget — check the code BEFORE blaming the bot

A referral code is **one code with N uses**, not unlimited. Once exhausted the redeem
API answers:

```
{"success":false,"reason":"used_up",
 "detail":"This referral code has no remaining uses left."}
```

Observed caps vary per code — one exhausted at ~10 redemptions, a second at ~30-31.
Treat any "max redeem N" figure as code-specific, and let the run auto-stop on
`used_up` instead of hard-coding an expected count.

**When a bulk run starts failing at the redeem step across accounts, verify the code's
remaining quota first.** The symptom is indistinguishable from a bot regression — every
account "fails at step 4" while signup, card verification and session all succeed. In
this session that misread cost several killed/re-launched runs.

Handle it explicitly: treat `reason == "used_up"` as its own outcome (report it as
"KODE HABIS KUOTA"), **stop the run** rather than burning accounts and per-IP OTP
budget on a dead code, and ask the user for a fresh code. Do not silently retry.

### CSRF — the key trick
```
header x-hatch-csrf-token = cookie hatch_native_auth_csrf CUT AT THE DOT
                            (e.g. "abc.def" -> "abc")
also send                   x-hatch-caa-reg-entry-point: login_home
```
- The token is the FIRST PART of `hatch_native_auth_csrf` (also equals `csrf_token`
  from the `/restart` response).
- **It rotates on every state change** → re-read before each call. Read it via
  Playwright `context.cookies()` (Playwright CAN read HttpOnly; `document.cookie` cannot).
- Without it: `403 {"type":"csrfFailed"}`.

### OIDC bootstrap (needed before the card popup, else `?error=invalid_redirect`)
```
POST https://auth.meta.com/hatch/session/bootstrap/   form: frl_access_token=<...>
  -> 302 -> GET https://auth.meta.com/oidc/callback/?code=...&state=...
```
`frl_access_token` comes from the `register-completion` response at
`auth_meta_session.frl_access_token`. Submit it as a **real form POST** from a page
(fetch() is CORS-blocked; `ctx.request.post` returns 400).

**Known dead end — don't re-walk it.** Replaying this bootstrap from a *separate* page
completes the OIDC redirect (lands on `/access/disclosure`) yet the card popup still
returns `?error=invalid_redirect`; submitting it in the *main* page instead invalidates
the page handle and the run dies with `TargetClosedError`. Neither variant restores the
app session that `checkout/init` needs. That is the reason the **UI flow remains the only
reliable route to card verification** — treat the signup half as API-able and the
card/redeem half as browser work, rather than chasing a fully API-driven path.

## Pitfalls (all hit for real)

1. **OTP input is `class="sr-only"`** — `click()`/`fill()` fail. Use
   `page.evaluate` to `.focus()` then `page.keyboard.type(code, delay=120)`.
2. **Later-step buttons are pre-rendered DISABLED** — `button[type=submit]` first match is
   the *next* step's button. Always target `[data-pel-click='...']`.
3. **Confirm clicks time out** (React re-render) — fall back to
   `page.evaluate("()=>{const b=document.querySelector('[data-pel-click=\"...\"]'); b&&b.click();}")`.
4. **Birthday `<select>`s need `select_option(label=...)`**, not `value=`.
5. **Variant B form ("What's your birthday?") pre-fills TODAY's date** → age 0. Always
   override month/day/year with an adult DOB (use 1970-1990).
6. **Chromium + proxy**: pass `proxy={"server","username","password"}` **separately**.
   Credentials embedded in the server URL → `ERR_TUNNEL_CONNECTION_FAILED`.
7. **Chromium opens too many connections** → hits proxy session limits. Required args:
   `--disable-http2 --disable-preconnect --disable-dns-prefetch --disable-background-networking`
   `--disable-features=NetworkPrediction,PreconnectToSearch,SpeculativePreconnect`.
8. **Stale OTP**: record the newest IMAP UID *before* requesting, then filter `after_uid`.
9. **Card popup closes itself on success** → `TargetClosedError` from
   `wait_for_timeout` is EXPECTED and benign; catch it and continue.
10. **Settings panel** opens with `Ctrl+,` (Meta prints the shortcut in the UI). Clicking
    the gear is flaky; retry + `Escape` between rounds.
11. **Proxy rotation must key off the ACCOUNT NUMBER** (`proxies[n % len]`), not the loop
    index — otherwise every `--count 1` run hammers one IP and Meta stops sending OTP
    per-IP after ~30 signups.
12. **Fresh accounts need SETTLE time before the settings UI is usable.** An account that
    just finished onboarding (disclosure + card) has an empty Settings panel — the
    redeem entry is not rendered yet, so the UI path reports "tombol redeem nggak
    ketemu". Fix: after verification, `reload` 2-3x with ~13s waits before touching
    Settings. Accounts that skip onboarding are already settled and redeem instantly.
    (This is another reason to use the redeem API — it sidesteps the panel entirely.)
13. **Registration can silently not authenticate.** If the signup steps appear to pass
    but the app skips disclosure/verification *and* the redeem API answers
    `401 {"error":"Authentication required"}`, the session never established.
    Cheap guard: after signup call `GET /api/hatch/invite` (or `/api/auth/check`)
    and branch on the status — **only 401 means "not logged in"**:

    | status | meaning | action |
    |---|---|---|
    | 200 | session live | continue |
    | 401 | never authenticated | mark FAILED now; don't burn ~5 min on redeem rounds |
    | 403 | CSRF only — healthy account | retry without `x-hatch-csrf-token`, else treat as *inconclusive* and CONTINUE |

    **Do not treat 403 as failure.** A naive `ok if status == 200 else fail` check marks
    perfectly good accounts as broken — verified here: a signed-in account mid-onboarding
    returned 403 and was wrongly failed at 64s, killing a live run. 403 is common and
    benign on this endpoint; log it as a warning and keep going. (Best effort: probe once
    *with* the csrf header and once *without*, and only a 401 fails.) Common 401 trigger:
    rate-limit / proxy problems.
14. **A half-finished account from a killed run poisons the next one.** Re-running the
    same email after an aborted run yields broken state (missing "Confirm age" button,
    no disclosure step). If a run is killed mid-account, prefer starting the next run
    at the *following* number rather than reusing that address.
15. **Confirm-age button may never render.** Wait for
    `[data-pel-click='onboarding_confirm_age_click']` in a poll loop (~12 x 2.5s) before
    clicking, and wrap the click + `ctx.expect_page` in a 3x retry with a JS-click
    fallback. A bare 9s click timeout is the usual failure.
    If it is *still* missing, **re-read the page before failing the account** — a first
    miss is not a verdict:
    - page already advanced (no "confirm your age" text, URL off `/access/verification`)
      → verification wasn't needed: mark it SKIP and carry on to redeem;
    - page shows only "Link Instagram account" / "Link Facebook account" → a different
      verification variant: try the generic `confirm age` role button before giving up;
    - **the button IS there but carries NO `data-pel-click` attribute** — the actual
      root cause of most of these failures. A live dump of `/access/verification`
      showed `{'p': '', 't': 'Confirm'}` (empty pel, visible text only) next to
      `onboarding_settings_click` / `onboarding_link_ig_account_click`. An
      attribute-only locator can never match that render. **Always fall back to a text
      locator**: poll `[data-pel-click='onboarding_confirm_age_click']` first, then
      `get_by_role("button", name=re.compile(r"^(Confirm age|Confirm|Get started|Continue)$", re.I))`,
      and log which matched ("tombol verifikasi ketemu via teks"). Deploying this
      fallback removed the bulk of the `Confirm age nggak muncul` failures (9 in one
      session) and is cheaper than any retry/timeout tuning.
    Returning FAILED on the first miss silently burns healthy accounts (a run lost
    several this way).
16. **A parallel proxy liveness test reports false DEAD proxies.** Premium pools
    (ProxyScrape and similar) cap concurrent sessions per account. Sweeping a 100-proxy
    list with 20 worker threads showed only 4 alive; re-testing the *same* list with 2-3
    workers plus a short delay found 21. Never declare a pool dead off a parallel sweep —
    vet with low concurrency (2-3 workers, ~0.5-1s spacing), and re-verify immediately
    before a run because pool health drifts within minutes. Likewise distinguish
    *proxy* health from *target* reachability: `curl`/`requests` through a proxy can
    return HTTP 200 while Chromium against the same proxy fails with
    `ERR_TUNNEL_CONNECTION_FAILED` (see pitfall 6/7) — those are different bug classes.
17. **Validate the pool before the run, and re-rotate when one dies mid-run.** A pool can
    expire quietly between runs: every IP still resolved, but all four returned
    `ProxyError HTTPSConnection`, and the bot dutifully burned the whole batch in ~1s per
    account (`net::ERR_TUNNEL_CONNECTION_FAILED`). Two guards, both cheap:
    - **Pre-flight:** probe each proxy (`requests` GET of the target through it; accept
      200/301/302/307/400 since a non-browser hit legitimately returns 400/307). If
      **zero** are alive, ABORT the run with an explicit message plus a webhook notice —
      never start on a dead pool.
    - **Mid-run:** when an account fails with a transport error (`ERR_TUNNEL_CONNECTION_FAILED`,
      `ERR_PROXY`, `ERR_CONNECTION`, `ERR_TIMED_OUT`, `ERR_EMPTY_RESPONSE`), retry that
      same account on the next proxy (`proxies[(n + try) % len(proxies)]`, max ~3) before
      marking it failed.
    **Triage tell:** accounts failing in ~0-1s with an identical transport error = pool
    problem, not a logic regression. Also check the *credentials*: providers rotate
    user/pass while keeping the same IPs, so an IP that pings fine under a stale login
    still fails — ask the user to re-copy the proxy line, not just new IPs.

## Card age verification

- Opens a NEW TAB (`ctx.expect_page`). Fields: Card number, MM/YY, CVV,
  Country (defaults United States), ZIP.
- Submit via the div `[aria-label^='Pay now' i]` (label reads "Pay now, $1.00").
- It is a **$1 temporary authorization**, not a charge.
- A **non-US debit card + US ZIP passed** for us — don't assume it's rejected.
- Each new account needs its own verification.

### Why the card step cannot be browserless (settled)

The card is **not** posted as plain fields. `auth.meta.com` drives it through three
GraphQL mutations (`PaymentsCometGetServerEncryptionKeyMutation` →
`useFBPayAccountMutation` → `useECPCometFinalizeCheckoutMutation`), the PAN/CVV go up
as client-side-transformed `sensitive_string_value`s, and a ~1.2KB
`platform_trust_token` (device-trust JWT) rides along. Replicating that needs Meta's
card crypto **and** a valid device-trust token plus all GraphQL anti-CSRF params
(`fb_dtsg`, `lsd`, `jazoest`, `__hs`, `__dyn`, `__csr`). Do not promise a browserless
card step. Full transcript: `references/meta-card-verification-graphql.md`.

### User-facing progress reporting (they raised this)

Long unattended runs must **report per phase and per blocker as they happen** — the user
objected to silent iteration with "kenapa kamu lama sekali". Post a short status when:
each account resolves, an unexpected failure pattern appears (3+ consecutive failures =
likely throttling), and when a fix changes the approach. Do not narrate tool calls
inline; report findings and blockers.

### Where the APIs came from

Most of the non-obvious endpoints above were recovered from **browser HAR exports** the
user supplied, not from guessing. That technique is reusable and is written up in
`references/har-reverse-engineering.md` — read it before hand-probing a Meta-ish flow.

## Pacing & accounts.txt

- **Default: space accounts 70-140s apart.** Aggressive pacing (15-30s) makes the run
  flaky — the failure moves around (button not found, click timeout) rather than being a
  logic bug.
- **The user may explicitly order faster pacing** (they asked for 10s). Comply — they own
  the trade-off — but state the risk once: tighter pacing raises the chance of Meta
  per-IP OTP throttling, showing up as runs of `kode email nggak dateng` / silent
  registration failures. Per-account time is dominated by the flow (~140-190s) not the
  gap, so shrinking the gap saves far less wall-clock than it looks like.
- Print progress per phase; log `email|OK/FAILED|note|duration` to `accounts.txt`
  and push one Discord webhook message per account.

## Verification / honesty notes

- Confirm account creation by re-logging in: the prompt changes from
  *"To confirm your account"* to *"To log in"*.
- `/access` + "not available in your country or region" = **waitlist**, needs a
  supported-region proxy. `/access/disclosure` = real access (onboarding).
- Pure HTTP (requests/curl_cffi) is **blocked** — CSRF needs a JS-capable client.
  `fetch()` inside the browser works for the signup steps but the card step still
  needs the app's own session.
