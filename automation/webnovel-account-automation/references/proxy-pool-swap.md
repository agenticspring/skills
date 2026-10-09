# Safe proxy pool replacement (sticky multi-account)

## Wrong
Only overwrite `proxy.txt`. Sticky `device_profiles.json` still points emails at old `http://user:pass@oldhost:port`, and `sessions/*.json` still carry old proxy + cookies.

## Right procedure
1. Backup:
   - `proxy.txt.bak.<ts>`
   - `device_profiles.json.bak.<ts>`
2. Parse incoming list. Common vendor formats:
   - `user:pass@host:port` (ProxyScrape) → convert to `host:port:user:pass`
   - `host:port:user:pass` (already ProxyPool format)
3. Write new `proxy.txt`
4. Rebind every email in **this pool's** `device_profiles.json`:
   - Prefer unique host assignment when `len(proxies) >= len(accounts)`
   - Else round-robin still sticky per email
5. Delete all `sessions/*.json` (force re-login on new IP)
6. Sample health: curl_cffi chrome124 `GET https://m.webnovel.com/id` through several proxies (expect 200, not CF challenge)
7. Spot-test 1–2 accounts with `ensure_session(force=True)` + balance
8. Restart bot process so runtime ProxyPool reloads

## Expected side effects
- First action per account after swap often hits **11318 untrusted device** → auto Guard OTP (IMAP) once
- New cookies then stick to the new proxy

## Live example
2026-07-20: replaced 10 old proxies with 100 ProxyScrape premium HTTP; rebinding 62 profiles to unique hosts; cleared sessions; sample 8/8 healthy; 2 accounts trust+session+PS OK on new IPs.
