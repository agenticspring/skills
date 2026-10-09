# CCTP V2 All Supported Chains (2026-07-07)

Source: developers.circle.com + Iris API verification

## Mainnet EVM Chains (24)

| Chain | Domain | Contract Set | Notes |
|-------|--------|--------------|-------|
| Ethereum | 0 | Standard | |
| Avalanche | 1 | Standard | Instant finality |
| OP Mainnet | 2 | Standard | |
| Arbitrum | 3 | Standard | |
| Base | 6 | Standard | |
| Polygon PoS | 7 | Standard | Instant finality |
| Unichain | 10 | Standard | |
| Linea | 11 | Standard | |
| Codex | 12 | Standard | |
| Sonic | 13 | Standard | Instant finality |
| World Chain | 14 | Standard | |
| Monad | 15 | Standard | NEW |
| Sei | 16 | Standard | Instant finality |
| XDC | 18 | Standard | Instant finality |
| HyperEVM | 19 | Standard | Instant finality |
| Ink | 21 | Standard | |
| Plume | 22 | Standard | |
| ARC | 26 | Standard | Circle own chain |
| EDGE | 28 | DIFFERENT | Unique addresses |
| Injective | 29 | Standard | NEW |
| Morph | 30 | Standard | NEW |
| Pharos | 31 | Standard | NEW |
| Cronos | 32 | Standard | NEW |

## Standard Contract Addresses (All chains except EDGE)

| Contract | Address |
|----------|---------|
| TokenMessengerV2 | 0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d |
| MessageTransmitterV2 | 0x81D40F21F12A8F0E3252Bccb954D722d4c464B64 |
| TokenMinterV2 | 0xfd78EE919681417d192449715b2594ab58f5D002 |
| MessageV2 | 0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78 |

## EDGE (Domain 28) - DIFFERENT Addresses

| Contract | Address |
|----------|---------|
| TokenMessengerV2 | 0x98706A006bc632Df31CAdFCBD43F38887ce2ca5c |
| MessageTransmitterV2 | 0x5b61381Fc9e58E70EfC13a4A97516997019198ee |
| TokenMinterV2 | 0x338Dfd607855BeEc17f33e539Ac2479853cC8384 |
| MessageV2 | 0x88ba38dbB2117879E500c11A0772e2B84Be000B3 |

## Testnet Contract Addresses (All testnets)

| Contract | Address |
|----------|---------|
| TokenMessengerV2 | 0x8FE6B999Dc680CcFDD5Bf7EB0974218be2542DAA |
| MessageTransmitterV2 | 0xE737e5cEBEEBa77EFE34D4aa090756590b1CE275 |
| TokenMinterV2 | 0xb43db544E2c27092c107639Ad201b3dEfAbcF192 |

## Domain IDs NOT Used

Domains 4, 5, 8, 9, 17, 20, 23-25, 27 are skipped.

## Non-EVM Chains

Solana, Stellar, Starknet have separate contract formats (not covered here).