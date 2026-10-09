# ProxyScrape trial export + webnovel inject (2026-07-22)

## Trial length
Proven from live overview:
- `subscription_plan_days = 7`
- `expiration_time - time_activated = 7.0 days`
- UI/ops must show **days left** and exact expiry so user can recreate when expired.

## Overview fields (useful)
```json
{
  "is_trial": true,
  "bandwidth": 10000000000,
  "max_connections": 10,
  "services": {
    "datacenter_shared": {
      "proxy_amount": 100,
      "proxy_username": "...",
      "proxy_password": "...",
      "expiration_time": 1785313556,
      "countries": {"mixed": 100}
    }
  }
}
```

## Proxy list
```
GET /v2/v4/account/{AccountID}/datacenter_shared/proxy-list
  ?format=txt&type=displayproxies&protocol=http
```
- Missing `protocol` → `No protocol provided`
- `format=json&protocol=http` returns rows `[ip:port, HTTP, Online, cc]`
- Port observed: **3129**

## Webnovel inject format
Bot `ProxyPool` expects:
```
host:port:user:pass
```
Convert from:
```
http://user:pass@host:port
```
Backup old `proxy.txt` before replace. Reload live `WebnovelService.pool = ProxyPool(PROXY_FILE)`.

## Register proxy sources (order)
1. `PROXYSCRAPE_REGISTER_PROXY_FILE` (TG sets to bot proxy.txt)
2. local register_proxy.txt / proxy.txt
3. `/root/webnovel-tg-bot/proxy.txt`
4. github-autoreg webshare / webnovel-autoreg proxies
5. direct

## TG commands
- `/proxy` — status + keyboard
- `/proxycreate` — new trial + inject
- `/proxycreate force` — replace active trial
- DB table `proxyscrape_batches` (active/expired/replaced)

## Domain default for trial ops
`<REDACTED>` only. Avoid `<REDACTED>` (disposable). Avoid relying on `<REDACTED>` mail.
