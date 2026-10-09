# TanStack Start /_serverFn — worked Bandit List run (2026-08-17)

Target: `https://playbandits.xyz/claim` (The Bandit List allowlist claim),
tweet `https://x.com/playbandits/status/2089381817904435553`.

## What it is

- Lovable/TanStack Start app. Mint gated behind an allowlist claim: connect
  wallet → sign message → server checks membership → locks a mint spot.
- Claim is NOT a free mint — it reserves a spot for a later OpenSea mint
  ("minting soon on opensea", "Your spot is locked to your wallet").

## Bundle / function map

Main bundle `/assets/index-C8eMZaQz.js` (TanStack Router). Route chunk
`claim.index-DkuUj_Zf.js` imports `claim.functions-iG5kA0kl.js` and
`ClaimApp-BNO_tMTL.js`.

`claim.functions-iG5kA0kl.js` tail (function registrations):

```js
w=h({method:"POST"}).handler(e("dd0dff83ee1a3fd525f7a70dc9dbdd473f25b411997ff34d8810ff8c4aa35743"))  // check eligibility (export l)
T=h({method:"POST"}).handler(e("8f4fe76c1f6172085eb1468b7ec2b94612768ee4c8fbf82781d832c39497c74c"))  // claim (export u)
E=h({method:"GET"}).handler(e("1615536e23a86f8f8c435f8471ce449b9db06943e03f450f9f8a4a86a772c84d"))   // leaderboard (export c)
...
export{k as a, E as c, C as d, x as f, O as i, w as l, M as n, A as o, N as r, D as s, j as t, T as u}
```

ClaimApp import mapping: `import{c as e, d as t, f as n, l as r, s as i, u as a}`
→ `r` = check (`dd0dff83...`), `a` = claim (`8f4fe76c...`),
`e` = leaderboard (`1615536e...`), `i` = register/claim-token fn.

## Wire protocol

- Endpoint: `POST /_serverFn/<sha256>` (NOT `/_server`).
- Headers required: `Content-Type: application/json`, `x-tsr-serverFn: true`,
  `accept: application/json`, `Origin: https://playbandits.xyz`,
  `Referer: https://playbandits.xyz/claim`, cookies from prior page load.
- Without Origin/Referer/cookies: `403 Forbidden`.
- Body: `{"data": {...}}`. Plain JSON worked for the check function when the
  payload shape matched (`{"data":{"address":"0x...","purpose":"claim"}}`),
  but the CLAIM function returned `Seroval Error (step: 3)` on raw JSON —
  use the in-page import path below instead.

## Working invocation (Camofox eval)

```js
// check eligibility — returns sign-message string
import('/assets/claim.functions-iG5kA0kl.js')
  .then(m=>m.l({data:{address:'0xBff994004E9558A8e7e4CD0D817884dC7ff8e65d',purpose:'claim'}}))
  .then(r=>JSON.stringify(r).slice(0,900))

// after signing locally:
import('/assets/claim.functions-iG5kA0kl.js')
  .then(m=>m.u({data:{message:'<exact sign message>',signature:'<0x sig>'}}))
  .then(r=>JSON.stringify(r).slice(0,1200))
```

Sign the message with ethers (NOT cast):
```js
const { ethers } = require("ethers");
const wallet = new ethers.Wallet(PK);
const sig = await wallet.signMessage(msg); // personal_sign semantics
```

Result for Set 1: `{"status":"not_eligible"}`. Leaderboard GET worked with
raw curl: `?_serverFn/1615536e...?data=...` returns Seroval JSON of
community counts (h00dle 204, script_kiddies 127, onchain_hoodies 108, ...).

## Lessons

- Bare curl to `/_serverFn` gets 403 until Origin/Referer/cookies are set.
- `import()` inside `camofox eval` is the escape hatch for Seroval encoding —
  let the framework serialize, never hand-craft Seroval.
- Minified export names must be mapped from the chunk tail before calling;
  the wrong export = wrong function (Seroval error or unrelated result).
- Allowlist claims are NOT mints; the claim locks a spot for a later mint and
  the site says the mint date drops on X first.
