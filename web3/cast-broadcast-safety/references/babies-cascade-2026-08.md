# BABIES Cascade v4 — mint → NFT → sweep (2026-08-21)

Session transcript of the RWA FLYWHEEL BABIES cascade
(`0xfCe5F08D3167863ad8D85735bbE8Ec973dc32bCC`, Robinhood 4663) that surfaced
the broadcast-wrapper bugs. `mintFree()` `0x8ab53447`, freeMinted cap 1/wallet,
global drip `lastFreeMintAt + mintInterval` (observed 3s → 5s → 60s → 600s → 2s
→ 10s — the dev changes it live, so re-read every round).

## Working workflow (user-specified v4)

1. Fund current wallet from hub (0.00085 ETH), skip if already funded.
2. Run `babies_sniper.py` (target 1, ACTIVE 1, CENTRE -120, TUNE 1).
3. On WIN: `safeTransferFrom(owner, Set1, tokenId)` — NFT to hub immediately.
4. Sweep ENTIRE remaining ETH (keep only real transfer fee) to next wallet.
5. Repeat through Set 100; stop when balance < MINBAL (0.00006).

## Bugs found & fixed (in order)

| # | Symptom | Root cause | Fix |
|---|---------|-----------|-----|
| 1 | Sweep left 0.00001/wallet (~$0.02) | fixed `GAS_BUF` in sweep | keep = `21000*gas_price*1.15`, min 0.0000012 |
| 2 | MINBAL 0.00012 stopped cascade early | floor too high | MINBAL = 0.00006 (sniper MIN_BALANCE_WEI) |
| 3 | Sweep reverted `insufficient funds` in-script, manual OK | `value*1e18` double-conversion in broadcast wrapper | name param `value_wei`, pass wei as-is |
| 4 | `Must specify a recipient address` | `--json <to>` dropped when refactoring base cmd | keep recipient in base list |
| 5 | First sweep after win reverts | pending sniper txs reserve balance in estimate | fresh nonce per retry + backoff 4s+attempt*3 |
| 6 | cast default fee fails thin balances | cast estimates high max fee | always pass `--gas-price 0x1406f40` (~0.021 gwei) |

## Timing notes (same bot, different outcome)

- Set 1 WIN at interval 3s: fired -120ms, landed sec +0, ~40 shots.
- Same bot at interval 600s: 0 wins in 13 min (lottery, not race).
- At interval 2s the cascade won 22 wallets in ~7 min (Set 3-24).
- Interval is dev-controlled and moves every win; never precompute boundary.

## Verified numbers

- Fee per reverted mintFree shot: gasUsed 28403 × 0.02004 gwei ≈ 0.00000057 ETH.
- Blockscout `fee` field = reserved (gasLimit × maxFee), NOT actual — actual is
  gasUsed × effectiveGasPrice.
- 100 wallets scanned on-chain: freeMinted + balanceOf both 1 = real win;
  log win count over-counts (receipt check + sync both credit).

## Result

24 BABIES consolidated to Set 1 (22 NFT transfers + hub's own), residual dust
~0.00000008 ETH/wallet below transfer fee — "sampai ga bisa tx" endpoint.
