---
name: pixelmon-mint-bypass
description: Farm game-mint credits via battle engine replay.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Pixelmon, Mint, Voucher, Battle, Replay, Robinhood]
    related_skills: [nft-mint-verification, evm-wallet-set-management, web3-freemint-batch-execution]
---

# Pixelmon Mint Bypass (Battle Replay)

Auto-win a deterministic web game's boss battle offline, submit the action
transcript to get a signed EIP-712 win voucher, redeem it on-chain for mint
credits, then commit+finalize mints. Worked on pixelmon.mom (Robinhood 4663)
GenesisCapsule, 17 NFT farmed before 2400/2400 sold out. Scripts live in
`/root/projects/pixelmon-bot/` and the private repo `agenticspring/pixelmon-bot`.

Does NOT mint for free: commitMint is paid (0.0001 ETH). The bypass skips the
gameplay, not the payment.

## When to Use

- A mint is gated behind a web game/battle that awards credits or vouchers.
- The game engine ships as readable JS (`engine.mjs`) and is deterministic
  (no server-side RNG beyond a seed).
- User asks to "bypass the game" / farm credits / auto-win a battle.

## Prerequisites

- Node.js (replay the engine), Python + `cast`, `eth-account`
- `ALCHEMY_API_KEY` in `~/.hermes/.env`
- Wallet sets at `/root/.hermes/.credintial/.springwallet`

## How to Run

```bash
cd /root/projects/pixelmon-bot
python3 pixelmon_max_mint.py --wallet-set N     # battle-loop + mint to cap (6)
python3 pixelmon_mint.py --wallet-set N --mint 1
```

## Procedure

1. **Recon the game.** Fetch the site's JS: `app.js` reveals the flow
   (start session → player actions → claim). `engine.mjs` is the battle engine.
   Read `BOT_TEAM` and the player's starting `team` from app.js.
2. **Confirm determinism.** Engine uses fixed damage % tables + seeded PRNG
   (`makeRng(seed)`) — no hidden RNG. Solidity twin exists (`BattleEngine.sol`)
   so the server replays the same logic.
3. **Find a winning team.** Brute-force team + slot combos against `BOT_TEAM`
   across many seeds; pick one that wins ~100% (found: VERDANT(3)/PYRON(1)/TIDRA(2)
   all with slots [0,1], 15/15 seeds). IMPORTANT: rebuild bot units fresh per
   battle — battleSteps mutates hp/pp, a shared array gives fake wins.
4. **Start + replay + claim.** `POST /api/battle/start {wallet,team,difficulty:3,balance:'tuned'}`
   returns `sessionId` + `seed`. Replay locally with that seed, record EVERY
   action incl. `null` on `faintSwitch` phase (the API rejects transcripts
   missing them: "battle replay is incomplete"). `POST /api/battle/claim`
   returns `{voucher, signature}`.
5. **Redeem on-chain.** ABI-encode the struct properly: selector +
   struct fields (96B) + offset word (0x80) + sig length + sig padded to 32B.
   Wrong order → revert `0x`. `redeemWinVoucher` → +3 credits.
6. **Mint.** `commitMint()` payable (read `price()`) → `finalizeMint(commitId)`.
   Find commitId from the MintCommitted event (topic1), NOT from
   totalCommitted (id ≠ running count).
7. **Handle TooEarly.** `finalizeMint` in the same block reverts
   `0x085de625 TooEarly` — retry after ~1 block (3s). Loop finalizes.

## Pitfalls

- **`finalizeMint` TooEarly** — same-block call reverts; always retry with delay.
- **`commitMint` SoldOut** — `totalCommitted == TOTAL_SUPPLY_CAP` stops minting;
  check before spending on battles.
- **API rejects transcripts** without `null` on faintSwitch phases.
- **Shared bot array in brute-force** = fake PLAYER_WINs; rebuild units per battle.
- **Voucher ABI encoding** — ethers put the bytes offset AFTER the struct;
  manual encoding that puts offset first reverts.
- **Not free**: `commitMint` is payable; the bypass skips gameplay only.
- **Voucher expiry** — `deadline` is a few minutes; redeem promptly.

## Verification

```bash
# after max mint: balanceOf should equal cap (6), used == MAX_PER_WALLET
cast call <contract> "balanceOf(address)(uint256)" <wallet> --rpc-url <alchemy>
cast call <contract> "mintedBy(address)(uint8)" <wallet> --rpc-url <alchemy>
```
