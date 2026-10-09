# CloakBrowser local install + Outlook hybrid (2026-07-25)

## Install (no Docker)
```bash
pip install -U cloakbrowser          # wrapper 0.5.2 proven
python3 -m cloakbrowser install      # free binary ~chromium-146.0.7680.177.5
python3 -m cloakbrowser info
# Binary: ~/.cloakbrowser/chromium-146.0.7680.177.5/chrome
```
Optional: `DISPLAY=:99` + Xvfb; `CLOAKBROWSER_SUPPRESS_FONT_WARNING=1`.

## Launch API
```python
from cloakbrowser import launch, launch_async
browser = await launch_async(
    headless=False,
    proxy="http://user:pass@host:port",
    humanize=True,
    timezone="America/New_York",
    locale="en-US",
    args=["--no-sandbox", "--disable-dev-shm-usage"],
)
# navigator.webdriver → False (smoke-tested)
```

## Paths on this VPS
| Path | Role |
|---|---|
| `/root/outlook-creator/` | adapted zip (`register.py`, `hybrid_local.py`, `.env`) |
| `/root/outlook-autoreg/` | earlier custom toolkit |
| `/tmp/outlook-creator-sanitized/outlook-creator/` | original zip extract |

## Proxy wiring
`.env` keys (zip style):
```ini
PROXY_LOGIN=
PROXY_PASSWORD=
PROXY_HOST=
PROXY_PORT=
```
Webnovel TG format `host:port:user:pass` → map into those keys.

### Probe before full hybrid
1. `signup.live.com` must 200 “Create your Microsoft account”
2. `login.microsoftonline.com` must open (risk/verify) — **Webnovel DC often `ERR_TUNNEL_CONNECTION_FAILED` here even when signup works**

## Hybrid phase outcomes (Webshare / Webnovel DC)
1. Load signup → often get `continuationToken` + `_px3` + canary
2. CheckAvailable → `isAvailable: true` possible
3. Browser `risk/verify #1` → frequently **403 `AADSTS7005106` / `riskBlock`** (no challenge URL)
4. CreateAccount without clean verify → **`error.code=1350`** (or 1059 humanCaptcha on pure API)

## Do not claim
- CloakBrowser install alone = Outlook accounts working
- Webnovel proxy pool is “good enough” without dual-host probe
- `accounts.json` from `register.py` = verified account (it may log mid-captcha)

## Next when blocked
- Residential sticky proxy (zip designed for DataImpulse-like)
- Or pause — tooling is ready; risk policy is the gate
