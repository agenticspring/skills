---
name: microsoft-account-registration
description: Automate Microsoft/Outlook (signup.live.com) account creation — Playwright fluent form, Webshare-class proxies, HUMAN/PerimeterX press-and-hold gate, optional phone stop policy.
version: 1.0.0
---

# Microsoft / Outlook Account Registration

## When to use
- User asks to create Outlook.com / Microsoft account
- URL like `signup.live.com/signup`
- Need Microsoft mail for other automations

## Hard truth (do not overpromise)
- Full E2E is **not yet proven** from this VPS stack as of 2026-07-25.
- **Paused/archived 2026-07-25 by Dez** — do **not** mass-retry create until a better method or residential proxy exists. Resume entrypoints: `/root/archive/outlook-create-latest` + Obsidian `Projects/Outlook Account Create Archive.md` (detail: `references/outlook-pause-archive-2026-07-25.md`).
- Proven path: Webshare form email→password→birth→name, then **HUMAN press-and-hold** and/or **Microsoft riskBlock**.
- DC proxies often die earlier with **“We ran into a problem”**.
- Server kill shot (browser): `POST …/risk/verify` → **403** `AADSTS7005106` + `innerError.code=riskBlock` → UI **“Account creation has been blocked / unusual activity”**.
- After risk clearance fail, CreateAccount often returns **`error.code=1350`** (not a success).
- `_px3` / `_pxvid` / `_pxde` alone ≠ success — risk/verify can still riskBlock **or** return `riskChallengeRequired` (another HUMAN round).
- **Correct hold control ≠ cleared challenge:** nested `aria-label="Press & Hold Human Challenge"` + 15–20s hold (headed/stealth/Xvfb) repeatedly failed clearance; do not claim hold works just because the button was targeted.
- Phone verify can still appear after human check on other attempts.
- Inventory here is mostly **Webshare + DC** (no proven residential provider in env). Batch Webshare: many hosts riskBlock; minority reach press-and-hold without immediate block.
- Do **not** claim account created until inbox/login proof exists.
- **Architecture target (user zip `outlook-creator-sanitized`, 2026-07-25):** hybrid **CloakBrowser** for HUMAN/PX + same-origin `risk/verify`, **curl_cffi** for CheckAvailable + CreateAccount. Pure Playwright stealth ≠ CloakBrowser.
- **Installed (2026-07-25):** `pip install cloakbrowser` (0.5.2) + `python3 -m cloakbrowser install` → free Chromium **146** at `~/.cloakbrowser/chromium-146.0.7680.177.5/chrome`. Use `from cloakbrowser import launch, launch_async` — Docker Manager optional. Smoke: `navigator.webdriver False` under Xvfb `:99`.
- **Local runners:** `/root/outlook-creator/` (`register.py`, `hybrid_local.py`, `.env`). Prefer pip `launch`/`hybrid_local.py` when Docker Manager is absent. See `references/outlook-cloakbrowser-hybrid.md` + `references/outlook-cloakbrowser-local-install.md`.

## Canonical toolkit (custom method)
```text
/root/outlook-autoreg/
  session.py signup_api.py px_hold.py run.py analyze_capture.py
  data/px_capture.json  logs/last_{api,browser}.json
```
```bash
cd /root/outlook-autoreg
python3 run.py --mode api --proxy-file /root/github-autoreg/proxy_webshare.txt --prefer-host <REDACTED>
python3 run.py --mode browser --proxy-file /root/github-autoreg/proxy_webshare.txt --prefer-host <REDACTED>
python3 analyze_capture.py data/px_capture.json
```
- **api**: curl_cffi Chrome impersonation → CheckAvailable + CreateAccount
- **browser**: stealth Playwright + custom hold + PX network capture
- **hybrid**: both for diagnostics
- Success appends `data/accounts.txt` only when flags prove create; never print full passwords in chat unless asked.

## Live signup fingerprint (proven 2026-07-25)
| Item | Value |
|---|---|
| URL | `https://signup.live.com/signup?lic=1` |
| UI | Fluent multi-step (email → password → country/birth → name → human) |
| Email field | `input[type=email]` then **Next** (must enable after valid value) |
| Password | `input[type=password]`, ≥8 + upper/lower/number mix |
| Birth | `#countryDropdownId`, `#BirthMonthDropdown`, `#BirthDayDropdown`, `input[name=BirthYear]` |
| Name | `input[name=firstNameInput]`, `input[name=lastNameInput]` |
| API (browserless) | `ServerData=…`; `urlCreateAccount` = `/API/CreateAccount`; `urlCheckAvailableSigninNames` |
| Dry CreateAccount without full risk | error **`1347`** (incomplete) |
| Arkose public key (ServerData) | `B7D8911C-5CC8-A9A3-35B0-554ACEE604DA` (`iframe.arkoselabs.com`) |
| **Actual late gate observed** | **HUMAN / PerimeterX press-and-hold**, not Arkose iframe |
| HUMAN iframe | `https://iframe.hsprotect.net/…` |
| HUMAN app_id | `PXzC5j78di` (`sHumanAppId` / `urlHumanIframe`) |
| Hold control | nested frame button `aria-label` ≈ `Press & Hold Human Challenge` / `#px-captcha` |

## Proxy rules (critical)
| Pool | Outlook signup |
|---|---|
| Webnovel DC (`/root/webnovel-tg-bot/proxy.txt`) | flaky for CloakBrowser: many **`net::ERR_TUNNEL_CONNECTION_FAILED`** on `signup.live.com` and especially **`login.microsoftonline.com`** (required for same-origin `risk/verify`). |
| Generic DC | often **“We ran into a problem”** after email Next |
| **Webshare-class** | better form reach (password→birth→name→human); still frequent **riskBlock** |
| Residential sticky (zip DataImpulse-style `.env`) | intended for zip hybrid; not in current env inventory |

**Dual-host probe before a full hybrid run:**
```text
signup.live.com  AND  login.microsoftonline.com
```
Do not burn long hybrid runs on tunnel-fail pools. Do not burn Capsolver on IPs that cannot open a clean form.

Files often available:
- `/root/github-autoreg/proxy_webshare.txt`
- `/root/x-autoreg/proxy_webshare.txt`
- `/root/webnovel-tg-bot/proxy.txt` (only after dual-host probe)

## Preferred browser path (Playwright)
1. Sticky **Webshare** proxy + Windows Chrome UA + `navigator.webdriver` stripped.
2. Fill full email `local@outlook.com` (not local-only unless UI demands domain picker).
3. Wait until **Next is enabled** before click (disabled = validation/domain not accepted).
4. Password → Next.
5. Country **United States** (or user region), month/day combobox + year input (adult year).
6. First/last name → Next.
7. On **“Let's prove you're human / Press and hold”**:
   - Hold the **nested hsprotect frame** button (page-coordinate `bounding_box` of frame element), 10–15s+; do **not** hold the outer back button or full-page `#outer` div.
   - If hold fails: treat as **HUMAN/PX solver problem**, not FunCaptcha-by-default.
8. Capsolver: try documented HUMAN/PX task types with `app_id=PXzC5j78di` + same proxy; FunCaptcha task for Arkose key only if Arkose iframe actually appears.
9. **Phone gate** → stop, report, do not mark success unless user provides SMS provider.
10. Success only with proof: signed-in surface / account ready + credentials saved under `/root/outlook_accounts.txt` (600) without dumping secrets in chat unless asked.

## Browserless notes (curl_cffi)
- `CheckAvailableSigninNames` with proper `canary` / `uaid` / `hpgid` can return JSON after experiment canary refresh (`isAvailable: true` proven).
- Wrong body → HTML error page.
- `CreateAccount` without HIP/risk/human tokens → **`error.code=1347`** (incomplete).
- With fuller payload but **no HUMAN clearance** → **`error.code=1059`**, **`field=humanCaptcha`**, `data` may include `riskAssessmentDetails`, `repMapRequestIdentifierDetails`, `uuid`, `vid`.
- Retry CreateAccount injecting those risk strings **still 1059** without valid PX clearance — not a win path by itself.
- `curl_cffi` TLS impersonation **helps early form/API** but **does not remove** server-side HUMAN sensor (`fEnableHumanSensorOnSignup=1`, `urlHumanIframe` hsprotect). User idea “pakai curl_cffi biar captcha hilang” → **false for Outlook**; report 1059 honestly.
- Risk URLs under `login.microsoftonline.com/…/risk/initialize|verify` fire in browser path:
  - `initialize` → `riskProvider: Human` + `humanSensorUrl` hsprotect
  - `verify` **403 riskBlock** = hard policy block (not “need more hold seconds”)
- Incomplete browserless risk posts often return HTML shell.

## Captcha mapping (do not conflate)
| Gate | What it is | Action |
|---|---|---|
| Early “We ran into a problem” | risk/IP block interstitial | rotate to Webshare; no captcha spend |
| HUMAN press-and-hold (`hsprotect`, `PXzC5j78di`) | PerimeterX/HUMAN | frame-targeted hold and/or PX/HUMAN solver |
| Arkose (`B7D8911C-…`) | FunCaptcha (may appear other locales/risks) | FunCaptcha task only if iframe present |
| Phone/SMS | security proof | stop unless SMS API |

See skill `captcha-manager` for balances; do not assume FunCaptcha solve clears HUMAN hold.

## Ops discipline
- Prefer short Playwright scripts (one stage per run) — long multi-solver scripts often hit approval timeout.
- Save progress JSON under `/tmp/outlook_*.json` with email/proxy/flags; secrets only to `/root/outlook_accounts.txt` on true success.
- Never print full passwords in chat unless user explicitly asks.
- If user says “lanjutkan” **while active**, resume from last proven stage (human hold), not from zero DC probe.
- If user says **pause / arsip / lanjut nanti setelah method ketemu**: stop retries, snapshot under `/root/archive/outlook-create-*`, redact archived `.env` secrets, update Obsidian Session Index + archive note — **do not** keep burning proxies.

## Custom hold + PX capture (what “method sendiri” means)
UI hold alone is **not** enough. Useful custom stack (`/root/outlook-autoreg`):
1. Gesture engine on nested `Press & Hold Human Challenge` (page-coord `bounding_box`, 15–20s + jitter). **Targeting proven; clearance not proven.**
2. Intercept collector `POST https://collector-pxzc5j78di.hsprotect.net/api/v2/msft` (`payload=` opaque) + risk init/verify.
3. Capture cookie family: `_px3`, `_pxvid`, `_pxde`, `pxcts` (often on `.hsprotect.net`).
4. Detect `risk_block` from risk/verify 403 + UI blocked flags — separate from “still on hold”.
5. CLI: `run.py --mode api|browser|hybrid`, `batch_try.py` (rotate Webshare, exclude burned hosts), `debug_hold.py` (frame dump), `analyze_capture.py`.
6. Next research: reverse/replay sensor so clearance validates — **having `_px3` then “Account creation has been blocked” still counts as fail**.

### When user says “gas custom method / method sendiri hold”
1. Use toolkit above — don’t restart from random DC probes.
2. Prefer Webshare hosts that reach **press-and-hold without immediate riskBlock** (batch to find them).
3. Report: form stage / hold targeted? / hold cleared? / riskBlock? / account proof.
4. After stuck: residential cleaner proxy, specialized PX solver, or pause — **not** more FunCaptcha spend.

Capsolver/2captcha/Anti-Captcha inventory: skill `captcha-manager` + `references/outlook-human-perimeterx.md`. Capsolver PerimeterX docs may be **Coming Soon** / task types unsupported on current keys.

## Pitfalls
- Treating Outlook as “just Arkose” because ServerData lists Arkose — live late gate was HUMAN hold.
- Believing `curl_cffi` alone removes captcha — expect **1059 humanCaptcha**.
- Holding page chrome / 24×24 back button instead of nested frame HUMAN control.
- **Hold false positive:** correct control + long press still stuck — dig sensor/risk, not random clicks.
- Using Webnovel DC proxies and concluding “Outlook is impossible”.
- Clicking Next while still disabled after email fill.
- Claiming create success at name page, after hold, or after `_px*` cookies without post-create proof.
- Ignoring **risk/verify 403 AADSTS7005106 riskBlock** — hard block, not “need more hold seconds”.
- Spending Capsolver FunCaptcha/CF while still on HUMAN page with no Arkose iframe.
- Burning the same Webshare host after riskBlock without excluding it (`--exclude-host` / `batch_try.py`).
- Approval-blocked long commands — split: (1) reach human page (2) hold/capture (3) finish.
- fail2ban: user IP may be free while login fails — VPN-works often = ISP/path, not ban; **no whitelist unless asked**.

## References
- `references/outlook-signup-spike.md` — stage transcript, selectors, HUMAN iframe details
- `references/outlook-custom-toolkit.md` — `/root/outlook-autoreg` CLI, 1059/blocked outcomes, capture analysis
- `references/outlook-cloakbrowser-hybrid.md` — user zip CloakBrowser hybrid; risk/verify browser-only
- `references/outlook-cloakbrowser-local-install.md` — pip install, launch API, dual-host proxy probe, 1350/riskBlock outcomes
- `references/outlook-pause-archive-2026-07-25.md` — pause decision, archive paths, resume checklist
- Captcha inventory: skill `captcha-manager`
- Proxy Webshare patterns also in skill `github-account-registration`

## VPS browser inventory (ops)
On “browser apa yang terpasang / kebanyakan”:
- **Keep:** snap Chromium, Playwright `chromium-1234` + `headless_shell-1234`, ffmpeg, **CloakBrowser** (`~/.cloakbrowser/chromium-146…`).
- **Safe clean:** orphan `agent-browser-chrome-*` procs + `/tmp/agent-browser-chrome-*`; old Playwright **1228** (~640MB).
- **Often missing:** Google Chrome, Firefox, Docker CloakBrowser-Manager.
- Mass kill can SIGTERM the agent shell — kill by `user-data-dir=/tmp/agent-browser-chrome-`, then `rm` temps/cache; verify with `pgrep` counts.

## CloakBrowser + zip hybrid — install & E2E
```bash
pip install -U cloakbrowser && python3 -m cloakbrowser install && python3 -m cloakbrowser info
```
```python
from cloakbrowser import launch_async
browser = await launch_async(headless=False, proxy="http://user:pass@host:port",
                             humanize=True, timezone="America/New_York", locale="en-US")
```
### Outcomes with Webshare/Webnovel DC (2026-07-25)
| Path | Typical result |
|---|---|
| `register.py` form | captcha page **or** tunnel fail |
| `hybrid_local.py` | canary + CT + `_px3` + email available → **`risk/verify` 403 AADSTS7005106 riskBlock** → CreateAccount **`1350`** |
| Cloak installed ⇒ accounts work | **false** without cleaner residential / non-blocked risk path |

### Zip pitfalls
- `outlook_creator.py` assumes Manager CDP (`/api/profiles/{id}/cdp`) — without Docker use pip `launch` / `hybrid_local.py`.
- `risk/verify` **must** be browser same-origin XHR on `login.microsoftonline.com`.
- `register.py` may write `accounts.json` mid-captcha — not success proof.
- Never dump account passwords from `accounts.json` into chat.
