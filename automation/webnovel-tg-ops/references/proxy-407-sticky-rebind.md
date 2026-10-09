# Proxy 407 from stale sticky bindings

## Symptom
Powerstone/bookmark/create output shows per-account failures like:

```text
curl: (56) CONNECT tunnel failed, response 407
```

This is HTTP proxy auth failure, not Webnovel account/password failure.

## Root cause pattern
After ProxyScrape trial replacement or `proxy.txt` injection, `proxy.txt` may contain a fresh authenticated pool while old sticky state remains:

- `device_profiles.json` profile entries still point at proxy URLs not present in current `proxy.txt`.
- `sessions/*.json` may also store old `proxy` values and continue restoring those sessions.
- The active `ProxyPool` can be healthy while selected accounts still fail with 407 because account-level sticky state wins.

## Fix workflow
1. Normalize active proxy file lines:
   - `host:port:user:pass` -> `http://user:pass@host:port`
   - `host:port` -> `http://host:port`
2. Compare normalized active pool against every `profiles[email].proxy` in `device_profiles.json`.
3. Back up `device_profiles.json` first.
4. Rebind any profile with missing/stale proxy to a deterministic proxy from the active pool.
5. Back up then delete any `sessions/*.json` whose saved `proxy` is not in the active normalized pool.
6. Restart the single `webnovel-tg` screen to clear in-memory sessions:

```bash
screen -S webnovel-tg -X quit || true
screen -wipe >/dev/null 2>&1 || true
unset TELEGRAM_BOT_TOKEN TELEGRAM_TOKEN
screen -dmS webnovel-tg bash -lc 'cd /root/webnovel-tg-bot && unset TELEGRAM_BOT_TOKEN TELEGRAM_TOKEN && ./run.sh >> logs/bot-screen.log 2>&1'
```

## Verification
- Probe a sample of current `proxy.txt` with `curl_cffi` against `https://api.ipify.org?format=json`.
- For failed account localparts, confirm their rebound profile proxy returns HTTP 200 from `api.ipify.org`.
- Run a safe Webnovel probe such as `get_power_balance` for one previously failing account.

Expected after fix:
- Previously 407 accounts should either succeed or move to a different real gate such as trust-email OTP, CF/no-csrf, or normal login failure.
- If an account reaches trust email, the 407 proxy-auth issue is resolved for that account.

## Pitfall
Replacing `proxy.txt` alone is not enough. Sticky profile and session cache state can continue using old authenticated proxy credentials until explicitly rebound/cleared.
