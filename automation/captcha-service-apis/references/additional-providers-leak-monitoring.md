# Additional CAPTCHA providers for public-secret leak monitoring

Condensed provider notes for **authorized, responsible monitoring**. Detection should normally be `identify → redact → notify/revoke`; do not validate third-party credentials without explicit authorization. Balance/status endpoints below are read-only, but responses can expose account metadata.

## Provider matrix

| Provider | Documented secret format | Read-only endpoint | Method and authentication | Official source |
|---|---|---|---|---|
| uCaptcha | Prefix `ucap_` followed by a random alphanumeric string; docs do not state suffix length | `https://api.ucaptcha.net/getBalance` | `POST` JSON: `{"clientKey":"<key>"}` | [Authentication](https://ucaptcha.net/docs/getting-started/authentication/), [getBalance](https://ucaptcha.net/docs/api/ucaptcha/get-balance/) |
| Solvex | Prefix `sk_live_`; docs do not state suffix length/charset | `https://api.solvex.run/getBalance` | `POST` JSON: `{"clientKey":"<key>"}` | [API docs](https://solvex.run/docs) |
| CaptchaAI | Exactly 32 characters; docs do not normatively specify charset/prefix | `https://ocr.captchaai.com/res.php` | `POST multipart/form-data`: `key=<key>`, `action=getbalance`, optionally `json=1` | [Official balance OpenAPI](https://docs.captchaai.com/api/balance.yaml), [API reference](https://docs.captchaai.com/api_v1/) |
| SolveCaptcha | Exactly 32 characters; official example resembles lowercase hex, but docs only guarantee length | `https://api.solvecaptcha.com/res.php` | `GET` query: `key=<key>&action=getbalance` | [Captcha Solver API](https://solvecaptcha.com/captcha-solver-api) |
| NextCaptcha | Named `clientKey`; no documented prefix, length, or charset | `https://api.nextcaptcha.com/getBalance` | `POST application/json`: `{"clientKey":"<key>"}` | [getBalance](https://nextcaptcha.com/en/apidocs/get-balance), [API docs](https://nextcaptcha.com/en/apidocs) |
| NopeCHA | Named subscription key; no documented prefix, length, or charset | `https://api.nopecha.com/status/` | `GET` query: `key=<key>`; returns plan, credit, quota, and reset metadata | [Subscription status](https://developers.nopecha.com/status/subscription/), [Status API](https://developers.nopecha.com/status/) |
| ImageTyperz / CaptchaTypers | Access token supported; no documented prefix/length/charset | `http://www.captchatypers.com/Forms/RequestBalanceToken.ashx` | `POST` form: `token=<token>&action=REQUESTBALANCE`; legacy username/password is also supported | [Official API page](https://www.imagetyperz.com/Forms/api/api.html), [official source docs](https://github.com/imagetyperz-api/API-docs) |
| EndCaptcha | No API key: username/password pair | `http://api.endcaptcha.com/balance` | `POST` form fields `username` and `password` | [HTTP API specifications](https://endcaptcha.com/api-specs) |

## Detection guidance

1. Prefer provider-owned prefixes where documented:
   - uCaptcha candidate: `ucap_[A-Za-z0-9]+`
   - Solvex candidate: `sk_live_[A-Za-z0-9_-]+`
2. Treat these as **candidate patterns**, not proof. Apply boundaries, minimum entropy, assignment-name/domain context, allowlists, and test-fixture suppression.
3. `sk_live_` is not globally unique to Solvex. Require Solvex context such as `api.solvex.run`, a provider name, or an adjacent Solvex configuration key.
4. For 32-character providers, do not silently narrow to hex unless official documentation guarantees hex. Length-only matching has high false-positive risk; require identifiers such as `CAPTCHAAI_API_KEY` or `SOLVECAPTCHA_API_KEY` and provider-domain context.
5. For NextCaptcha, NopeCHA, and ImageTyperz, avoid value-only regexes. Detect contextual assignments and high-entropy values.
6. EndCaptcha should be modeled as a contextual credential pair, not a standalone API-key detector.
7. ImageTyperz and EndCaptcha documentation advertises plain-HTTP balance URLs. Do not transmit a secret over those URLs; first obtain an officially confirmed HTTPS endpoint or avoid live validation.
8. A valid zero balance still indicates a live credential. Distinguish invalid/revoked, valid-empty, valid-funded, blocked/rate-limited, and indeterminate outcomes.

## Research discipline

- Cite provider-owned documentation for **each** format and endpoint claim.
- Clearly distinguish a normative format statement from an example that merely resembles hex or another charset.
- If docs omit prefix/length/charset, report that explicitly rather than inventing a regex.
- Never test real credentials or make authenticated calls during documentation research unless the user explicitly authorizes controlled validation of credentials they own.
