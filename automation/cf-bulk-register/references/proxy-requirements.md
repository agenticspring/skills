# Proxy Requirements for Cloudflare Signup

Cloudflare signup (`dash.cloudflare.com/sign-up`) is **hard-blocked from datacenter IPs**.
A residential proxy is not optional — but "a proxy" is also not enough: it must be
**RESIDENTIAL**, not datacenter.

## What was proven (empero / 82.39.206.183, 2026-07)
- Direct VPS IP → first account succeeded, then IP got flagged. All subsequent attempts
  from same IP got **"Just a moment..." 403 (WAF challenge)** at bootstrap.
- **Proxyscrape premium HTTP** proxies (100 tested, datacenter):
  ```bash
  curl -x "http://user:pass@host:port" -s -o /dev/null -w '%{http_code}' \
        https://dash.cloudflare.com/sign-up
  ```
  → **403 on ALL 100**. Every Proxyscrape datacenter IP is refused.
- **Webshare premium datacenter** proxies (10 tested):
  → ~30% passed bootstrap (200), 1 of those successfully completed a full signup
     (Leaseweb UK IP, `31.59.20.176`). After 1 account, that IP was also flagged.
  → Conclusion: SOME datacenter IPs work, but each IP = exactly 1 account max.
  → Webshare 4-part format `host:port:user:pass` works with the script's `_parse_proxy_line`.
- **Free proxy lists** (scraped 70+ sources → 6,120 live HTTP/HTTPS):
  → Filtered against CF bootstrap: only **2 unique IPs** (0.08%) passed.
  → One was Zscaler (corporate proxy, not residential).
  → Both that passed bootstrap still got error **code 1111** on signup POST.
  → Free proxy lists are 99.9% datacenter — useless for CF signup.

## Preflight probe (run this before any bulk run)
Test each candidate proxy and keep only the ones that return a clean 200 HTML page:
```bash
for p in $(cat proxies.txt); do
  code=$(timeout 15 curl -s -x "http://$p" -o /dev/null -w '%{http_code}' \
         https://dash.cloudflare.com/sign-up 2>/dev/null)
  echo "$p -> $code"
done
```
- `200` + actual signup HTML = usable (still verify in-browser: browser egress IP
  must differ from the VPS IP).
- `403` (or a CF challenge/interstitial) = blocked, discard.

## Provider guidance
- Use **residential** pools: DataImpulse residential, Proxy-Cheap residential, 922proxy
  residential, etc. Datacenter lists (Proxyscrape premium, most "HTTP proxy" sellers)
  will not pass.
- Rotate per account: set `"proxy_file": "proxies.txt"` (one `scheme://user:pass@host:port`
  per line). `main.py` randomly picks one per attempt.
- Verify egress changed: `curl -s https://api.ipify.org` vs `curl -s -x <proxy> ...`.

## Symptom -> cause mapping (do NOT re-chase Turnstile)
| Signup symptom | Real cause |
|---|---|
| "Just a moment..." 403 at `bootstrap` call | WAF challenge — IP blocked before reaching CF API. Common for datacenter/flagged IPs |
| "You are unable to sign up at this time" | IP / residential-proxy block detected at signup |
| "Please complete the CAPTCHA and try again." | IP block surfacing as captcha error, OR proxy working but token not bound (rare) |
| `code: 1111` on `user/create` POST (after bootstrap 200 ✓) | IP passed WAF but detected as proxy at signup-time. The bootstrap succeeds (200) but the subsequent signup POST fails. This is a SIGNUP-only block, not a WAF block. Free proxies that pass bootstrap almost always fail here. |
| `Signup failed: Redirect failed: .../sign-up` | form never left sign-up = same IP block |
| `✅ Turnstile solved` + still rejected | IP block, NOT a captcha bug |

Always dump `document.body.innerText` on failure first; the phrase "unable to sign up"
is the definitive signal to fix the proxy, not the captcha.
