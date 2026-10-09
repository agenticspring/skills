# Recovering an app's API from a HAR export

HAR (HTTP Archive) files exported by a browser's devtools are usually the fastest way to
find the real endpoints — far cheaper than clicking around and guessing. On this job this
was how the deterministic redeem API was found (which replaced a ~300s flaky UI path).

A HAR is JSON:

```
{"log": {"version":"1.2", "creator":{"name":"WebInspector",...},
         "pages":[...], "entries":[ {request:{method,url,headers,postData},
                                     response:{status,content:{text}} }, ... ]}}
```

Note: `WebInspector` exports often hold only a partial/subset of traffic (one had just
21 entries) — that is normal. If a phase looks missing, ask for a re-capture.

## Recipe

1. **Host + endpoint census.** Count hosts; then list unique `(method, path)` filtered to
   `api|graphql|pay|card|checkout|otc|billing|instrument|redeem|invite`. Dedupe on
   `(method, url-without-querystring)` so repeated calls collapse to one line.
2. **Read `postData.text` for the interesting ones.** Meta/GraphQL bodies are
   form-urlencoded, so `urllib.parse.parse_qs(body)` then `json.loads(q["variables"][0])`
   gives you clean structured input. The friendly name lives in the
   `x-fb-friendly-name` header (or `fb_api_req_friendly_name` in the body).
3. **Extract the mutation chain, not just one call.** Ordered friendly-names are the flow:
   `...GetServerEncryptionKeyMutation` → `useFBPayAccountMutation` →
   `...FinalizeCheckoutMutation`.
4. **Inspect structure, never print secrets.** Walk the JSON and print keys plus value
   *lengths/shape only* for anything matching `sensitive|csc|cvv|token|password|card`.
   Printing the value is how card data ends up in a transcript or a repo.
5. **Then reimplement as `fetch()` inside the browser**, not as raw HTTP. The browser
   supplies cookies, `fb_dtsg`/CSRF and CORS automatically; raw `requests` gets
   `403 csrfFailed` no matter how many cookies you copy.

## What "sensitive_string_value" means

Fields shaped `{"sensitive_string_value": "..."}` are client-side transformed before
upload. Length is a useful tell: a 5-6 char value is a token/reference, **not** an
encrypted PAN — meaning the real secret moved through a different channel. When you see
this plus a large device-trust JWT, treat browserless replication as out of scope.

## HAR files are credential material — warn the owner

Real HAR exports carry live secrets. On this job the files contained:

- session JWTs (`eyJ...`) — anyone holding the file can ride the session
- `fb_dtsg` (Meta's CSRF) appearing 30-50x per file
- `platform_trust_token` (device-trust JWT, ~1.2KB)
- partial card data: `credit_card_first_6`, `credit_card_last_4`, billing ZIP

Tell the user plainly, and if they intend to share one, strip the `cookie` /
`authorization` headers, every `fb_dtsg` value, any `platform_trust_token`, and all
`credit_card_*` / `csc` fields first. Never copy a HAR into a repo, notes vault, or
shared doc.

## Durable takeaway

Before reverse-engineering a hardened login/payment flow by hand, ask whether the user
can export a HAR from a browser session where the flow already succeeded. One successful
capture beat a dozen probes.
