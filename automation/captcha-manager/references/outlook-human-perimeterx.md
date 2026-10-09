# Outlook HUMAN / PerimeterX vs Arkose (2026-07)

Do **not** default Outlook signup to FunCaptcha just because ServerData lists Arkose.

## Form progress that works (Webshare-class)

1. Email → Next  
2. Password → Next  
3. Country + birth (Fluent: `#countryDropdownId`, `#BirthMonthDropdown`, `#BirthDayDropdown`, `input[name=BirthYear]`) → Next  
4. Name (`firstNameInput` / `lastNameInput`) → Next  
5. **Stops at HUMAN press-and-hold** (phone not always reached)

### Early failure (before password)

- UI: **We ran into a problem / Please try again…**
- Common on **DC / Webnovel-class proxies** and bare VPS IP
- Prefer **Webshare-class** pools (`proxy_webshare.txt`); form progress repeatedly OK on that class
- Do **not** burn captcha balance on early risk block

## Late gate identity (critical)

UI:

```text
Let's prove you're human
Press and hold the button.
```

| Signal | Value |
|---|---|
| Vendor | HUMAN Security / PerimeterX |
| Iframe | `iframe.hsprotect.net` |
| App id | **`PXzC5j78di`** (`sHumanAppId`) |
| Hold control | `[aria-label="Press & Hold Human Challenge"]` (nested frames; child may show as `about:blank`) |
| Optional | `#px-captcha` |

**Not** reCAPTCHA. **Not** CF managed. Outer Fluent chrome holds (back button 24×24, `#outer`) do **not** clear the challenge.

## Also in ServerData (other runs)

- Arkose pid: `B7D8911C-5CC8-A9A3-35B0-554ACEE604DA`
- Only spend FunCaptcha if an Arkose iframe is **actually present**
- Incomplete `CreateAccount` without risk/HIP/human → API error **`1347`** (incomplete), not success
- No HUMAN clearance → CreateAccount **`1059` `field=humanCaptcha`**

## Solver inventory (our keys, live createTask)

| Provider | Result |
|---|---|
| Capsolver docs PerimeterX | Page exists; body **Coming Soon**; claims separate endpoint + proxy required when live |
| Capsolver task names tried | `AntiPerimeterXTask`, `AntiPerimeterXTaskProxyLess`, `PerimeterXTask`, `HumanTask`, `AntiHumanTask`, `PressAndHoldTask` → **`ERROR_TYPE_NOT_SUPPORTED`** |
| Capsolver FunCaptcha for this hold | Not a substitute; invalid/unsupported for HUMAN hold path |
| Anti-Captcha | `PerimeterXTask` / `AntiPerimeterXTask` / `PXCaptchaTask` → **`ERROR_TASK_NOT_SUPPORTED`** |
| 2captcha `method=perimeterx` / `pxcaptcha` / `human` | Treated as image upload → `ERROR_ZERO_CAPTCHA_FILESIZE` |

**Balance ≠ capability.** Capsolver/2captcha/Anti-Captcha money for Webnovel reCAPTCHA/CF does **not** clear Outlook HUMAN hold until a PX press-hold task exists on the account.

## risk/verify is browser-only

User hybrid zip (`outlook-creator-sanitized`) and live probes agree:

- `risk/verify` on `login.microsoftonline.com` must run **same-origin in browser**.
- curl_cffi / mismatched TLS → **`403 riskBlock` / AADSTS7005106**.
- curl_cffi is fine for CheckAvailable + CreateAccount **after** HUMAN clearance, not instead of it.

## “No.2 solver khusus PX” means

A provider that returns **HUMAN/PerimeterX press-hold clearance** (`_px3` family / challengeSolution), **not**:

- Capsolver FunCaptcha for Arkose key alone
- Capsolver CF `AntiCloudflareTask`
- reCAPTCHA/hCaptcha keys from Webnovel inventory

## Browser hold (what failed in session)

- Headless Playwright hold on wrong nodes  
- Headed Xvfb + `playwright_stealth.Stealth.apply_stealth_sync` (`navigator.webdriver` false) + correct aria hold ~15–20s → still stuck  
- Report stuck honestly; do not claim account created

## Honest report template

1. Form stage reached (email/password/birth/name)  
2. Gate name: HUMAN press-and-hold, app id `PXzC5j78di`  
3. Solver attempts with **error codes**  
4. Account **not created** until past hold (+ any phone)  
5. Options: specialized PX service, stronger anti-detect profile (CloakBrowser), or manual hold on user device

## Related

- skill `microsoft-account-registration` + `references/outlook-cloakbrowser-hybrid.md`
- `captcha-manager` pitfalls (Outlook HUMAN vs Webnovel CF vs reCAPTCHA)
- Proxy pools are product-specific: Webnovel DC ≠ Outlook/GitHub signup
