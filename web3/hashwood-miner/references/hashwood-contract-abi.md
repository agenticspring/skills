# Hashwood Contract ABI & Function Selectors

## Verified Function Selectors

| Function | Signature | Selector |
|----------|-----------|----------|
| challengeNumber | `challengeNumber()` | `0x8ae0368b` |
| miningTarget | `miningTarget()` | `0x8a769d35` |
| MINT_PRICE | `MINT_PRICE()` | `0x745e43a5` |
| checkMintSolution | `checkMintSolution(uint256,address)` | `0x9d7a7cc6` |
| mint | `mint(uint256,bytes32)` | `0x1801fbe5` |
| balanceOf | `balanceOf(address)` | `0x70a08231` |
| totalSupply | `totalSupply()` | `0x18160ddd` |

## Storage Slots (verified via eth_getStorageAt)

- challengeNumber → slot 0x0
- miningTarget → slot 0x1

## RPC Architecture & Latency Breakdown

The public RPC endpoint (`rpc.mainnet.chain.robinhood.com`) routes through:
```
VPS → Cloudflare Edge → Envoy (Istio) → Offchain Labs Sequencer
```

DNS CNAME chain: `rpc.mainnet.chain.robinhood.com` → `customer-origin.offchainlabs.com`

**Latency breakdown (measured via Server-Timing header):**

| Component | Latency | Notes |
|-----------|---------|-------|
| VPS → Cloudflare Edge | 1.2ms | ICMP ping. Very low — VPS in France, edge in AMS (Amsterdam) |
| Cloudflare Edge processing | 4ms | cfEdge;dur=4 from header |
| Cloudflare → Origin round-trip | 102ms | cfOrigin;dur=102 from header. ~50ms network + ~52ms server processing |
| **Total per eth_call** | **~110-200ms** | Lower bound with persistent TCP conn; upper bound with new TLS each time |

**Key finding:** Even a Cloudflare Worker would NOT help — the bottleneck is the **origin server processing time** (52ms + 50ms network), not the VPS→Cloudflare leg. Without a local node, <100ms RPC latency is physically impossible.

## WebSocket / Alternate Endpoints

All tested and confirmed UNAVAILABLE:

| Endpoint | Result |
|----------|--------|
| `wss://.../ws` | 404 |
| WebSocket handshake on port 443 | 400 (rejected) |
| Direct origin IP via --connect-to | Same latency (still through Cloudflare) |
| `eth_getStorageAt` | Same latency as `eth_call` (~200ms) |
| HTTP (non-TLS, port 80) | 301 redirect to HTTPS |
| Nitro sequencer ports (9642, 9644, 8547) | Timeout — not exposed publicly |

## Effective Gas Costs

Base gas price on Robinhood Chain: ~0.1-1 gwei. | Example TX cost with 60000 gas: ~0.000000006 ETH at default price. | ⚠️ A 50x gas boost (50 gwei) makes each TX cost ~0.003 ETH — enough to drain 0.0017 ETH in 20 failed reverts.

## ABI for eth_call

### challengeNumber()
```
Input:  0x8ae0368b
Output: bytes32 (64 hex chars)
Example: cast call 0xD69be8d7c6d0e8216Dc2C151834E4150313260Cc "challengeNumber()(bytes32)"
```

### miningTarget()
```
Input:  0x8a769d35
Output: uint256
Example: cast call 0xD69be8d7c6d0e8216Dc2C151834E4150313260Cc "miningTarget()(uint256)"
```

### checkMintSolution(uint256 nonce, address miner)
```
Input:  0x9d7a7cc6 + nonce(32 bytes) + addr(32 bytes padded)
Output: bool (0x00...01 = true)
Example: cast call 0xD69be8d7c6d0e8216Dc2C151834E4150313260Cc "checkMintSolution(uint256,address)(bool)" <nonce> <address>
```

### mint(uint256 nonce, bytes32 digest)
```
Input:  0x1801fbe5 + nonce(32 bytes) + digest(32 bytes)
Value:  MINT_PRICE (0.00005 ETH = 50000000000000 wei)
Example: cast send 0xD69be8d7c6d0e8216Dc2C151834E4150313260Cc "mint(uint256,bytes32)" <nonce> <digest> --value 50000000000000
```

## Event: Mint

```solidity
event Mint(address indexed _to, uint256 amount, uint256 nonce, bytes32 challengeNumber);
```

Topics:
- topic[0]: keccak256("Mint(address,uint256,uint256,bytes32)")
- topic[1]: _to (miner address, indexed)
- topic[2]: amount

## Tokenomics

| Season | Blocks | Reward/Mint | Supply % |
|--------|--------|-------------|----------|
| 1 | 1-11000 | 1,100 HASH | ~50% |
| 2 | 11001-22000 | 550 HASH | ~25% |
| 3 | 22001-33000 | 275 HASH | ~12.5% |
| 4 | 33001-44000 | 137.5 HASH | ~6.25% |
| 5 | 44001-55000 | 68.75 HASH | ~3.125% |
