# Signed whitelist-seat claim (personal_sign + /join worker)

Worked 2026-08-21 on Invisible Divisions (`invisibledivisions.xyz`, Ethereum
mainnet) — a 500-seat free-mint whitelist gated by a Cloudflare Workers
collector that verifies a wallet signature. Distinct from plain `POST {wallet}`
whitelists and from TanStack server functions.

## Site recon pattern

- Page title/meta reveals the mechanic: "500 FREE MINT WHITELIST", "SEATS",
  "FIRST COME, FIRST INSCRIBED", "A SEAT IS NOT A MINT".
- Config lives inline in the page HTML (`const WHITELIST_ENDPOINT = '...'`)
  plus a comment: "Any endpoint that accepts POST JSON {address, ts} works".
- Read the full submit handler in the page source BEFORE batch — the real
  payload is NOT the config comment; the JS does sign-then-submit:
  1. build message (plain text with project name + "TS: <epoch_ms>");
  2. `eth.request({method:'personal_sign', params:[msg, account]})`;
  3. `fetch(ENDPOINT + '/join', {POST, body:{message, signature}})`.

## Endpoints observed

- `GET <endpoint>/count` → `{claimed, cap, open}`. `open:false` disables the
  button; the page shows "ALL N SEATS CLAIMED".
- `POST <endpoint>/join` `{message, signature}` → `{ok:true}` = seat secured;
  `{ok:true, already:true}` = duplicate wallet; HTTP 409 = cap reached
  ("ALL 500 SEATS ARE GONE"); 404 on the bare endpoint (root path has no
  handler — must use `/join`).

## Batch procedure (100 wallets)

1. Derive each Set's private key ephemerally (`cast wallet private-key
   --mnemonic <tmp>`, file in `/dev/shm`, chmod 600, unlink after).
2. Build the message EXACTLY as the site does — newline-separated, with the
   literal project title and `TS:<epoch_ms>`. If the site uses
   `personal_sign`, ethers `Wallet.signMessage(message)` reproduces it
   (no `0x` prefix needed — signMessage handles the personal_sign prefix).
3. Sign locally (`NODE_PATH=/tmp/node_modules node sign.js` with ethers;
   or `cast wallet sign`). Never send the private key anywhere.
4. POST `/join`; record `{ok, status}` per wallet.
5. Seat cap is global and fills FAST — a sequential 100-wallet batch can hit
   409 mid-run (observed: Set 1 secured, Sets 2+ all 409). Do Set 1 first as
   the probe; if cap is near, expect losses. Check `/count` before and during.

## Pitfalls

- `personal_sign` message must byte-match the site's JS exactly — any
  whitespace/TS mismatch makes the worker reject the signature.
- The worker endpoint 404s on the bare origin path — always POST to `/join`.
- 409 = cap reached, not a transient error; stop the batch, don't retry.
- A "seat" is a whitelist spot, NOT the mint: be present at drop time or the
  seat rolls to public sale.
- This pattern (signature-verified collector on Cloudflare Workers) is common
  for small free-mint drops; the same flow works for Formspree/sheet hooks if
  they verify signatures server-side.
