# Sticky per-account device isolation

## Why
Many Webnovel accounts from one VPS look like one device if UA/TLS/proxy are identical. Isolation is **per-email durable profile**, not one browser profile shared by all.

## Storage
- File: `/root/webnovel-autoreg/device_profiles.json` (**gitignored** — contains proxy URLs with creds)
- Module: `/root/webnovel-autoreg/device_profiles.py`
- API: `get_or_create_profile(email, prefer_proxy=None)`, `profile_summary(email)`, `update_profile_proxy(email, proxy)`

## Profile shape
```json
{
  "email": "user@<REDACTED>",
  "proxy": "http://user:pass@host:port",
  "desktop": {"id": "win_chrome120", "ua": "...", "accept_language": "...", "platform": "Win32"},
  "mobile": {"id": "android_chrome124", "ua": "...", "impersonate": "chrome124", "accept_language": "..."},
  "created_at": 0,
  "updated_at": 0
}
```

## Assignment rules
1. On first touch of an email, assign:
   - sticky proxy from `proxy.txt` (prefer unused IPs; else stable hash pick)
   - desktop fingerprint from pool (Win/Mac/Linux Chrome variants)
   - mobile fingerprint from pool (Android Chrome 120/124 + locale AL)
2. Never randomize on every login — sticky forever unless `force_new` or explicit proxy update.
3. Mobile **impersonate** should stay on **chrome120 / chrome124**. chrome131 frequently returns CF challenge on `m.webnovel.com`.
4. Register/login (`LightSession`) use **desktop** UA/AL. PCM (`open_mobile_session`) uses **mobile** UA + impersonate + same sticky proxy.

## Wire points
- `signup.register` → profile before `LightSession`
- `signup.login_check` → profile before `LightSession`; put summary in `meta["device"]`
- `signup.open_mobile_session(..., email=)` → load mobile half of profile
- TG bot `wn/client.py` `ensure_session` / `_proxy_for(email)` → sticky proxy, pass `email=` into mobile session

## Verification (session recipe)
1. Pick 2 emails; call `get_or_create_profile` twice each — second call must equal first (sticky).
2. Assert profiles differ on at least one of: proxy, desktop.id, mobile.id.
3. `login_check` both with `return_meta=True` — `meta["device"]` should match stored profile.
4. `open_mobile_session(..., email=)` — session `User-Agent` matches mobile UA; proxy host matches sticky proxy; `login_ok`/`info_ok` when ticket available.

## Limits
- Account count > proxy count ⇒ IP reuse is expected; still sticky (same email → same IP), not random hop.
- Isolation is HTTP fingerprint + proxy, not full browser canvas/WebGL spoofing.
