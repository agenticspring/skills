# Tencent TCaptcha / TenDI (TokenHub signup)

## Fingerprint (live 2026-07-21)
- Page: `https://www.tencentcloud.com/account/register`
- UI: Safety check popup, e.g. **“Select the image that best matches ‘Fish’”**
- Network:
  - `https://captchacdn.cloudcachetci.com/TCaptcha-global.js`
  - `https://captchaapi.tencentcloudcs.com/cap_union_prehandle?aid=188959458&…`
- **Captcha appId / aid:** `188959458`
- Do **not** use rumt telemetry `aid=00110011-…` as captcha appId

## Solver protocol (critical)
Solvers do **not** take a pre-solved token or screenshot as input.

### Submit (input TO solver)
```json
{
  "type": "TencentTaskProxyless",
  "appId": "188959458",
  "websiteURL": "https://www.tencentcloud.com/account/register",
  "captchaScript": "https://captchacdn.cloudcachetci.com/TCaptcha-global.js"
}
```
CapMonster alternate:
```json
{
  "type": "CustomTask",
  "class": "TenDI",
  "websiteURL": "https://www.tencentcloud.com/account/register",
  "websiteKey": "188959458",
  "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
```

### Result (output FROM solver)
```json
{ "ticket": "…", "randstr": "@…", "ret": 0, "appid": "188959458" }
```
Inject `ticket` + `randstr` into page/callback / send-code request **only after** status ready.

## User audit: “salah kirim token captcha?”
**No — not a mis-sent puzzle token.**

| Claim | Reality |
|---|---|
| We upload captcha image/token to solver | False — API wants appId+URL |
| appId wrong | False — matches live `cap_union_prehandle?aid=188959458` |
| websiteURL wrong | False — register page URL |
| Failure mode | createTask **OK** then `ERROR_CAPTCHA_UNSOLVABLE` |

If appId/task type were badly wrong, expect `ERROR_TASK_ABSENT` / bad-param more often than worker unsolvable after accept.

## Error reading
| Response | Meaning |
|---|---|
| createTask OK + `ERROR_CAPTCHA_UNSOLVABLE` | Params accepted; workers could not solve this challenge instance |
| `ERROR_TASK_ABSENT` | Wrong/unsupported task type for that provider |
| `ERROR_ZERO_BALANCE` | Key empty — pick next funded key |

## Proven live outcomes (TokenHub)
| Provider | Result |
|---|---|
| 2captcha `TencentTaskProxyless` | accepted → **UNSOLVABLE** (image Fish) |
| CapMonster `CustomTask/TenDI` | accepted → **UNSOLVABLE** |

Support exists; **this instance** unsolvable with current keys/proxyless path. Next levers: residential `TencentTask` + proxy, headed/manual, retry later.

## Project module
- `/root/tencent-tokenhub/tencent_captcha.py` — richest 2captcha key → CapMonster fallback
- `/root/tencent-tokenhub/register_claim.py` — detect captcha → solve → inject → resend code → IMAP

## Key selection
- Rank `TWOCAPTCHA_API_KEY*` by **live balance**; skip zero/negative
- CapMonster: `CAPMONSTER_API_KEY` via `api.capmonster.cloud/getBalance`
