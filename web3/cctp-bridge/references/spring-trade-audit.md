# Spring Trade Bot Audit (2026-07-07)

## Repo
- **URL**: https://github.com/<HANDLE_REDACTED>/spring-trade (private)
- **Local**: `/root/spring-trade/`
- **Language**: Go
- **Binary**: `spring-trade`

## What It Does

Telegram bot for:
1. **CCTP V2 Bridge** — USDC from EVM chains → ARC (gasless via Forwarding Service)
2. **NOXA Trading** — Buy/sell tokens on ARC (Uniswap V3 fork)
3. **Multi-user** — Invite-only, encrypted wallets, per-user settings

## Audit Results

### CCTP V2 Contracts — ALL VERIFIED ✅

| Contract | Address | On-Chain |
|----------|---------|----------|
| TokenMessengerV2 | `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` | ✅ 2175 bytes |
| MessageTransmitterV2 | `0x81D40F21F12A8F0E3252Bccb954D722d4c464B64` | ✅ 2175 bytes |
| TokenMinterV2 | `0xfd78EE919681417d192449715b2594ab58f5D002` | ✅ 9295 bytes |
| MessageV2 | `0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78` | ✅ 281 bytes |
| USDC | `0x3600000000000000000000000000000000000000` | ✅ 1798 bytes |

### Source Chains — ALL VERIFIED ✅

| Chain | Domain | USDC Address |
|-------|--------|--------------|
| Ethereum | 0 | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` |
| Base | 6 | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Arbitrum | 3 | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` |
| OP Mainnet | 2 | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` |
| Polygon | 7 | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` |
| Avalanche | 1 | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` |

### NOXA Trade Contracts — ALL VERIFIED ✅

| Contract | Address | On-Chain |
|----------|---------|----------|
| LaunchFactory | `0xE7d4E64079FE467A21801B36Ccc6D9B3F66BD372` | ✅ 22811 bytes |
| LaunchLocker | `0x630957Cf4582baDa8B583B5A9476a7108cFdE0A4` | ✅ 4823 bytes |
| V3Factory | `0xf0db7b58379503491d857dB50AC9ece64c653918` | ✅ 24535 bytes |
| SwapRouter | `0x53BF6B0684Ec7eF91e1387Da3D1a1769bC5A6F77` | ✅ 24497 bytes |
| Quoter | `0x7DfD4F31be6814D2906BDE155c3e1B146EAc1468` | ✅ 8273 bytes |
| PositionManager | `0x39654A85A4C05127f5Fd6ED22CAeC077A0fB1377` | ✅ 24384 bytes |

### Live Trade Test

- NOAH/USDC pool: `0xefae3808ebce882e41801315532ec3a7f1bee7cd` (22142 bytes)
- Fee tier: 10000 (1%)
- QuoterV2.quoteExactInputSingle() returns valid quotes
- 1 NOAH = 0.000012 USDC, 1 USDC = 79,637 NOAH

### Iris API Forwarding — ALL ACTIVE ✅

All 6 source chains → ARC (domain 26) confirmed with forwarding fees.

## Fixes Applied

1. **Manual claim feature** — Added `doClaim()` function + claim buttons per pending burn
2. **Anti double-bridge removed** — Users can bridge even with pending burns
3. **Arm snipe improved** — Added 24h timeout, 3 retries, better feedback
4. **Quick chain switch** — Added chain source buttons (ETH/Base/ARB/OP/POL/AVAX) in bridge menu
5. **Module renamed** — `arcbot-go` → `spring-trade` (module, binary, DB, all imports)

## Key Architecture Decisions

- **Forwarding Service** for gasless mint (Circle pays dest gas)
- **depositForBurnWithHook** with Forwarding Magic Bytes
- **SQLite WAL** for multi-user persistence
- **AES-256-GCM** for private key encryption
- **Invite-only** access control
- **Anti-MEV**: priority fee + private RPC endpoint
