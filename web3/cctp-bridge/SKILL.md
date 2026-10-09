---
name: cctp-bridge
description: Circle CCTP V2 cross-chain USDC bridge operations. Bridge native USDC between EVM chains using burn-and-mint mechanism. Includes ARC Mainnet (Circle's chain) integration.
version: 1.1.0
author: spring
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [CCTP, Circle, USDC, Bridge, Cross-Chain, ARC, EVM, DeFi]
    related_skills: [web3-farmer-bot]
---

# CCTP V2 — Cross-Chain Transfer Protocol

## Overview

CCTP (Cross-Chain Transfer Protocol) is Circle's permissionless onchain utility for transferring **native USDC** across blockchains. Burns USDC on source chain, mints on destination chain — 1:1 ratio, no liquidity pools, no wrapped tokens.

```
Source Chain                    Destination Chain
    │                               │
    ├─ Burn USDC ──────────────────►│
    │                               ├─ Mint USDC
    │                               │
    └─ Attestation (Circle Iris) ──►│
```

## Supported Chains (24 Mainnet + 17 Testnet)

### Mainnet

| Chain | Domain | Instant Finality | Fast Transfer |
|-------|--------|------------------|---------------|
| Ethereum | 0 | ❌ | ✅ |
| Avalanche | 1 | ✅ | N/A |
| OP Mainnet | 2 | ❌ | ✅ |
| Arbitrum | 3 | ❌ | ✅ |
| Base | 6 | ❌ | ✅ |
| Polygon PoS | 7 | ✅ | N/A |
| Unichain | 10 | ❌ | ✅ |
| Linea | 11 | ❌ | ✅ |
| Codex | 12 | ❌ | ✅ |
| Sonic | 13 | ✅ | N/A |
| World Chain | 14 | ❌ | ✅ |
| Monad | 15 | ❌ | ✅ |
| Sei | 16 | ✅ | N/A |
| XDC | 18 | ✅ | N/A |
| HyperEVM | 19 | ✅ | N/A |
| Ink | 21 | ❌ | ✅ |
| Plume | 22 | ❌ | ✅ |
| Arc (domain 26) | **26** | ⚠️ docs conflict | N/A — **re-verify live** |
| EDGE | 28 | ❌ | ✅ |
| Injective | 29 | ✅ | N/A |
| Morph | 30 | ❌ | ✅ |
| Pharos | 31 | ❌ | ✅ |
| Cronos | 32 | ❌ | ✅ |

### Testnet

Ethereum Sepolia, Avalanche Fuji, OP Sepolia, Arbitrum Sepolia, Base Sepolia, Polygon PoS Amoy, Linea Sepolia, **Arc Testnet**, Unichain Sepolia, Codex Testnet, Sonic Testnet, World Chain Sepolia, Sei Testnet, XDC Apothem, HyperEVM Testnet, Ink Testnet, Plume Testnet

## ARC / Domain-26 Status Guard (2026-07-31)

**Do not assume that domain `26` is a production Arc destination solely from this skill or an app-router label.** Circle’s currently published CCTP supported-chain page labels domain `26` as **Arc testnet** and explicitly says Arc is the exception where CCTP supports Arc testnet only. This conflicts with older local Arc-mainnet notes.

Before any mainnet burn whose router maps to domain `26`, require all of:

```text
current Circle documentation and Iris route confirmation
→ non-pending Iris attestation/message
→ independently verifiable destination receipt (`receiveMessage` or forwarding)
→ observed recipient USDC balance increase on the expected destination network
```

A successful Base burn proves only the source-side burn. It does **not** prove delivery to an intended Arc mainnet account. Treat prior “ARC Mainnet domain 26” statements below as historical notes pending re-verification.

## ARC Mainnet Configuration

Historical local notes follow; do not treat them as current Circle route authority without the status guard above.

| Detail | Value |
|--------|-------|
| **Chain Name** | ARC Mainnet |
| **Chain ID** | 5042 |
| **Domain** | 26 |
| **Instant Finality** | ✅ Yes |
| **RPC** | `https://real-pump-soon-trust-me-bro-again.poptyedev.com/` |
| **Explorer** | `https://arc-mainnet.cloud.blockscout.com/` (may be offline) |

### Contract Addresses (Verified on-chain 2026-07-07)

| Contract | Address | Type |
|----------|---------|------|
| **TokenMessengerV2** | `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` | TransparentUpgradeableProxy |
| **MessageTransmitterV2** | `0x81D40F21F12A8F0E3252Bccb954D722d4c464B64` | TransparentUpgradeableProxy |
| **TokenMinterV2** | `0xfd78EE919681417d192449715b2594ab58f5D002` | Proxy |
| **MessageV2** | `0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78` | Deployed contract |
| **USDC** | `0x3600000000000000000000000000000000000000` | ERC20 (1,798 bytes) |

**Note**: Contract addresses are the same across ALL CCTP V2 mainnet chains (deterministic deployment). USDC address varies per chain.

### Verify Contracts Exist

Run `scripts/verify-arc-contracts.sh` for a full check, or use this Python snippet for quick existence checks:

```python
import requests
rpc = "https://real-pump-soon-trust-me-bro-again.poptyedev.com/"
contracts = {
    "TokenMessengerV2": "0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d",
    "MessageTransmitterV2": "0x81D40F21F12A8F0E3252Bccb954D722d4c464B64",
    "USDC": "0x3600000000000000000000000000000000000000",
}
for name, addr in contracts.items():
    r = requests.post(rpc, json={"jsonrpc":"2.0","method":"eth_getCode","params":[addr,"latest"],"id":1})
    code = r.json().get('result', '')
    print(f"{name}: {'EXISTS' if len(code) > 10 else 'NOT FOUND'} ({len(code)} bytes)")
```

## Transfer Flow (Step by Step)

### Step 1: Approve USDC for TokenMessenger

```solidity
// On source chain
USDC.approve(TokenMessengerV2, amount);
```

### Step 2: Call depositForBurn

```solidity
TokenMessengerV2.depositForBurn(
    amount,              // USDC amount (in smallest unit)
    destinationDomain,   // 26 for ARC
    mintRecipient,       // bytes32 padded address on ARC
    burnToken,           // USDC address on source chain
    destinationCaller,   // bytes32(0) for permissionless
    maxFee,              // max fee for fast transfer (0 for standard)
    minFinalityThreshold // 0 for standard, 1000 for fast
);
```

### Step 3: Poll for Attestation

```python
# Circle Iris API
import requests, time

def poll_attestation(source_domain, tx_hash, timeout=600):
    url = f"https://iris-api.circle.com/v2/messages/{source_domain}"
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(url, params={"transactionHash": tx_hash})
        data = r.json()
        if data.get("messages"):
            msg = data["messages"][0]
            if msg.get("attestation") and msg["attestation"] != "PENDING":
                return msg
        time.sleep(5)
    return None
```

### Step 4: Receive Message on Destination

```solidity
// On ARC (destination chain)
MessageTransmitterV2.receiveMessage(message, attestation);
```

## Quickstart Options

Circle provides quickstart guides:
- **Ethereum → ARC**: `/cctp/quickstarts/transfer-usdc-ethereum-to-arc`
- **Solana → ARC**: `/cctp/quickstarts/transfer-usdc-solana-to-arc`
- **Stellar ↔ ARC**: `/cctp/quickstarts/transfer-usdc-stellar-arc`

## CCTP Go SDK

```bash
git clone https://github.com/circlefin/cctp-go
cd cctp-go
go mod download
go build -o bin/cctp ./cmd/cli

# Transfer
./bin/cctp transfer --source ethereum --dest arc --amount 100 --recipient 0x... --type fast

# Testnet
./bin/cctp transfer --testnet

# Resume existing transfer
./bin/cctp resume 0x...  # burn tx hash
```

### SDK Chain Constants

```go
import "github.com/circlefin/cctp-go"

// Mainnet
cctp.Ethereum  // Domain 0
cctp.Avalanche // Domain 1
cctp.OPMainnet // Domain 2
cctp.Arbitrum  // Domain 3
cctp.Base      // Domain 6
cctp.PolygonPoS // Domain 7
// ... etc

// Testnet
cctp.ArcTestnet // Domain 26, ChainID 5042002
```

### Custom RPC Override

```go
chains := cctp.GetChains(false)
customRPCs := map[string]string{
    cctp.Ethereum: "https://eth-mainnet.g.alchemy.com/v2/KEY",
}
chains = cctp.ApplyRPCOverrides(chains, customRPCs)
```

## Iris Attestation API

**Base URL**: `https://iris-api.circle.com`

### Get Message
```
GET /v2/messages/{sourceDomain}?transactionHash={txHash}
```

**Response**:
```json
{
  "messages": [{
    "attestation": "0x...",  // "PENDING" if not ready
    "message": "0x...",
    "eventNonce": "123",
    "cctpVersion": 2,
    "sourceDomain": 0,
    "destinationDomain": 26
  }]
}
```

### Get Transfer Fees
```
GET /v2/fees?source={sourceDomain}&destination={destDomain}
```

## Transfer Types

| Type | Speed | Fee | Use Case |
|------|-------|-----|----------|
| **Standard** | 13-19 min (or ~8s for instant finality chains) | Free | Cost-sensitive |
| **Fast** | 8-20 sec | 1-14 bps | Time-sensitive |
| **Forwarding** | 8-20 sec (Fast) + gasless mint | Forward fee + protocol fee | Automated/gasless |

**Note**: Instant finality chains (Avalanche, Polygon, Sei, Sonic, XDC, HyperEVM, ARC) always use Standard at ~8s — Fast Transfer not needed.

## Self-Operated Destination Relay (No Forwarding Fee)

Use this mode when the operator controls a funded destination-chain relayer and wants to avoid third-party service and forwarding fees.

### Flow

```text
source USDC → standard depositForBurn (maxFee = 0, no hook)
→ Circle Iris attestation
→ operator relayer submits receiveMessage on destination
→ recipient receives native USDC
```

- Use `depositForBurn`, **not** `depositForBurnWithHook`.
- Set `maxFee = 0`; source burn amount equals intended destination amount.
- The relayer may differ from the recipient because `receiveMessage` is permissionless.
- The relayer wallet must hold destination gas. On ARC, native USDC pays gas, so retain a native-USDC reserve before enabling relay.
- Persist the burn before polling Iris. Mark it completed only after `receiveMessage` succeeds; keep it pending on unavailable attestation, disabled relay, insufficient gas, or RPC failure for safe retry.
- Keep relay keys encrypted at rest. When selected through an admin UI, verify that the configured address belongs to an authorized admin before decrypting it.

### Do not mix modes

Do not gate this route on the Forwarding-fee API or use forwarding-completion detection. Standard relay completion is: Iris attestation ready → successful destination `receiveMessage` transaction (or Iris reports already minted).

## Forwarding Service (Gasless Mint)

Circle's Forwarding Service pays for gas on the **destination chain**. Users only need gas on the source chain.

### How It Works

Instead of calling `depositForBurn`, call `depositForBurnWithHook` with special `hookData`:

```solidity
TokenMessengerV2.depositForBurnWithHook(
    amount,                    // USDC amount
    destinationDomain,         // 26 for ARC
    mintRecipient,             // bytes32 padded address
    burnToken,                 // USDC address
    destinationCaller,         // bytes32(0) for permissionless
    maxFee,                    // max fee
    minFinalityThreshold,      // 1000 (fast) or 2000 (standard)
    hookData                   // Forwarding Magic Bytes (see below)
);
```

### Forwarding Magic Bytes

```
0x636374702d666f72776172640000000000000000000000000000000000000000
```

This is `"cctp-forward"` padded to 32 bytes. Tells Circle to auto-mint on destination.

```python
FORWARDING_MAGIC = bytes.fromhex(
    "636374702d666f7277617264"  # "cctp-forward"
    "0000000000000000000000000000000000000000"  # padding
)
# Length: 32 bytes exactly
```

### Forwarding Fee API

```
GET https://iris-api.circle.com/v2/burn/USDC/fees/{sourceDomain}/{destDomain}?forward=true
```

**Response** (per finality threshold):
```json
[{
  "finalityThreshold": 1000,
  "minimumFee": 0.25,        // basis points
  "forwardFee": {
    "low": 17875,
    "med": 18625,             // use this for maxFee
    "high": 19375
  }
}]
```

### Verified Forwarding Fees to ARC (Domain 26)

| Source | forwardFee (med) | minFee (bps) | Finality |
|--------|-----------------|--------------|----------|
| Ethereum (0) | 18625 | 0.25 | 1000 |
| Base (6) | 18625 | 0.325 | 1000 |
| Arbitrum (3) | 16550 | 0.325 | 1000 |
| OP Mainnet (2) | 16557 | 0.325 | 1000 |
| Polygon (7) | 16557 | 0 | 1000 |
| Avalanche (1) | 16557 | 0 | 1000 |

### Fee Calculation

```python
import math

def compute_fee_quote(transfer_amount, option, buffer_pct=25):
    forward_fee = round(option['forwardFee']['med'])
    bps_scaled = round(option['minimumFee'] * 100)
    protocol_fee = (transfer_amount * bps_scaled) // 1_000_000
    base_fee = forward_fee + protocol_fee
    buffer = (base_fee * round(buffer_pct)) // 100
    max_fee = base_fee + buffer
    return {
        'forwardFee': forward_fee,
        'protocolFee': protocol_fee,
        'maxFee': max_fee,
        'totalAmount': transfer_amount + max_fee,
    }
```

### Checking If Route Is Live

```python
def is_route_live(source_domain, dest_domain):
    url = f"https://iris-api.circle.com/v2/burn/USDC/fees/{source_domain}/{dest_domain}?forward=true"
    r = requests.get(url, timeout=10)
    return r.status_code == 200 and len(r.json()) > 0
```

### Key Insight: Forwarding vs Manual

| Aspect | Forwarding | Manual (receiveMessage) |
|--------|-----------|------------------------|
| Gas on dest | Circle pays | User pays |
| Extra call | None | receiveMessage() |
| Speed | Same | Same |
| Complexity | Lower | Higher |
| Reliability | Circle handles | User must track attestation |

## Pitfalls

1. **Domain 26 is not free authority for Arc mainnet** — Circle docs have labeled domain 26 as Arc testnet. Source burn to domain 26 only proves the burn; prove delivery with Iris + destination receipt + balance delta. See ARC / Domain-26 Status Guard.
2. **App router `maxFeeBps` is not a CCTP domain** — values like `200` on `bridge(amount, recipient, maxFeeBps)` are fee bounds (2%), not destination IDs. Decode `MessageSent` header for the real domain.
3. **“Sign once / relayer mints” ≠ claimable** — source success can coexist with Iris `pending_confirmations` and `message=null`. No claim/relay until attestation is non-pending (or destination already minted). See `references/app-router-auto-relay-claimability.md`.
4. **Approve + bridge is still two Base signatures** — UI copy “sign once” may omit the separate USDC approve.
5. **Contract addresses are same** — All CCTP V2 mainnet chains use identical TokenMessengerV2 and MessageTransmitterV2 addresses (EXCEPT EDGE)
6. **USDC address varies per chain** — ARC uses `0x3600000000000000000000000000000000000000`
7. **Domain ≠ Chain ID** — Domain is Circle's identifier; Chain ID is EVM standard (Arc often 5042)
8. **mintRecipient must be bytes32** — Pad address with leading zeros: `0x000000000000000000000000{address}`
9. **Iris API polling** — Attestation can take 8-20 minutes for standard transfers, sometimes longer under pending_confirmations
10. **Fast Transfer not available from instant finality chains** — Use Standard instead
11. **Custom RPC** — ARC uses non-standard RPCs; explorers may be delayed/offline
12. **No USDC on chain = can't bridge** — Need USDC on source chain first
13. **Testnet vs Mainnet** — ARC Testnet (ChainID 5042002) ≠ ARC Mainnet (ChainID 5042)
11. **Go 1.25 compatibility** — cctp-go requires Go 1.25.2 but has build issues. Use `go mod tidy` + Go 1.24.x as workaround: `sed -i 's/go 1.25.2/go 1.24/' go.mod && go mod tidy && go build`
12. **Go internal package restriction** — `cctp-go/internal/wallet` can't be imported from outside the module. Use the CLI or Python script instead of custom Go code.
13. **CCTP CLI needs TTY** — The interactive TUI requires a terminal. Use Python web3.py script for non-interactive/automated bridging.
14. **ARC CCTP V2 contracts lack standard view functions** — The implementations do NOT contain `localMessageTransmitter()`, `localDomain()`, `messageBodyVersion()`, or `tokenMinter()` selectors. These calls revert. Only core write functions (`depositForBurn`, `depositForBurnWithHook`, `receiveMessage`) and proxy management (`owner`, `implementation`, `upgradeTo`) work. Verified by extracting function selectors from the 16KB implementation bytecodes. The contracts are functional for bridging — just can't query config via standard CCTP view ABI.
15. **ARC CCTP contracts are proxies** — TokenMessengerV2 impl: `0x1ccafdffbc1b7b5c499c97322f961b7d929a41b4`, MessageTransmitterV2 impl: `0xdb9fead96ee05783db38c82dc4689ceeb6712df0`. MessageTransmitterV2 has Pausable functionality (pause/unpause with pauser role). MessageTransmitterV2 `version()` returns 1 (call via selector `0x54fd4d50`, not `0x0af50ea2`).
16. **ARC USDC totalSupply is small** — As of 2026-07-07, only ~46,557 USDC exists on ARC. TokenMessengerV2 holds 0 USDC (no active bridge deposits). Chain is live but low activity.
17. **EDGE chain has DIFFERENT contracts** — Domain 28 (EDGE) uses unique addresses, NOT the deterministic ones: TokenMessengerV2=`0x98706A006bc632Df31CAdFCBD43F38887ce2ca5c`, MessageTransmitterV2=`0x5b61381Fc9e58E70EfC13a4A97516997019198ee`, TokenMinterV2=`0x338Dfd607855BeEc17f33e539Ac2479853cC8384`, MessageV2=`0x88ba38dbB2117879E500c11A0772e2B84Be000B3`.
18. **Additional chains not in Go SDK** — Monad (15), EDGE (28), Injective (29), Morph (30), Pharos (31), Cronos (32) are supported by CCTP V2 but not yet in the Go SDK.

## References

- Circle Docs: https://developers.circle.com/cctp
- CCTP Go SDK: https://github.com/circlefin/cctp-go
- Iris API: https://iris-api.circle.com
- Supported Chains: https://developers.circle.com/cctp/concepts/supported-chains-and-domains
- **Skill-local**: `references/arc-mainnet-onchain-verification.md` — Detailed on-chain verification of ARC contracts (selectors, bytecode sizes, proxy impls, owner addresses)
- **Skill-local**: `references/app-router-auto-relay-claimability.md` — UI auto-relay vs Iris claimability; Base→Arc no browser claim while attestation pending
- **Skill-local**: `scripts/verify-arc-contracts.sh` — Reusable bash script to verify ARC contracts via raw JSON-RPC calls
