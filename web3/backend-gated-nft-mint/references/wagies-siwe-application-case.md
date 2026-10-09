# WAGIES SIWE-style Whitelist Application (verified 2026-08)

Browserless whitelist application for wagies.xyz: `personal_sign` login +
AI chat interview → HIRED verdict + offer-letter PNG. Set 1
(0xBff994004E9558A8e7e4CD0D817884dC7ff8e65d) accepted, ref code f20eee7c.
Signature-only end-to-end: no gas, no approve, no transaction anywhere.

## Recon summary

- Landing page bundle contains ZERO wallet code and zero crypto addresses.
  The whole flow lives in a widget JS (`doris-widget.js`) loaded by the
  `/careers/` subpage only.
- Backend: single Railway API (`web-production-520ec.up.railway.app`),
  endpoints `/api/session`, `/api/verify`, `/api/message`, `/api/handle`,
  `/api/stats`, `/api/letter/<app_id>.png`.
- Safety audit pattern that cleared it: grep bundle for
  eth_sendTransaction / signTypedData / approve / switchEthereumChain — all
  absent; only `eth_requestAccounts` + `personal_sign`. Probe
  `message_to_sign` with a dummy address before ever signing with a real one.

## Verified flow (eth_account, no browser)

1. Derive address+pk from `.springwallet` Set N in `/dev/shm` (ephemeral).
2. `POST /api/session {wallet, ref:""}` (header `origin: https://wagies.xyz`)
   → `{app_id, message_to_sign}` where message =
   `WAGIES Corp job application — <random hex>`.
3. Sign locally:
   ```python
   from eth_account import Account
   from eth_account.messages import encode_defunct
   sig = Account.from_key(pk).sign_message(encode_defunct(text=msg)).signature.hex()
   ```
4. `POST /api/verify {app_id, signature}` → `{ok:true, q_index:0, doris:...}`.
5. Interview = 4–5 `POST /api/message {app_id, text}` turns. Final response
   carries `{verdict:"HIRED", title, letter_url, ref_code}`.
6. Letter PNG at `API + letter_url`; global stats at `GET /api/stats`
   ({cap, hired, total_applications}).

## Session quirks (all hit live)

- Re-POSTing `/api/session` for an already-verified wallet RESUMES: returns
  `{app_id, history:[...]}` with NO `message_to_sign`. That app_id is already
  verified — skip verify, go straight to `/api/message`.
- Stale/expired app_id on `/api/message` → HTTP 404 `{"error":"No active
  application"}`. Redo session (+verify if asked) for a fresh app_id.
- Read HTTPError bodies: they carry the real reason ("Bad signature",
  "Signature doesn't match wallet"). Treat 400 as diagnostic, not opaque.
- Interview answers are free-text judged by an LLM persona; playful
  memecoin-flavored answers passed. One word minimum or it re-asks.

## Signing gotchas

- `cast wallet sign <file>` signs the LITERAL PATH STRING, never file
  contents → server sees "Signature doesn't match wallet". Use
  eth_account `encode_defunct(text=...)` or pipe via stdin:
  `printf %s "$MSG" | cast wallet sign --private-key $PK -`.
- personal_sign here is standard EIP-191 of the UTF-8 text; no chainId,
  no typed data, no nonce beyond the random hex in the message itself.
