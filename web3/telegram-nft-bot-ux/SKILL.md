---
name: telegram-nft-bot-ux
description: Build Maestro-style Telegram NFT bot UX with real content.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Telegram, NFT, Bot, UX, Maestro]
---

# Telegram NFT Bot UX (Maestro/Trojan Style)

Patterns for building responsive Telegram NFT trading bots that feel like
Maestro/Trojan meme coin bots. Key principle: every button shows REAL data,
never placeholder text.

## Core Rules

1. **No dead buttons** — if a button exists, it must show actual data or perform a real action.
2. **Auto-detect chain** — probe multiple chains via eth_getCode.
3. **Markdown formatting** — always use `parse_mode: 'Markdown'` in editMessageText.
4. **Error handler mandatory** — add `bot.catch()` to prevent crash on expired callbacks.
5. **Pending action state machine** — track what bot waits for using a Map keyed by `actorId:chatId`.

## Button Layout Pattern

```
💰 Wallets | 📊 Portfolio
📈 PNL History | ⚙️ Settings
🔄 Refresh
```

Each opens a sub-view with its own keyboard + back button.

## NFT Card Layout

Show name, chain, supply progress bar, floor price, mint phases with countdown, and eligible wallet count. Use emoji indicators (🟢 LIVE, ⏳ countdown, 🔴 sold out).

## Wallet Management Flow

- List from keystore (not stale manifest)
- Per-wallet delete buttons (3 per row)
- Generate → creates wallet, shows address immediately
- Import → set pending action, wait for user PK text
- Export → show addresses from keystore

## Settings Submenu

| Setting | Options |
|---------|---------|
| Mode | Read Only ↔ LIVE |
| Gas Strategy | Economy / Standard / Fast / Sniper |
| Slippage | 0.5% / 1% / 2% / 5% |

## Common Pitfalls

- Without `parse_mode`, markdown renders as raw asterisks
- Callback tokens expire ~90s; handle gracefully with error handler
- S3 uploads fail via curl subprocess; use Python requests
- OpenSea drops list may lag; verify on-chain instead

## Verification

Click each button and confirm unique relevant content appears.
