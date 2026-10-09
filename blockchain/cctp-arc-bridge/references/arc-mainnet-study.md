# Arc Mainnet — Evidence and Verification Matrix

## Scope
Condensed evidence from the Arc Mainnet study. This reference distinguishes official documentation, public discovery, and live read-only observations.

## Official sources

- Arc Docs RPC reference: `https://docs.arc.io/arc/references/rpc-endpoints`
  - The page currently documents Arc Testnet (`5042002`, `https://rpc.testnet.arc.network`).
  - It states that mainnet endpoints and parameters are published separately when available.
- Arc Docs LLM index: `https://docs.arc.io/llms.txt`
  - Arc is an EVM-compatible L1.
  - USDC is the native gas token.
  - Arc provides sub-second deterministic finality.
- Arc execution-layer docs/repository:
  - Execution layer is Reth-based.
  - Consensus implementation is Malachite BFT-based.
- Circle CCTP docs: `https://developers.circle.com/cctp`
  - Arc is supported by CCTP; use CCTP domain 26.
  - The checked CCTP pages do not directly publish a mainnet RPC URL.

## Chain identity

```text
EVM Chain ID: 5042 (0x13b2)
CCTP Domain: 26
Gas currency: USDC
Finality: deterministic, sub-second
```

## Read-only verification matrix

| Endpoint | `eth_chainId` | `net_version` | `web3_clientVersion` | Classification |
|---|---:|---:|---|---|
| `https://rpc.blockdaemon.mainnet.arc.io` | `0x13b2` | `5042` | `reth/v1.11.3-5791a7c/x86_64-unknown-linux-gnu` | Public provider-branded endpoint; liveness verified; official endorsement not independently proven |
| `https://5042.rpc.thirdweb.com` | `0x13b2` | `5042` | `thirdweb/1.0` | Public provider endpoint; liveness verified |
| `https://real-pump-soon-trust-me-bro-again.poptyedev.com/` | `0x13b2` | `5042` | `reth/v1.11.3-5791a7c/x86_64-unknown-linux-gnu` | Public third-party hostname; liveness verified; ownership and authorization unconfirmed |

Additional read-only methods used: `eth_blockNumber`, `eth_gasPrice`, `eth_getBlockByNumber`, `eth_getCode`, `eth_getBalance`.

## Discovery discipline

A candidate is independently discovered only when its provenance comes from a public source that was not the candidate itself or a pre-existing seed. Valid passive sources include:

```text
official docs / public JS / GitHub / chain registries / CT logs / provider indexes / public search
```

A screenshot or known seed may be used as a clue or for verification, but must not be reported as discovery-from-zero. Always report:

```text
source → candidate → read-only verification → confidence/limitations
```

## Safety boundary

No authenticated calls, credential use, port scanning, brute-force subdomain guessing, or transaction broadcasts are part of this workflow. A live JSON-RPC response proves reachability and chain identity only; it does not establish ownership, privacy, or permission to submit transactions.
