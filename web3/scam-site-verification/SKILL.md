---
name: scam-site-verification
description: "Verify a crypto site is a scam and trace its sink wallet."
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Scam, Phishing, Bridge, Wallet-Tracing, Recon, Victim-Counting]
---

# Scam Site Verification & Sink Wallet Tracing

Determines whether a crypto/bridge/DeFi website is a scam frontend, extracts
the sink wallet that collects victim funds, and counts real victims on-chain.
Verified on `drbriidge.co` (fake "DR Bridge — Native USDC CCTP Bridge", 2026-08):
a broken fork of a legit frontend whose chain config routed everything to a
zero-address sink and whose drain flowed to a known bot-sybil cluster.

Does NOT audit contract bytecode for exploits (see `web3-rpc-contract-audit`),
does NOT verify tweeted-token claims (`token-launch-verify`), and does NOT map
general site infrastructure (`site-recon`). This skill is the scam-specific
variant: find the money sink, prove it is the sink, count victims.

Also covers the adjacent honesty question **"is this chain / RPC endpoint
real?"** — fake or impersonated networks handed over as a Name / Chain ID / RPC
block. See the chain/RPC authenticity section below and
`references/chain-rpc-authenticity.md` (worked GIWA case, full probe transcript).

## When to Use

- "Cek apakah ini scam atau bridge asli" / "apakah ini situs penipuan?"
- "Pastikan websitenya aman jika konek wallet" — safe-to-connect audit
  (see Procedure step 9)
- A bridge/DEX/faucet site appears with a fresh domain and asks to connect wallet
- Need to quantify losses: "berapa banyak yang sudah ke-scam?"
- Comparing a suspicious site against a known-legit frontend (same bundle, broken config)
- Finding whether a scam wallet is still active / draining
- "Ini real RPC <chain> kah?" / "apakah chain ini beneran?" — someone hands over a
  Name + Chain ID + RPC URL and asks whether it is safe to use (see the
  chain/RPC authenticity section)

## Prerequisites

- Python3 `re` for JS-bundle address extraction (via `execute_code`)
- Blockscout v2 API for token transfers: `https://<chain>.blockscout.com/api/v2`
- RPC for `eth_getCode`/`eth_getBalance` cross-chain checks
- No API keys — all public endpoints

Concrete worked example (drbriidge.co full trace):
`references/drbriidge-case.md`

## How to Run

Invoke through `terminal`/`execute_code`: curl the site HTML + JS bundle,
`execute_code` regex for addresses and config, Blockscout REST for transfers.
Never connect a wallet or sign anything on the suspect site.

## Quick Reference

```bash
# Site + bundle
curl -sL "https://<site>/" -o home.html
curl -s "https://<site>/assets/<bundle>.js" -o bundle.js

# Extract addresses + find sink
# via execute_code: re.findall(r'0x[a-fA-F0-9]{40}', bundle)
# grep for: recipientAddress | feeRecipient | beneficiary | owner

# Blockscout transfers into a wallet
curl -s "https://base.blockscout.com/api/v2/addresses/<SINK>/token-transfers"

# Cross-chain existence
# eth_getCode on the SAME address across ETH/Base/Arb/Arc — contract on one chain only?
```

## Procedure

1. **Fetch HTML + JS bundle.** Grep the bundle for `0x[a-fA-F0-9]{40}`
   addresses AND for `recipientAddress` / `feeRecipient` / `beneficiary` /
   `owner` — the default recipient in a bridge frontend is the scam sink.
2. **Classify every address.** Known-good = Circle USDC/messengers, Uniswap
   routers, ERC-4337 EntryPoint, ENS resolver, secp256k1 curve constants.
   Everything else is custom and suspect. Zero addresses in *chain config*
   (`usdcAddress: 0x0000...0000`, `cctpMessenger: 0x0000...0000`) are the
   signature of a broken/fake fork — a real bridge never routes to 0x0.
3. **Check chain config numbers.** Confuse chainId with CCTP domain = amateur
   fork. Example: Arc chainId is 5042 (0x13b2), CCTP domain is 26 — a config
   saying `chainIdNum: 26` for Arc is wrong even when the domain is right.
4. **Trace the sink on Blockscout** (`/api/v2/addresses/{SINK}/token-transfers`,
   paginate with `next_page_params`). For every transfer record: token symbol,
   raw value + decimals, from/to, timestamp.
5. **Distinguish victims from test transfers — the critical step.** Senders
   with near-identical addresses (same suffix, e.g. `...D6DBb` /
   `...6D6DBB`, `...697ab` / `...7697AB`) are **vanity pairs made by the
   scammer** testing their own frontend — NOT victims. Do NOT count them as
   losses. Real victims are unrelated unique EOAs sending real value.
6. **Look for drain transactions.** `transferAndMulticall`, `approve` to a
   router (e.g. `MetaAggregationRouterV2`), swap via `RelayRouterV3`, then
   trace the final destination. Cross-check the destination against known
   bot-sybil operators from prior investigations (e.g. `0xF70dA978...`).
7. **Check if the sink is still active.** Recent tx (`transferAndMulticall` in
   last 24h) = drainer armed and waiting for real victims.
8. **Report.** Verdict (scam/drainer vs legit), sink address, real-victim count
   (exclude vanity pairs), total drained, active/inactive status.
9. **Safe-to-connect audit** (worked on wagies.xyz 2026-08 → LEGIT,
   signature-only). Same bundle dissection, different question: "boleh konek
   wallet?" Grep ALL site JS — main bundles AND subpage-only widget scripts
   (the wallet flow often lives in a separate file loaded only by the signup
   page, e.g. wagies' `doris-widget.js` on `/careers/`) — for:
   `eth_sendTransaction`, `signTypedData`, `.approve(`,
   `wallet_switchEthereumChain`, `addEthereumChain`, transfer call sites.
   Classify every wallet interaction: `eth_requestAccounts` + `personal_sign`
   of a server-provided plain message = login gate that cannot move funds;
   anything constructing txs/approvals = not safe by default. Enumerate all
   backend endpoints; probe challenge fields with a DUMMY address before ever
   signing with a real one (inspect `message_to_sign` is plain text). Zero
   hardcoded 0x…40 addresses anywhere = strong no-sink evidence. Verdict
   wording: "aman konek" ≠ proyek bagus; future mint contracts are a new
   audit surface.

## Fake chain / RPC endpoint authenticity

Question shape: someone hands over `Name / Chain ID / RPC URL` and asks "is this
real?". Answer it from the chain itself plus domain forensics — never from the
claim, and (when the user says so) not from the project's documentation either.
Worked case: a leaked "GIWA mainnet" RPC, 2026-09.

**The core trap: a fake chain can wear a REAL reserved chain ID.** GIWA (an OP
Stack L2 by Dunamu/Upbit) had chain ID `9134` registered in
`ethereum-lists/chains` a year before launch, so the supplied RPC answering
`eth_chainId = 0x23ae (9134)` proved **nothing**. Always check *who* added the
registry entry and when:

```bash
curl -s "https://api.github.com/repos/ethereum-lists/chains/commits?path=_data/chains/eip155-<id>.json&per_page=5"
```

A commit by the project's own team means the ID is legitimately theirs — which is
precisely what an impersonator borrows. A commit by an unrelated account means
chain-ID squatting.

### Checklist — cheapest first

1. `eth_chainId` + `net_version` — does the RPC actually serve the ID it advertises?
2. Registry file: `https://raw.githubusercontent.com/ethereum-lists/chains/master/_data/chains/eip155-<id>.json`.
   **An empty `"rpc": []` means no official RPC is published** — the biggest single tell.
   `"status": "incubating"` is also a signal.
3. `eth_getBlockByNumber("0x0")` → genesis timestamp. A "mainnet" whose genesis is hours old
   is not a live mainnet.
4. Domain forensics: `whois <domain>` (creation date), apex `A`/`AAAA`, TLS `notBefore`
   (`openssl s_client … | openssl x509 -noout -dates`), `ipinfo.io/<ip>` for ASN/hosting.
   A domain registered **the same day** with **no apex records at all** — only the single RPC
   hostname — is the whole story. Cheap VPS hosting reinforces it.
5. `net_peerCount` (a public network at `0x0` is odd) and `txpool_status` (often 403).
6. **L1 anchor:** on OP Stack, `eth_call` to `0x4200000000000000000000000000000000000015`
   with selector `0x8381f58a` (`number()`) and compare against a real L1 height. Matching ⇒
   the chain genuinely is anchored to that L1 — so it is a *real deployment*, just not
   necessarily *that project's*.
7. `eth_getCode` sweep for predeploys + canonical infra (Multicall3, Permit2,
   Create2Deployer, SafeSingletonFactory, EntryPoints, EAS).

### Block production is NOT activity

An OP Stack chain **emits a block every second with zero users**; each such block contains
exactly one transaction — the **system deposit** (`from 0xdead…0001` → `L1Block 0x4200…0015`,
type `0x7e`, ~46,230 gas). Therefore:

- `eth_blockNumber` growing is a **heartbeat, not a launch signal**. Say that explicitly.
- Census it: `eth_getBlockTransactionCountByNumber` over all blocks — any block with `!= 1`
  tx is real activity. Sampling `gasUsed` works too (deposit ≈ 46k; far above ⇒ a user tx).
- Then pull the anomalous blocks with full txs: senders, `to == null` (deployment), selectors.
  `from == to` self-transfers of small value are **bridge-to-self tests**, not organic users.

**Expect this behaviour while scanning:** such endpoints often **reject JSON-RPC batches
larger than ~10** (batch 25 → HTTP 400) and **rate-limit hard** under concurrency — a
20k-block census at 24 workers returned answers for only 3,876 blocks. Single requests were
~0.12 s, so scan with many *small* batches, slowly, and **report the sampled fraction
honestly** rather than implying full coverage.

### Safety verdict to give

- **Read-only `curl` JSON-RPC is safe for funds** — no keys, no signing. Real caveats: the
  operator sees your IP and query pattern, and **the answer is unverifiable** (no second RPC,
  no explorer ⇒ "there are blocks" is only that RPC's word).
- **Never add it as a custom network in a wallet holding keys.** Wallets auto-query
  `eth_accounts` / `eth_getBalance` / `eth_getCode` across accounts, so a hostile RPC clusters
  every wallet you own and can serve fabricated balances/tokens to bait an approval.
- A live, mainnet-anchored, actively-deploying chain is **still not proof of ownership** —
  when the user says it is a *leaked* endpoint (leaker fronting the project's internal node
  behind their own fresh domain), say plainly that chain data alone cannot separate "leaked
  real staging node" from "copycat wearing the reserved chain ID".
- Point at tamper-proof launch signals instead: the project's own docs network table, and the
  registry `rpc` array flipping from `[]`.

## Pitfalls

- **Fresh domain ≠ "no scam yet".** Check the site's launch date vs the first
  sink transfer. drbriidge.co was 1 day old with $54 in test transfers already
  drained — the drainer was armed, just no real victims yet.
- **Response 200 proves nothing.** The site works; the config is what lies.
- **Don't count vanity-pair senders as victims.** Two addresses sharing a
  suffix (same last 6+ chars) are one operator testing. Only unique,
  unrelated EOAs count.
- **Don't stop at the first transfer page.** Paginate token-transfers fully
  before concluding "no losses".
- **Native balance ≠ scam take.** The sink may hold ETH from other operations;
  the USDC/token inflows on the bridge chains are the scam-specific measure.
- **"Powered by X" footer = fork tell.** A scam site embedding a legit
  project's branding (@DyorSwapdex in drbriidge's bundle) means someone cloned
  the frontend — verify the legit project didn't deploy this domain.
- **Vercel hosting is neutral.** Vercel/AWS/Railway hosting is free-tier
friendly; the discriminator is the JS config and the sink, not the host.
- **Wallet flow can hide in subpage widgets.** The landing page may have zero
wallet code; check every `<script src>` on EVERY page — signup/careers/
apply pages often load their own widget JS with the real flow.
- **A chain ID matching the real project proves nothing** — reserved IDs are
  public in `ethereum-lists/chains` and are the impersonator's favourite
  prop. Verify the *entry's provenance*, not the number.
- **Don't accept the project's docs as the answer when the user asks for chain
  evidence.** Dez explicitly redirected: "ga usah baca dokumentasi dulu … kau
  cek aja RPC-nya ada aktivitas tx dll atau infra yg udh ada". When asked to
  verify something, probe the source itself and report what the data shows.
- **Uniform 1 tx/block is not "a working chain".** On OP Stack that is only the
  system deposit — zero users. Never report "produksi blok aktif" as if it meant
  adoption or a live launch; state the heartbeat-vs-activity distinction.
- **Don't infer ownership from infrastructure.** Canonical deployments
  (Multicall3 3,808 B, Permit2 9,152 B, Create2Deployer 1,584 B) exist at the
  same address on nearly every EVM chain, and OP Stack predeploys (WETH9,
  EAS, L1Block, bridges) are stock. Only project-specific contracts and the L1
  counterpart contracts carry signal.

## Verification

```bash
# Proves the sink collected funds and shows who sent them:
curl -s "https://base.blockscout.com/api/v2/addresses/<SINK>/token-transfers" | \
  python3 -c "import json,sys; [print(t['token']['symbol'], t['total']['value'], t['from']['hash'][:12], t['timestamp'][:16]) for t in json.load(sys.stdin)['items']]"
```

Cross-check: victim addresses are unique EOAs (not vanity-paired), and the
drain tx's final destination matches a known operator cluster.
