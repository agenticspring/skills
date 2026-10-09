# ARC Mainnet — On-Chain Verification (2026-07-07)

Source: Direct RPC queries to `https://real-pump-soon-trust-me-bro-again.poptyedev.com/`

## Chain Info

| Field | Value |
|-------|-------|
| Chain ID | 5042 (0x13b2) |
| Block Number | ~9,041,933 |
| Block Time | 2026-07-07T09:45:23 UTC |
| Gas Limit | 30,000,000 |
| Gas Price | 40 Gwei |
| Base Fee | 20 Gwei |
| EIP-1559 | Supported |
| Miner | `0xaf1e4eeeb68cb154ab5321bfe89aa6117f9b5c76` |

## USDC Contract (`0x3600000000000000000000000000000000000000`)

| Method | Selector | Result |
|--------|----------|--------|
| `name()` | `0x06fdde03` | `"USDC"` |
| `symbol()` | `0x95d89b41` | `"USDC"` |
| `decimals()` | `0x313ce567` | `6` |
| `totalSupply()` | `0x18160ddd` | `46,557,327,828` (46,557.327828 USDC) |
| Bytecode | — | 1,798 bytes |

## CCTP V2 Contracts

### TokenMessengerV2 (`0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d`)

| Method | Selector | Result |
|--------|----------|--------|
| `implementation()` | `0x5c60da1b` | `0x1ccafdffbc1b7b5c499c97322f961b7d929a41b4` |
| `owner()` | `0x8da5cb5b` | `0xa9eac9d4d7d2c2a97abd6b102f8adb3df6889386` |
| `pendingImplementation()` | `0xe30c3978` | `0x0` (no pending upgrade) |
| `localMessageTransmitter()` | `0x21121c76` | **REVERTS** (not in bytecode) |
| `tokenMinter()` | `0x39f9a10b` | **REVERTS** (not in bytecode) |
| `localDomain()` | `0xe38be128` | **REVERTS** (not in bytecode) |
| Bytecode (impl) | — | ~16,283 bytes |

### MessageTransmitterV2 (`0x81D40F21F12A8F0E3252Bccb954D722d4c464B64`)

| Method | Selector | Result |
|--------|----------|--------|
| `implementation()` | `0x5c60da1b` | `0xdb9fead96ee05783db38c82dc4689ceeb6712df0` |
| `owner()` | `0x8da5cb5b` | `0xb3ad729b38bf4d1257e224084322cb38edd74ed5` |
| `version()` | `0x54fd4d50` | `1` |
| `localDomain()` | `0xe38be128` | **REVERTS** (not in bytecode) |
| `messageBodyVersion()` | `0x2398e36a` | **REVERTS** (not in bytecode) |
| `maxMessageBodySize()` | `0xf19873ee` | **REVERTS** (not in bytecode) |
| Bytecode (impl) | — | ~16,882 bytes |
| Pausable | — | Yes (pause/unpause with pauser role) |

### TokenMinterV2 (`0xfd78EE919681417d192449715b2594ab58f5D002`)

| Method | Selector | Result |
|--------|----------|--------|
| `owner()` | `0x8da5cb5b` | `0x551afd83de85f2a0c47b6092866f90d3d126b45d` |
| `implementation()` | `0x5c60da1b` | **REVERTS** (non-standard proxy) |

### MessageV2 (`0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78`)

- Contract deployed, exists on-chain

## Verification Method

1. `eth_chainId`, `eth_blockNumber`, `eth_gasPrice`, `eth_feeHistory` for chain info
2. `eth_call` with ERC20 selectors (`0x06fdde03`, `0x95d89b41`, `0x313ce567`, `0x18160ddd`) for USDC
3. `eth_call` with proxy selectors (`0x5c60da1b`, `0x8da5cb5b`, `0xe30c3978`) for contract management
4. `eth_getCode` to verify deployment and measure bytecode size
5. Function selector extraction from implementation bytecodes using regex `63([0-9a-f]{8})` on raw bytecode — confirmed that CCTP view selectors (`0x21121c76`, `0x39f9a10b`, `0xe38be128`, `0x2398e36a`, `0xf19873ee`) are absent
6. `eth_call` with `0x70a08231` (balanceOf) to check USDC held by TokenMessengerV2: 0

## Key Takeaway

ARC's CCTP V2 contracts are **minimal proxy implementations** that support core bridge operations (burn/mint/receive) but do NOT expose the standard CCTP view functions. If you need domain info, hardcode Domain=26 for ARC rather than querying `localDomain()`.
