# Outlook create — pause/archive snapshot (2026-07-25)

## Decision
Dez: pause and archive; resume after a viable method is found.

## Paths
- Live (kept): `/root/outlook-creator/`, `/root/outlook-autoreg/`
- Archive: `/root/archive/outlook-create-latest` → `outlook-create_20260725_222644/`
- Obsidian: `Projects/Outlook Account Create Archive.md`
- CloakBrowser binary: `~/.cloakbrowser/chromium-146.0.7680.177.5/chrome`

## What was proven
- Form: email → password → birth → name
- Hybrid tokens: canary + continuationToken + sometimes `_px3`
- Dual-host openable on good Webshare: `signup.live.com` + `login.microsoftonline.com`
- HUMAN challenge can appear; `_px3` can change without risk clearance

## Terminal failures (not success)
| Signal | Meaning |
|---|---|
| `AADSTS7005106` / `riskBlock` | hard Microsoft risk policy block |
| `riskChallengeRequired` | another HUMAN round required |
| CreateAccount `1350` | create rejected after incomplete risk |
| CreateAccount `1059` humanCaptcha | curl path missing HUMAN clearance |
| `ERR_TUNNEL_CONNECTION_FAILED` | proxy cannot reach MS hosts |

## Resume requirements
1. Residential / cleaner sticky proxy **or** proven HUMAN/PX solve path
2. Browser-side `risk/verify` (same-origin on `login.microsoftonline.com`)
3. Real CreateAccount success evidence before saving credentials

## Do not on resume
- Mass-retry burned Webshare hosts without dual-host probe
- Treat Capsolver/2captcha/Anti-Captcha as PX press-hold solvers (unsupported here)
- Claim success from mid-captcha `accounts.json` writes
