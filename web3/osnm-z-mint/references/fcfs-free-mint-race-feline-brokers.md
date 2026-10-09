# FCFS free-mint race — Feline Brokers case study

## What happened (2026-08-16)

User: "Mint 2" for `https://opensea.io/collection/felinebrokers` (claimed free
mint). Target: Set 1, Robinhood, quantity 2.

Observed timeline:

| UTC | State |
|---|---|
| 15:58 | Collection metadata: contract null. Drops endpoint: `0x62ee0cd8d3b62a961a635ba4fa10d21ed866f8e6`, `seadrop_v1_erc721`, supply 1207/5555. Active stage `signed_presale` price 0, ends 16:00:33Z. OSNM-Z calldata fails `no wallet remains eligible`. |
| 16:00 | Active stage still `signed_presale`, now ends 16:18:33Z (extended). Public stage moved to 16:18:33Z. |
| 16:01 | Same active stage; public moved to 19:00:33Z in a later read, presale 18:15:33Z. Supply 5555/5555, `is_minting: false` → sold out. |

Result: drop sold out before the public stage opened; nothing minted.

## Root causes

1. Multi-stage drop with a partner-only `signed_presale` first. Set 1 not
   eligible → OSNM-Z correctly failed closed.
2. OpenSea pushed the active stage end time repeatedly (16:00 → 16:18 →
   18:15). Waiting for a fixed "public opens at T" is unreliable.
3. The manual loop (sleep until T, re-read, calldata, then mint) is minutes
   too slow for a supply that went 1207 → 5555 (fully minted) in the window.
4. A "free mint" label is only true for the stage that is actually eligible
   for the wallet; the partner presale was also free but restricted.

## Correct approach (written into skill)

- Poll the drops endpoint every 5-10s with `scripts/watch-drop-stage.py`.
- Exit 0 on target stage live → immediately run `osnm-z calldata` + mint.
- Exit 1 on `total_supply >= max_supply` or `is_minting: false` → stop.
- Pre-authenticate and keep the calldata path warm before the window.
- Never trust one reading of `active_stage.end_time`.

## Evidence kept

- Contract: `0x62ee0cd8d3b62a961a635ba4fa10d21ed866f8e6`
- Drop API: `https://api.opensea.io/api/v2/drops/felinebrokers`
- No transaction was signed or broadcast; no funds were spent.
