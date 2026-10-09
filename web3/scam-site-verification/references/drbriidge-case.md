# Case: drbriidge.co "DR Bridge" — fake CCTP bridge (2026-08)

Full walkthrough of a scam-site investigation that produced this skill.

## Site facts

- Domain: `drbriidge.co` ("DR Bridge — Native USDC CCTP Bridge" title)
- Hosting: Vercel (NS vercel-dns.com, IP 216.198.79.65 → AWS/Amazon)
- Fresh domain: registered ~1 day before investigation (GoDaddy registrant)
- JS bundle: `/assets/index-MJ0_bxQI.js` (~502 KB)

## Bundle findings

```js
// chain config extracted:
Arc: { chainIdNum: 26,                // WRONG — Arc chainId is 5042 (0x13b2)
       rpcUrl: "https://arc-mainnet-rpc.baracat.meme",   // non-official .meme RPC
       usdcAddress: "0x0000...0000",  // ZERO — real Arc USDC is a predeploy
       cctpMessenger: "0x0000...0000" // ZERO — real messenger exists
     }
// sink:
useState(e.recipientAddress || `0xd1f3d439abc6b89b05d9d15b8caf7049a46a4e5f`)
// footer: "Powered by" → https://x.com/DyorSwapdex  (clone of DYORSwap frontend)
```

Known-good addresses found alongside (do NOT flag): Base USDC
`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`, ETH USDC `0xA0b8...`,
Arbitrum USDC `0xaf88...`, EntryPoint `0x00000000000C2E...`, ENS Universal
Resolver `0xeEeEEEeE14D718293...`, secp256k1 constants (`0xffff...fc2f`,
`0xffff...eafcec`).

## Sink wallet trace

Sink = `0xd1F3D439aBC6B89B05d9d15b8caF7049a46A4e5f` (default recipientAddress).

Blockscout Base token-transfers (all IN, 9 records, no OUT):

| USDC | sender (uniqueness) | time |
|------|--------------------|------|
| 0.10 | 0x8a62...e003 | 08-08 01:07 |
| 5.00 | 0x757887...91651f / 0x7578D2...1652c | 07-08 23:18-25 |
| 48.00 | 0xFc928A...697ab / 0xFC929d...7697AB | 07-08 18:57-58 |
| 1.00 | 0x9015E7...b0b / 0x9015cf...95bb | 07-08 18:01-03 |
| ARB | 3370 (t.me/arb_pool token) | 07-08 18:43 |

**Vanity-pair group**: `0xFc928A5E...697ab` + `0xFC929dF2...7697AB`,
`0x9015E715...` + `0x9015cf...` — address pairs sharing a suffix are the same
operator testing their own frontend. Result: **0 unique unrelated victims**,
$54.20 total was all operator self-testing.

## Drain tx (active 09-08 00:45)

Tx `0xc93480bced7e2a00908974ed89b7f81d2a6d2e81cc383f09c816ba6b3e985f5f`:
`transferAndMulticall` on Base:
- tokens: [Base USDC]
- amounts: [54200000] (= $54.20)
- approve to MetaAggregationRouterV2 `0x6131B5fa...`
- swap via RelayRouterV3 `0xb92fe9...` → destination
  **`0xF70dA97811cb96ACdF810712Aa562db8fA3dBEF`**

That destination is a known bot-sybil operator (652K+ tx vanity cluster from
prior pools.trade work), confirming the drain flows into a farm cluster.

## Verdict

Fake CCTP bridge clone. Zero-address chain config + sink + drain armed + fresh
domain. No real victims yet at analysis time, but the drainer was ready.