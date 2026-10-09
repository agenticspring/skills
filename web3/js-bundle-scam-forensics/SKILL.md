---
name: js-bundle-scam-forensics
description: "Find drainer execution proof inside JS bundles."
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Scam, JS-Forensics, Drainer, Bundle-Analysis, Phishing]
---

# JS Bundle Scam Forensics

Proves a crypto frontend is a drainer by dissecting its compiled JS bundle at
the execution level: what transaction the code actually sends, whether the
recipient is user-controlled or hardcoded, and whether displayed activity is
fake. Verified on `drbriidge.co` (2026-08) where every UI claim contradicted
the execution function.

Complements `scam-site-verification` (which finds the sink and counts victims
on-chain). This skill answers the BEFORE-ONCHAIN questions: does the code call
the real protocol at all, and where does money actually go? It does NOT audit
bytecode (`web3-rpc-contract-audit`) or verify token claims, and it does NOT
require a sink trace to reach a verdict.

## When to Use

- "Ini benar ga?" — someone pastes an analysis claiming a site is a drainer
- Need to PROVE scam from code, not just vibe (a 200-ok site can be all theater)
- A bridge/DEX frontend shows trades/streams but you suspect they're fake
- Comparing a suspicious bundle against a known-legit frontend
- Before reporting to Vercel/Circle — evidence needs code quotes, not screenshots

## Prerequisites

- The site's main JS bundle saved locally (curl the HTML, then curl the
  `<script type="module" src="/assets/*.js">` asset)
- Python3 stdlib `re` is enough (run inside `execute_code`)
- Optional: `cctp-bridge`/`cctp-arc-bridge` skill for real Circle contract
  addresses and domain/chainId facts

## How to Run

1. Save bundle: `curl -s "https://<site>/assets/index-<hash>.js" -o bundle.js` via `terminal`.
2. Run `scripts/analyze_execution.py bundle.js` via `terminal` — prints every
   contract call site, transfer target, and fake-activity array it finds.
3. Interpret with the Procedure below.

## Quick Reference

```bash
# Functions the contract runner calls — the ACTUAL txs the app can send
# (starts of: 'transfer(', 'eth_sendTransaction', 'depositForBurn', 'sendTransaction')

# User-input audit: which inputs exist? (only "number" amount = no recipient field)

# Chain config: usdcAddress / cctpMessenger values per chain (zero = fake)
#   Arc: {usdcAddress: '0x0000...0000'}   ← broken/fake fork signature

# Fake activity: hardcoded array of stream records + setInterval(Math.random)
# e.g. Ne=[{id:'1',type:'OUT',amount:'$25.93',timeAgo:'28m',chain:'Base'}, ...]
```

## Procedure

1. **Fetch the site shell + JS bundle** via `terminal` curl. Check the mini
   HTML for `<script type="module" src="/assets/*">` — that file holds all app
   logic (site definitionally a Vite/Next SPA).
2. **Dump all contract/address constants.** Regex `0x[a-fA-F0-9]{40}` over the
   bundle, then CLASSIFY: Circle USDC/messengers, Uniswap routers, ERC-4337
   EntryPoint, ENS resolver, secp256k1 curve constants are library noise; what
   remains is the app's own constants.
3. **Find the single execution function.** The bridge submit handler is one
   `async function` that returns a `.hash`. Read it top-to-bottom:
   - Chain with a real USDC address → `new Contract(usdcAddr, abi, signer).transfer(recipient, amount)` — a plain ERC-20 send, NOT burn/mint.
   - Chain whose config is `0x0000...0000` → `eth_sendTransaction({to: recipient, value: amount})` — native send.
   - If both paths exist and neither calls `depositForBurn`, done: it is not a bridge, it transfers directly.
4. **Check recipient authority.** Find every assignment to
   `recipientAddress`/initial state. If the bundle hardcodes one address AND
   overwrites it at wallet-connect (`{address: wallet, recipientAddress: b}`),
   the user cannot change destination (verify: the only `<input>` is
   `type:"number"` for amount). no user recipient field = hardcoded payee.
5. **Check fake activity.** Look for `setInterval(...Math.random()...1e4)`
   writing hardcoded records (`[{id, type:'OUT', amount:'$...', timeAgo, chain}]`).
   A real explorer pulls history; this is theatrical volume.
   Also grep for `status: 'COMPLETED'` being set right after a plain transfer —
   the UI celebrates empties.
6. **Capture the wallet-connector tell.** Error strings mention the target
   wallet (e.g. `You rejected the prompt in OKX Wallet`) — tells you who the
   investors the phisher hosts.
7. **Verdict from code, then hand off.** If recipient is a hardcoded EOA,
   execution is a transfer, and the UI fabricates volumes — that's a drainer.
   Output the sink address for `scam-site-verification` to trace on-chain.

## Pitfalls

- **UI strings ≠ execution.** `TokenMessenger.depositForBurn()` in a progress
  label does not mean the code calls it. Only the returned tx from the execution
  function counts; same for status text vs status writes.
- **Zero-address config is a scale.** One broken chain config is definitive if
  the legit chains have real addresses while your target chain is `0x0`. It
  proves the author copied a frontend and 140-removed the expensive parts.
- **`chainIdNum` reuse.** Config with `chainIdNum: 26` for a 5042 chain = the
  fork author reused CCTP domain as chain id. That is a code-level flag, no
  onchain needed.
- **Do not over-trust pretty Vercel hosting.** Hosting is neutral — read the
  bundle, not the certificate.
- **Minified bundle readability.** Work on one `context slice` of ~200-400
  chars around hits rather than the whole 500KB file; print `context` not the
  raw blob.

## Verification

```bash
# A drainer's bundle proves itself with this invariant:
python3 -c "
import re
b=open('bundle.js').read()
execs=re.findall(r'\.(transfer|eth_sendTransaction|depositForBurn)\(', b)
print('transfer', len([x for x in execs if 'transfer' in x]),
      'depositForBurn', len([x for x in execs if 'depositForBurn' in x]))
"
# transfer > 0 AND depositForBurn == 0  ⇔  not a bridge
```