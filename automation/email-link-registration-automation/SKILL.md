---
name: email-link-registration-automation
description: Automate email-verified signup — activation links, 6-digit OTP, or identity-provider flows with age/onboarding gates — via proxy rotation, IMAP polling, and strict success criteria.
version: 1.0.0
category: automation
tags: [registration, IMAP, email-verification, proxy-rotation, stdlib, account-automation]
---

# Email-link Registration Automation

Use this for sites where signup is: form submit -> email arrives -> click activation link -> login becomes valid.

This skill is about the **class** of workflow, not one site.

## When to use

- Registration confirms via **email** — either a confirmation **link** or a **6-digit OTP code**.
  Both are covered here; the OTP variant is in "Variant: multi-step React/Next.js OTP signup".
- You need to run from lightweight environments like VPS or Termux.
- You need proxy rotation because registration endpoints may ban or rate-limit specific IPs.
- You must prove that a created account is actually usable, not merely that the registration endpoint returned success.

## Core rule: success means verified, not merely registered

Never count an account as success after only the registration API returns `code=0` or equivalent.

An account is **successful only if**:
1. registration request succeeds,
2. verification email is found,
3. the activation link is extracted or resolved,
4. the activation URL is hit successfully,
5. optional but preferred: login is tested and proven.

If email is missing, polling fails, or activation is not confirmed, do **not** save the account as success.

## Recommended workflow

1. **Bootstrap session state**
   - Fetch the site's current JS/runtime config, not just the HTML form.
   - If the site uses runtime RSA/public-key config, extract it from the JS bundle or runtime object each run.
   - Do not hardcode secrets or user passwords in code. Read them from `.env`.

2. **Resolve the real registration prerequisites**
   - Inspect the site's actual login/register JS functions (`register`, `checkCode`, `jsonp`, etc.) and copy the real request shape.
   - Confirm whether the site uses GET/JSONP vs POST/XHR. Do not assume.
   - Confirm the live password policy from client-side validators.

3. **Register**
   - Submit through a cookie-aware session.
   - Use proxy rotation when IP bans are possible.
   - Treat known IP-ban responses as proxy failures, not account failures.

4. **Poll IMAP correctly**
   - Search multiple Gmail folders because names are locale-dependent:
     - `INBOX`
     - `[Gmail]/All Mail`
     - `[Gmail]/Semua Email`
   - Search by `TO` / body text for the **exact target address**.
   - On catch-all domains, **do not** fall back to bare `UNSEEN FROM provider` — that steals other accounts' mails and creates false green paths.
   - Require target address in To / Delivered-To / X-Original-To / body before accepting a message.

5. **Extract the activation URL correctly**
   - Some providers send a **tracking URL** instead of the final site URL.
   - Prefer HTML `href=` CTA links; if multiple trackers exist, pick the longest real CTA (not open-pixel/beacon paths like `/q/`).
   - Follow the tracking URL redirect to get the real confirmation page before declaring the account verified.
   - If confirm JSONP keeps raw query tokens then re-encodes them (jQuery-style), preserve that encoding exactly (often double-encoding).

6. **Save only verified accounts**
   - Write `email:password` to the success file only after verification succeeds.
   - Unverified registrations should be logged separately or counted as failed/incomplete.

7. **Prove usability**
   - Prefer testing login with the same credentials after confirmation.
   - Treat login codes carefully: password-wrong vs untrusted-device vs captcha-after-password are different outcomes.
   - If login fails, the flow is still incomplete even if registration and email detection worked.

## Proxy rotation rules

- Keep proxies in a dedicated `proxy.txt` file, one proxy per line.
- Support `host:port:user:pass` and normalized URL forms.
- On site-specific IP ban codes/messages, mark the proxy dead and retry with another proxy.
- Do not mark the account successful when registration succeeded on one proxy but verification never completed.
- **Rotate by ACCOUNT IDENTITY, not by loop index.** `proxies[i % len(proxies)]` with `i` the inner
  counter pins every single-account run (`--count 1` — i.e. all your testing) to `proxies[0]`. One IP
  then absorbs the whole batch and trips the per-IP OTP/registration throttle while the rest of the
  pool stays unused, which reads as "the flow is broken". Use a value stable across runs —
  account serial / email / persisted counter: `proxies[n % len(proxies)]`. Log the exit IP per
  account so a non-rotating pool is visible immediately. Full write-up:
  `browserless-web-automation` → Pitfalls.

## Password handling rules

- Use `.env` for a fixed password if the user wants one shared password.
- Never hardcode the user-provided password into source files or README examples.
- If `.env` contains a blank value, allow later env sources to override it with a non-blank value.
- Prefer local `.env` for project-specific values, but allow fallback from known credential sources when local values are blank.

## Lightweight implementation pattern

When the target environment is Termux/VPS and the workflow can avoid a browser:
- prefer Python stdlib (`urllib`, `imaplib`, `http.cookiejar`) over heavy dependencies,
- inline RSA/PKCS1 handling when necessary,
- keep the script runnable with `python3 script.py` and no install step.

Use a browser only when the site truly requires JS execution that cannot be reproduced over direct HTTP.

## Pitfalls

### 1. Registration response != usable account
A `code=0` register response is not the finish line. Many sites still require email confirmation before auth works.

### 2. Wrong Gmail folder assumptions
If polling only checks one folder name, detection may fail on localized Gmail accounts.

### 3. Tracking-link emails
The visible confirmation link may be a mailing-provider tracker (for example, `spmailtechnol`), not the real site confirm URL. Follow redirects. Distinguish CTA paths from open-pixel/beacon paths.

### 3b. Catch-all IMAP poison
Bare `UNSEEN FROM provider` on catch-all inboxes can activate the wrong account's link. Always bind the message to the target address.

### 4. Misleading output
Do not print `success` before verification. Use wording like `registration submitted` until verification is proven.

### 5. Blank local env shadowing valid fallback creds
A local `.env` with `IMAP_PASS=` empty can accidentally disable IMAP if the loader refuses to override blank values from later env sources.

### 6. Old account files can poison debugging
If earlier runs saved unverified or pre-fix accounts, later login tests may fail for reasons unrelated to the current code. Treat fresh post-fix accounts separately when validating login.

### 7. A reused OTP silently kills the run — guard on IMAP UID

Codes are keyed by *address*, so a catch-all inbox still holds the **previous** login's code. A
naive poll returns the stale one, the provider rejects it, and the page never advances — which
looks exactly like "the panel is broken" or "the button doesn't work", and sends you debugging the
wrong layer.

Snapshot the newest IMAP UID for the target address **before** submitting the address, then accept
only messages with a **higher** UID:

```python
uid0 = newest_uid(email)              # search (TO "<target>"), take the last UID
... submit email, wait for the code screen ...
code = get_otp(email, after_uid=uid0) # skip anything <= uid0
```

If no new mail arrives at all (provider re-send rate limit), **stop and report it** — retrying with
the old code guarantees a false negative.

### 8. Never classify a page from one word in its body

`"/access" in url or "waitlist" in body.lower()` labelled every onboarding page "GEO-BLOCKED",
because that word also appears elsewhere in the bundle. The result was a confident, wrong verdict
that nearly ended a working job. Match on the **rendered heading** of the step
(`"a few things to know"`, `"confirm your age"`, `"what's your birthday"`) and assert on the
control you expect (`[data-pel-click=…]`), never on a stray token.

## Output conventions

Use status wording that matches reality:
- `Registration submitted`
- `Verification email found`
- `Activation URL resolved`
- `Account verified`
- `Login proven`

Avoid `Success` unless the flow's actual terminal condition was reached.

## Variant: gRPC-web / protobuf auth APIs (Grok/xAI case)

Some sites' signup backends are **not REST JSON** — they speak ConnectRPC /
gRPC-web over protobuf. accounts.x.ai (Grok) is a proven example. The REST-ish
paths visible in JS (`/api/auth/*`) can be a disabled/decoy path that 404s.

Class-level rules that apply whenever JSON POSTs to discovered paths return
`404` while `OPTIONS` on the same path returns `204`:
1. Find the real transport in the JS bundle (`createClientTransport`,
   `createConnectTransport`, `TransportProvider`). ConnectRPC URL shape is
   `{baseUrl}/{typeName}/{MethodPascalCase}` — method name is PascalCase.
2. Decode `fileDesc("base64...")` strings embedded in the JS. Base64-decoding
   gives the full proto schema: field names in order, nested types, service +
   method list, and the Go package (`proxy/gen/go/...`) which yields the
   typeName. **Never guess protobuf field numbers from prose order** — read the
   descriptor; numbers are frequently non-sequential (e.g. password=5, tos=6).
3. gRPC-web request: `Content-Type: application/grpc-web+proto`,
   `X-Grpc-Web: 1`, body = frame `\x00` + 4-byte big-endian length + protobuf.
   Response uses the same framing. Success = `grpc-status: 0` (empty body OK).
   `grpc-status: 13` with "invalid compression flag: 123" means you sent JSON
   where protobuf frames were expected.
4. Cloudflare Turnstile tokens are IP-bound: solve with `AntiTurnstileTask` +
   proxy and route the registration API calls through that SAME proxy,
   otherwise the final create call fails `Failed to verify Cloudflare turnstile token`.
   The LOGIN call (`CreateSession`) enforces the same anti-abuse requirement —
   expect `grpc-status 7: Anti-abuse token is missing` if you omit it.
5. Verification codes may be 6 ALPHANUMERIC (`WEG-D4V`), not 6 digits — read
   the actual email subject before writing the IMAP poll regex.
6. Verify endpoints can consume the code (`delete_on_success`): if a later step
   needs the same code, set delete_on_success=false or skip the explicit verify.
7. After signup, the session JWT may double as a web-app cookie under a
   specific name (Grok: cookie `sso` on grok.com) even though bearer auth is
   rejected — check JS for how the session cookie is stored before assuming it
   is unusable. Registration success ≠ chat usable: new accounts can still be
   hit by server-side anti-bot on the chat REST endpoint. **Chat bypass for
   this class: look for a WebSocket gateway** (`wss://host/ws/mgw/?uid=...` for
   Grok) that enforces Castle/anti-bot differently (often not at all) while the
   REST chat endpoint 403s. WS chat is OpenAI-realtime-style: envelope
   `{session_id, event}`, user turn via `conversation.item.create` with
   `content:[{type:"input_text",text}]`, tokens via `response.output_text.delta`.
   See `references/grok-xai-case-notes.md` for the full protocol, the
   input_chunks format pitfall, and the rate-limit signal
   (`response.grok.output.stream_error.kind == "usage_limit_reached"`).

Full worked case (field numbers, headers, turnstile fix, script path):
`references/grok-xai-case-notes.md`.

## Variant: identity-provider signup with a gated onboarding (Meta "Muse" case)

Some sites create no local account at all — signup hands off to an identity provider
(`auth.meta.com`, Google, Apple) and the real chain is
**email OTP → profile + date-of-birth → age/identity gate → product onboarding**.

Class-level rules:

1. **The URL you land on after signup may be a router, not a wall.** `muse.ai` dropped every new
   account on `/access`, which reads like a waitlist. It was the onboarding router:
   `/access/disclosure` → `/access/verification` → app. **Read the heading and the controls before
   concluding "gated".** This mistake is expensive — it ends the job early on a run that was one
   click from working.
2. **Age gates often offer a card path, and foreign cards can pass.** The gate offered
   card / link-Instagram / link-Facebook. The card form wanted `Card number`, `MM/YY`, `CVV`,
   `Country or region` (defaults United States) and a **mandatory ZIP**; it is a
   **$1.00 temporary authorisation**, not a charge. A Spanish **debit** Mastercard with a plain US
   ZIP passed on the first try — do not refuse this path on a country mismatch without testing.
3. **Gates that open a new tab need `context.expect_page()`.** The card form is a separate tab on
   the provider's payment host. Inspecting only the parent page shows
   "finish verifying in the opened tab" and looks like nothing happened.
4. **A popup that closes itself is usually success.** The flow raised `TargetClosedError`
   immediately after submit. Reload the parent and check whether the gate disappeared before
   reporting failure.
5. **Time-boxed steps dictate the batch shape.** Invite redemption was "within 48 hours of
   joining", so register → verify → redeem must run in **one continuous session** on a fresh
   account. Re-logging in between steps is where such runs break (see pitfall 7).
6. **In-app actions have no deep link.** `/settings`, `/account`, `/app` all redirect back to the
   gate. Drive the product's own panel, and prefer the **keyboard shortcut** (`Ctrl+,`) over
   clicking the gear, which was unreliable run-to-run.

Full worked case (variant branching, the `data-pel-click` map, card-form locators, async settings
panel polling): `references/meta-muse-otp-signup.md`.

## Working style for long automations (user preference)

A registration run is a **chain of small blockers**, not one task. The user's explicit complaint
after a long silent grind: *"stop, explain why you take so long."* The debugging was not the
problem — **invisible progress** was.

- **Report at every change of theory.** One line per blocker transition is enough
  ("proxy rejects chromium → trying split credentials"). Batch the tool calls, not the narration.
- **Never grind more than ~2 failed hypotheses without surfacing status.** If the same class of
  failure has repeated twice, stop and report state + options instead of trying a third guess.
- **When the user says "stop and explain", lead with the reason, then current status, then the one
  decision you need.** No further tool calls until they answer.
- **Verify an "impossible" claim empirically before accepting it.** A "geo-block" that survived a
  US proxy turned out to be an onboarding gate plus a false positive in our own checker;
  confirming it by reading the real page cost far less time than acting on the wrong belief.

## References

- `references/meta-muse-otp-signup.md` — Meta/Muse identity-provider signup: variant branching, the `data-pel-click` step map, `sr-only` OTP input, card age-verification, and in-app invite redemption.
- `references/webnovel-case-notes.md` — concrete site-specific notes from a live session: runtime RSA key discovery, IMAP quirks, tracking-link activation, and failure modes.
- `references/grok-xai-case-notes.md` — browserless Grok/xAI signup via gRPC-web protobuf: endpoint discovery from JS bundles, descriptor decoding, verified field numbers, IP-bound Turnstile fix.
