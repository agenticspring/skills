# Case notes: multi-step React/Next.js OTP signup (Meta "Muse", muse.ai)

Solved end-to-end 2026-10-07, **including age verification and in-app invite redemption**.
`muse.ai` is Meta's consumer agent — auth redirects to `auth.meta.com`, cookies are
`.facebook.com` `datr` + `.instagram.com` `ig_did`. This is **Meta account creation**, not a
site-local account.

The flow and the browser-automation traps below generalise to any **Next.js + Radix/shadcn**
signup that renders all steps into one DOM and toggles visibility.

> **Correction to an earlier version of this file.** An earlier pass concluded
> "no age verification is ever requested" and "the product is geo-gated, accounts are useless".
> Both were wrong, and both came from stopping at `/access`. The gate chain is
> **disclosure → age verification → app**, and `/access` is the *onboarding router*, not a
> waitlist. See "The full gate chain" below. Do not repeat the earlier conclusion.

## The flow (full, proven)

```
1. landing         input placeholder "Mobile number or email"  -> Continue
2. email OTP       "Enter your code" — 6 digits, no password anywhere
3. profile form    TWO VARIANTS — branch on the rendered heading:
                     "Finish creating your account" -> First name + Last name + Birthday
                     "What's your birthday?"        -> Birthday only, no name inputs
4. /access/disclosure   "A few things to know"  -> button onboarding_disclosure_continue_click
5. /access/verification  "We need to confirm your age"
                           onboarding_confirm_age_click   -> opens a NEW TAB
6. (card tab) auth.meta.com/payments/checkout  -> card + MM/YY + CVV + Country + ZIP
7. app                chat with the agent, settings accessible
8. Settings (Ctrl+,) -> General -> "Redeem invite code" (invite_redeem_open_click)
                       -> type code -> Confirm
```

Meta sends two distinct mail types, both from Meta:
- `security@account.meta.com` — subject `Confirm your email address for your new Meta account`
- `notification@email.meta.com` — subject `Use code XXXXXX to log in`

**Passwordless.** Login later is the same 6-digit email code. Nothing belongs in an
`email:password` file — record `email` + "auth is OTP-only".

## The full gate chain — do not stop at `/access`

`/access` is a **router**, and its child routes are the onboarding steps:

| route | meaning | control |
|---|---|---|
| `/access` | entry | — |
| `/access/disclosure` | "A few things to know" | `onboarding_disclosure_continue_click` |
| `/access/verification` | age gate | `onboarding_confirm_age_click` |

Two mistakes cost real time here, both worth avoiding:

1. **String-matching a single word to classify a page.** The checker tested
   `"/access" in url or "waitlist" in body.lower()` and therefore labelled *every* `/access/*`
   page "GEO-BLOCK (waitlist)". The page actually rendered was the disclosure step. Classify by
   the **heading text** (`"a few things to know"`, `"confirm your age"`, `"what's your birthday"`),
   never by a bare token that also appears elsewhere in the bundle.
2. **Guessing product URLs.** `/settings`, `/settings/general`, `/account`, `/app` all redirect
   back to the gate. There is no deep link — reach settings **through the in-app panel**.

## Age verification: three options, card path is automatable

`/access/verification` offers **credit card** / *link Instagram* / *link Facebook*. The card
option spawns a **new tab** (not an in-page dialog) — capture it with `context.expect_page()`,
otherwise the parent page just sits on "Finish verifying your age in the opened tab."

Card form at `auth.meta.com/payments/checkout/?receiver_name=Age+Verification+CCV`:

```
Card number | MM/YY | CVV | Country or region (defaults United States) | ZIP code
[Pay now, $1.00]
```

* It is a **$1.00 temporary authorisation**, not a charge — copy says "You may see a temporary
  authorisation on your card".
* `Country or region` defaults to **United States** and a **ZIP is mandatory**.
* **A foreign-issued card is not automatically rejected.** A Spanish **debit** Mastercard plus a
  plain US ZIP (`10001`) passed on the first attempt. Do not pre-emptively refuse the card path
  on a country mismatch — test it.
* Field locators: `input[aria-label*='Card number' i]`, `…'MM/YY'`, `…'CVV'`; the ZIP field is the
  only text input with an **empty** `aria-label`.
* Submit control is a `div` labelled `Pay now, $1.00` — match `[aria-label^='Pay now' i]`, because
  the two `button[type=submit]` elements give no useful signal.

**The tab closing is success, not failure.** After submit the page shows
`Processing… → Still processing…` and then the popup auto-closes, which surfaces as
`TargetClosedError` on the next `wait_for_timeout`. Reload the parent page; if the gate is gone
you passed.

## In-app settings + invite redemption

* **Open settings with the keyboard shortcut `Ctrl+,`.** Clicking the gear
  (`settings_menu_open_click`) was unreliable across runs; `Ctrl+,` worked. Confirm the panel is
  open by looking for `Log out` / `Secure store` in the body, not for `General` alone.
* The panel **populates asynchronously** — the plan/usage/invite block
  (`Free plan`, `% used`, `Redeem invite code`) appears after the static entries. **Poll for
  `[data-pel-click='invite_redeem_open_click']` while scrolling** (up to ~20 attempts); a single
  dump will miss it and look like the element does not exist.
* Redemption is time-boxed: *"Redeem a friend's code within 48 hours of joining."* Therefore run
  **register → verify → redeem in ONE continuous browser session** on a fresh account. Logging
  out and back in is where runs break (see the OTP-reuse pitfall in SKILL.md).
* Success copy to assert on:
  `Congratulations! Your code redemption was successful.`

## Trap 1 — every step's button is pre-rendered, so `button[type=submit]` picks the wrong one

All steps live in the DOM at once; inactive ones render `disabled`. Clicking
`button[type=submit]` on the OTP step resolves to the **birthday step's** Confirm and times out
with `element is not enabled`.

The site labels every control:

```html
<button type="submit" data-pel-click="login_birthday_continue_click" disabled …>
```

**Target `[data-pel-click='…']`, never a bare tag+type selector.** Names seen:

| step | attribute |
|---|---|
| log-in entry | `logged_out_login_click` |
| email submit | `login_contact_continue_click` |
| OTP confirm | `login_otp_confirm_click` |
| profile confirm | `login_birthday_continue_click` |
| terms | `login_native_auth_tos_click` |
| resend / back | `login_resend_code_click` / `login_back_click` |
| disclosure continue | `onboarding_disclosure_continue_click` |
| age gate | `onboarding_confirm_age_click` |
| settings open | `settings_menu_open_click` |
| invite redeem | `invite_redeem_open_click` |

The attribute is a free **step-name oracle**: `login_birthday_continue_click` revealed the next
step before we reached it, which is how the form was pre-mapped.

## Trap 2 — the OTP input is `class="sr-only"`: not clickable, and `fill()` may not register

```html
<input type="text" maxlength="6" class="sr-only" pattern="[0-9]*" inputmode="numeric"
       autocomplete="one-time-code" aria-label="6-digit security code"/>
```

Visually hidden behind an overlay, so Playwright's `click()` fails with
`<div role="presentation"> intercepts pointer events`.

```python
await page.evaluate("""() => {
  const i = document.querySelector('input[maxlength="6"]');
  if (i) i.focus();
}""")
await page.keyboard.type(str(code), delay=120)
```

React's controlled-input handler picks up real key events; a programmatic `value=` assignment
often does not. Read the value back with a **plain JS string** — nested quotes inside f-strings
silently produce `(no input)` and make you think typing failed when it worked.

The same applies to the **invite-code input** (`aria-label="Invite code"`): its `click()` is
intercepted too, so JS-focus + `keyboard.type()` is the pattern there as well.

## Trap 3 — Playwright `click()` on the submit times out even though the button is enabled

Confirm reports `is_enabled() == True`, then `click()` burns 30 s because the re-render detaches
the node mid-action.

```python
await page.evaluate("""() => {
  const b = document.querySelector('[data-pel-click="login_birthday_continue_click"]');
  if (b) { b.scrollIntoView({block:'center'}); b.click(); }
}""")
```

Wrap Playwright click in try/except and fall through to the JS click. The timeout is **not** a
rejection.

## Trap 4 — date selects need `select_option(label=…)`, not value

Three `<select>`s in order **Month, Day, Year**, wrapped in styled Radix triggers. Options exist
as `1|2|3…` with visible labels like `January`. `label="June"`, `label="15"`, `label="1995"`
works; matching by value does not.

**These are pre-filled with TODAY's date.** In the birthday-only variant the Confirm button is
therefore already enabled — if you skip the selects, the account is created **0 years old** and
the age gate fires. Always override all three, and bias the year to a clearly-adult value when the
user asks for an older age.

## Trap 5 — wait on the placeholder, not on `input[type=text]`

The page carries several hidden inputs, so `input[type=text]` + `.first` resolves to an invisible
node and `wait_for(state="visible")` times out on a page that is fine. Use
`input[placeholder*='email' i]`. `wait_until="networkidle"` is flaky here — prefer
`domcontentloaded` plus the placeholder wait.

## Detecting "account already exists" from copy alone

| state | prompt |
|---|---|
| new address | `To confirm your account, enter the 6-digit code…` |
| already registered | `To log in, enter the code we sent to…` |

That text flip is a cheap, no-API existence check — useful for verifying a batch really created
accounts, and for not double-registering an address.

## Reusable checklist for this signup class

1. Dump `[data-pel-click]` first; build a step→attribute map before writing selectors.
2. Locate each step's *active* control by attribute, and by `is_enabled()`.
3. For any hidden/`sr-only` input: JS `focus()` + `keyboard.type()`.
4. Wrap every Playwright `click()` in try/except → JS `.click()` fallback.
5. `select_option(label=…)` for styled date dropdowns; override pre-filled defaults.
6. Gate waits on a placeholder or attribute selector, never a bare input tag.
7. Classify pages by **heading text**, never by one token that also appears in the JS bundle.
8. Expect `expect_page()` for gates that open new tabs; a closed popup often means success.
9. Poll-and-scroll for async panels; one dump is not evidence of absence.
10. Do the whole chain in one session when a step is time-boxed (invite redemption, trials).
