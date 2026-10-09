# Outlook custom toolkit (`/root/outlook-autoreg`)

Session build + E2E (2026-07-25). Research/WIP — not a proven full create.

## Layout
```text
/root/outlook-autoreg/
  session.py       # Proxy dataclass, curl_cffi session, ServerData parse
  signup_api.py    # gen_identity, bootstrap, CheckAvailable, CreateAccount, parse 1059
  px_hold.py       # Playwright stealth flow, human_hold(), PX request/response capture
  run.py           # CLI --mode api|browser|hybrid
  analyze_capture.py
  data/px_capture.json
  logs/last_api.json last_browser.json browser_*.png
```

## Commands
```bash
cd /root/outlook-autoreg
python3 run.py --mode api --proxy-file /root/github-autoreg/proxy_webshare.txt --prefer-host <REDACTED>
python3 run.py --mode browser --proxy-file /root/github-autoreg/proxy_webshare.txt --prefer-host <REDACTED>
python3 analyze_capture.py data/px_capture.json
```

Prefer Webshare hosts that previously opened the fluent form (example sticky: `<REDACTED>`). Headed browser uses `DISPLAY=:99` (Xvfb) when available.

## API mode outcomes (curl_cffi chrome124)
| Step | Result |
|---|---|
| Signup page + ServerData | OK |
| DFP `fpt.live.com` | sets `fptctx2`, `MUID` |
| Human iframe GET | OK (`app_id=PXzC5j78di`) |
| CheckAvailableSigninNames | `isAvailable: true` after canary refresh |
| CreateAccount incomplete | **`error.code=1347`** |
| CreateAccount fuller, no HUMAN | **`error.code=1059`**, **`field=humanCaptcha`** |
| Retry with riskAssessmentDetails from 1059 data | still **1059** |

1059 `data` may JSON-decode to: `riskAssessmentDetails`, `repMapRequestIdentifierDetails`, `uuid`, `vid`. Injecting those strings alone does **not** clear HUMAN.

## Browser mode outcomes
Form path with Webshare: email → password → birth → name → HUMAN or hard block.

Capture highlights:
- Collector: `POST https://collector-pxzc5j78di.hsprotect.net/api/v2/msft` (`payload=` opaque)
- Scripts: `client.hsprotect.net/PXzC5j78di/main.min.js`
- Risk: `login.microsoftonline.com/…/risk/initialize` and `…/risk/verify`
- Cookies seen: `_px3`, `_pxvid`, `_pxde`, `pxcts` (+ `amsc`, `fptctx2`, `MUID`)

Observed late page (not success):
```text
Account creation has been blocked
We have detected some unusual activity and have blocked the creation of this account.
```

Custom UI hold (correct `aria-label="Press & Hold Human Challenge"` box) + stealth + headed Xvfb still failed clearance in session tests.

## What “method sendiri” must become next
1. Reverse/reconstruct PX collector sensor (not only mouse hold).
2. Bind clearance to same sticky proxy + session.
3. Rotate flagged Webshare hosts after “unusual activity”.
4. Only then CreateAccount / Next past human.

## Related
- Parent skill body: selectors, proxy tables, Arkose vs HUMAN map
- `captcha-manager` / `references/outlook-human-perimeterx.md` — third-party solver limits