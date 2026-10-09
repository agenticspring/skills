---
name: telegram-nft-trading-bot
description: Build Telegram multi-wallet NFT sniper bots with Maestro UX.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Telegram, Bot, NFT, Sniper, Maestro, Multi-wallet]
---

# Telegram NFT Trading Bot — Build & Audit

Builds multi-wallet NFT sniper/minting bots on Telegram with Maestro/Trojan-style UX.
Covers inline keyboard navigation, eligibility scanning, scheduled minting,
batch sweeps, and EIP-1559 gas optimization. Requires grammy (or similar),
ethers.js, Foundry (`cast`), and an OpenSea API key.

## When to Use

- "Build a Telegram NFT bot like Maestro"
- "Audit or fix my NFT sniper bot"
- "Add wallet management / portfolio / PNL to my bot"
- "Why is my Telegram bot crashing on callback?"

## Architecture Pattern

```
Telegram Bot (grammy)
  → Handlers (menu nav, NFT paste, callbacks)
    → Eligibility Resolver (on-chain phase check per wallet)
      → Mint Scheduler (Set & Forget, polls until phase active)
        → Broadcast Executor (sign + broadcast via ethers)
          → SQLite (users, campaigns, PNL ledger, journal)
```

## Quick Reference

```text
# Key files in a working bot repo
handlers.ts       # menu nav, NFT lookup, callback routing
menu.ts           # inline keyboard builder + help text
nft-lookup.ts     # parse CA/URL → fetch metadata via OpenSea API
mint-scheduler.ts # poll on-chain state, fire when phase active
seadrop-eligibility.ts # read getPublicDrop/merkleRoot/signedParams per wallet
eip1559-gas.ts    # economy/standard/fast/sniper strategies
broadcast.ts      # sign + broadcast via ethers Wallet.sendTransaction()
telegram-wallet-manager.ts # generate/import/export/delete wallets
```

## Procedure

1. **Parse input** — accept bare CA, OpenSea URL, or collection slug. Auto-detect chain by trying multiple chains against the API.

2. **Render collection card** with progress bar, mint phases + countdown, floor price, and eligibility summary.

3. **Eligibility scan** — read `getPublicDrop()`, `getAllowListMerkleRoot()`, `getSignedMintValidationParams()` from SeaDrop contract; check each wallet's `getMintStats()` against phase quota.

4. **Wallet selector** — show eligible wallets as buttons; each triggers intent creation with idempotency key.

5. **Scheduled mint** — register schedule, poll slow (30s) then fast (3s inside window), fire callback when phase activates.

6. **Batch sweep** — group per-wallet transfer plans into one batch with single confirm button; executor iterates sequentially (nonce-safe).

## Pitfalls

- Always set `parse_mode: 'Markdown'` in `editMessageText` or bold/code formatting won't render.
- MUST add `bot.catch(err => ...)` — without it, an expired callback query crashes the entire bot process.
- Default chain should NOT be ethereum for non-mainnet deployments; use auto-detect by trying chains in order.
- `cast call` cannot simulate `--value`; payment errors only surface on `cast send`.
- OpenSea `/chain/{chain}/account/{address}/nfts` returns empty array (not error) for wrong chain.
- Inline keyboard buttons max 64 bytes callback_data; use HMAC-signed tokens bound to actor/chat/intent/expiry.
- S3 presigned POST uploads fail via curl subprocess (arg length); use Python requests.
- When using heredocs to write TypeScript files with template literals, backticks get eaten by shell escaping — write files via `write_file` tool instead.

### Telegram UX Pitfalls (from live audit)

- Every inline keyboard button MUST have a corresponding handler branch AND be listed in the allowed-actions array. Missing either → clicking silently returns to main menu with no feedback.
- Menu buttons showing only "Read-only data view" + returning to /start = stub handlers. Each button needs its own content section with real data or actionable prompts.
- Wallet generate/import/delete: use a pending-action state machine (`pendingActions` Map keyed by actor:chat) to track what the bot expects next. After Import prompt, listen for next text message as PK.
- Wallet list should read from the keystore/managed wallet store, NOT a stale manifest file. Manifest is public addresses only; keystore has full wallet objects.
- Per-wallet delete buttons need dynamic callback_data (`wallet_delete_${index}`); add prefix check to the navActions guard since it won't match exact string.
- PNL card rendering requires `sharp` for PNG generation; send via grammy `InputFile(buffer, 'filename.png')`.
- Config mode enum values are strict (`'read_only' | 'trading' | 'fcfs'`) — using `'live'` causes config validation failure at startup.
- Production safety gates can be bypassed by replacing `throw new Error(...)` with `console.warn(...)` when testing UX before wiring real signers.

## Verification

```bash
# Bot is alive
ps aux | grep production-bot | grep -v grep

# Telegram API reachable
curl -s "https://api.telegram.org/bot<TOKEN>/getMe" | python3 -c "import json,sys; print(json.load(sys.stdin).get('ok'))"

# Tests green
corepack pnpm test 2>&1 | grep 'Tests.*passed'
```

## References

- `references/seadrop-robinhood.md` — SeaDrop v1 on Robinhood Chain: deploy flow, signed voucher allowlist, EIP712 domain for signing vouchers, gas costs. Load when working with SeaDrop or RH chain specifically.
