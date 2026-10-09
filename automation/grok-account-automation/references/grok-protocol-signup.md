# Grok Protocol Signup (SignupServerAction) — Alternative Registration Path

Session: 2026-08-08. Implemented + tested. **Works end-to-end (produces SSO + accounts + 9Router connections) but does NOT bypass `bfs` — all protocol-signed accounts still got `bfs:1`.**

Source: `grokRegister-cpa-catchmail` repo (Userluckytian) claims protocol signup avoids `bot_flag_source` ("UI 注册页路径容易打上 bot_flag_source=1，协议注册 + Device Flow 出号更稳"). Our test disproved that for a datacenter-proxy + farm-domain account: flag persists regardless of signup path.

## Flow (all HTTP, no UI page)

```
1. GET  https://accounts.x.ai/sign-up?redirect=grok-com   (browser headers)
   → extract site_key (0x4AAAAAAA...), state_tree (Next.js flight), action_id
2. POST auth_mgmt.AuthManagement/CreateEmailValidationCode  (grpc-web, field1=email)
3. Poll IMAP for XXX-XXX code
4. POST auth_mgmt.AuthManagement/VerifyEmailValidationCode  (fields 1=email,2=code)
5. POST /sign-up?redirect=grok-com  (NOT gRPC — Next.js server action!)
   Headers: Accept: text/x-component, Content-Type: text/plain;charset=UTF-8,
            Next-Action: <action_id>, Next-Router-State-Tree: <state_tree>
   Body (JSON array):
   [{
     "emailValidationCode": code,
     "createUserAndSessionRequest": {
       "email", "givenName", "familyName", "clearTextPassword",
       "tosAcceptedVersion": "$undefined"          // NOT 1, NOT "1"
     },
     "turnstileToken": <real solve>,
     "conversionId": "<uuid>",
     "castleRequestToken": ""
   }, {"client": "$T", "meta": "$undefined", "mutationKey": "$undefined"}]
   → 200 text/x-component; SSO arrives via set-cookie hops (below), NOT in body text
6. Follow the set-cookie hop chain to obtain the `sso` cookie
```

## Action ID discovery (pitfall: it's NOT in the HTML)

- The `Next-Action` id is a 40-50 hex string defined in a JS chunk via `createServerReference("...", callServer, ...)`.
- The signup chunk is `3meced5pfki1l.js`; two refs exist: `7f09a33abde784e87cd6cf347b96ec73d7ece6e695` (used as `mutationFn: tY` — THIS is createUserAndSession) and `00b9249c2e02ce5b2380649dd262648f3b208daaa2` (other action).
- Confirmed mutation usage: `{mutate: ti} = useMutation({mutationFn: tY})`, called with the exact payload above.
- **JS src regex pitfall**: chunk URLs now carry `?dpl=...` after `.js` — `src="(/_next/static/[^"]+\.js)"` fails to match; use `src="(/_next/static/[^"]+\.js[^"]*)"`.
- If the action id is wrong, the server action silently renders the full page instead of returning a mutation result — no error, just a page. Check for `text/x-component` response containing set-cookie hop URLs as the success signal.

## Set-cookie hop chain (this is how SSO actually arrives)

The signup response body contains a hop URL like:
`https://auth.grokipedia.com/set-cookie?q=eyJ...` (chained via JWT `config.success_url`).

Decode the JWT in `?q=` — its `config` has `{token, success_url}`. The chain is:
```
auth.grokipedia.com/set-cookie?q=JWT1
  → config.success_url = auth.grokusercontent.com/set-cookie?q=JWT2
    → auth.grok.com/set-cookie?q=JWT3
      → auth.x.ai/set-cookie?q=JWT4
        → accounts.x.ai ... (307, ends)
```
`sso` cookie is SET at the `auth.grok.com` and `auth.x.ai` hops (`Max-Age=15552000` = 180 days).

**Pitfall — grokipedia hop 400s from curl_cffi**: the first hop (auth.grokipedia.com) returns HTTP 400 (needs `__cf_bm` / browser context). **Skip it**: decode JWT1's `config.success_url` and GET that directly — the grokusercontent hop then 303s and sets `sso`. You don't need to hit grokipedia at all.

## Result / negative finding

- Protocol signup produced working accounts: SSO captured, device-approve 303, 9Router poll success, connection created.
- **But the OAuth access token STILL contains `"bfs": 1`** — both with and without `?redirect=grok-com` on the signup URL. Removing the redirect param only changed Set-Cookie (`referrer=grok-com` → `last-logged-in-with=EMAIL`), not the flag.
- Further variation tests (2026-08-08) also all yielded `bfs:1`:
  - **Proxy provider swap**: 3xK Tech pool → webshare/Leaseweb (`31.59.x`, creds `bvytlgye:fritszjb82rs`).
  - **Email domain swap**: `<REDACTED>` → `<REDACTED>` (both catch-all → Gmail).
- Conclusion: `bfs` is NOT determined by signup path (UI vs protocol), the referrer cookie, the DC proxy provider, or the farm email domain. Narrowed suspects: the **Capsolver Turnstile solve pattern** itself (the one constant across all tests — xAI may fingerprint solver-produced tokens) or real-browser fingerprint at signup. True residential-IP signup remains untested (none available in this environment).

## Scripts

- `/root/grok-register/protocol_signup_test.py` — single protocol signup, prints SSO claims
- `/root/grok-register/protocol_full_test.py` — protocol signup → chain → approve device → check bfs in 9Router token
- `/root/grok-register/protocol_noredir_test.py` — same without `?redirect=grok-com`
