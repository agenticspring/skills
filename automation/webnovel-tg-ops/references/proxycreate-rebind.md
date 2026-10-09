# ProxyCreate / Proxy Inject Rebind Checklist

Use this after any ProxyScrape trial replace or proxy pool refresh.

## Why
Replacing `proxy.txt` is not enough. Accounts can keep stale sticky state:
- `device_profiles.json` may still point to old proxy URLs.
- `sessions/*.json` may still restore old proxy values.
- In-memory `svc._sessions` can keep the old mobile session alive until restart.

This is the root cause behind recurring `curl: (56) CONNECT tunnel failed, response 407` even after a fresh proxy inject.

## Required steps
1. Normalize active `proxy.txt` entries.
2. Rebind any profile proxy not present in the active normalized pool.
3. Backup and delete session cache files whose stored proxy is stale.
4. Reload the live proxy pool.
5. Clear in-memory service sessions.
6. Restart the single `webnovel-tg` screen if a long-running bot process may still hold old state.

## Verification
- Sample the active proxies with `api.ipify.org` or similar.
- Probe one previously failing account with `get_power_balance`.
- If the account now reaches trust-email OTP or CF/no-csrf, the proxy 407 issue is fixed.

## Relation to `/proxycreate`
`/proxycreate` should perform this rebind automatically after inject and report counts for:
- rebound profiles
- removed stale sessions

If those counts are zero because the pool is already clean, that is fine.
