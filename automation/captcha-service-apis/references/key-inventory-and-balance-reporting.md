# Key-inventory balance reporting — worked transcript and provider responses

Session context: user asked *"cek api captcha kita yg masih ada saldonya, tunjukkan api key sama
provider nya"*, then challenged the result with *"itu beneran kau hit ke api pas cek balance nya
gak?"*. Both asks are normal and both are answered by the same routine: query every key live, dedupe
by key value, print a flat block, and keep the raw evidence ready.

## The key family found in `~/.hermes/.env`

```
ANTICAPTCHA_API_KEY
CAPMONSTER_API_KEY
CAPSOLVER_API_KEY, CAPSOLVER_API_KEY_2, CAPSOLVER_API_KEY_3
TWOCAPTCHA_API_KEY, TWOCAPTCHA_API_KEY_2.._6
TWOCAPTCHA_KEY_1..TWOCAPTCHA_KEY_14
```

`TWOCAPTCHA_KEY_4` and `TWOCAPTCHA_API_KEY_2` both held `<TWOCAPTCHA_API_KEY_2_REDACTED>`.
Dedupe by key string; counting 27 env vars instead of 26 distinct keys overstates the total.

## Raw provider responses (verbatim)

**2captcha — `GET https://2captcha.com/res.php?key=<k>&action=getbalance`**
plain float, no JSON wrapper:

```
db753f23… -> 4.97841
cc194472… -> 3.98337
8861c78a… -> 3.70199
c102b4fc… -> 3
54081d9b… -> 2.71373
b9d54eed… -> 1.50189
1d4c3fcc… -> 0.10864
82d7c3c7… -> -0.00126      # drained
dd22eca1… -> -0.00134      # drained
```

**capsolver — `POST https://api.capsolver.com/getBalance`** `{"clientKey": "<k>"}`
```json
{"balance":8.2314,"errorId":0,"packages":[]}
{"balance":0.0001,"errorId":0,"packages":[]}
{"balance":0,"errorId":0,"packages":[]}
```

**anti-captcha — `POST https://api.anti-captcha.com/getBalance`** `{"clientKey": "<k>"}`
```json
{"errorId":0,"balance":98.26203}
```

**capmonster — `POST https://api.capmonster.cloud/getBalance`**
```
(empty body, no error payload)
```

## Drift measurements taken within ~40 seconds

```
anti-captcha   06:56:37 -> 98.26603
               06:56:52 -> 98.26203     (-0.004)
               06:57:0x -> 98.26003     (-0.002)
               06:57:0x -> 98.26003
2captcha API_2 2.71518  -> 2.71373       (-0.00145)
2captcha KEY_3 0.11154  -> 0.11009       (-0.00145)
```

`-0.00145` on 2captcha is the list price of roughly one reCAPTCHA solve, so two keys moving by that
exact amount means real solves are happening. The local host had **no** captcha process
(`crontab -l` empty, `ps aux | grep -iE "captcha|solve"` empty, `screen -ls` empty), which points at
shared/resold keys rather than the user's own workload. Report that distinction explicitly — it is
the difference between "your bot is busy" and "someone else is spending your money".

## Evidence block used to answer the liveness challenge

```
HTTP/2 200
server: nginx/1.18.0 (Ubuntu)
date: Wed, 30 Sep 2026 06:57:08 GMT
content-type: application/json; charset=utf-8
access-control-allow-origin: *
```

The combination that convinced the user was: raw body + provider `server`/`date` headers + the
balance visibly decreasing between two calls made seconds apart + an explicit UTC timestamp on the
whole check. Reproduce that triple rather than restating the figure.

## Provider verdict classes observed

| Response shape | Class | Action |
|---|---|---|
| 2captcha float > 0 | `active` | usable |
| 2captcha float < 0 | `valid_empty` | live key, drained — offer `.env` cleanup |
| capsolver `errorId:0` + balance | `active` / `valid_empty` | usable; `0` is live-but-empty |
| capsolver `clientKey is invalid` | `invalid_or_revoked` | exclude |
| `ERROR_WRONG_USER_KEY` (CaptchaAI) | `invalid_or_revoked` | exclude |
| `account authorization key not found` (anti-captcha) | `invalid_or_revoked` | exclude |
| empty body, connection error (capmonster) | `rate_limited_or_blocked` | NEVER report as `$0.00` |
| NextCaptcha generic "insufficient balance" | `indeterminate` | catch-all; not a validity signal |

Cross-provider testing is how an unknown key gets identified, but it generates a lot of
`invalid_or_revoked` noise — an unknown key only responds on **one** provider, so a wall of errors
is the expected shape, not a failure. Only surface the provider that actually answered.

## Reporting cadence

- Print the check timestamp in UTC on the first line.
- Funded keys sorted descending by balance.
- Drained/zero keys in a separated tail block, so the funded list stays scannable.
- One total line, deduped, with a note when a key appears twice in `.env`.
- If any key was printed into a persistent/shared chat surface, add a single rotation note and stop.
