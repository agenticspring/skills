# Fablings drip-race free mint (worked run, 2026-08-19)

Collection: FABLINGS — Kiln items, Robinhood Chain 4663.
Contract (items): `0xa185814414aa3D39c9A0B73A373E00C8C04Cb384`.
Mint: `mintFree()` = `0 wei` (nonpayable), `FREE_PER_WALLET = 10`.
`mintSkip()` = paid lane (0.0005 ETH) to bypass cooldown — skip it.

## The core mechanic: GLOBAL drip, not per-wallet

- `lastFreeMintAt()` (uint40) resets when ANY wallet wins a free slot.
- `mintInterval()` (uint256) is owner-set, read live (was 3s during the run).
- A mint outside the open window reverts `DripNotReady()` = `0x5273678a`.
- `mintedBy`/`freeMinted(address)` tracks the per-wallet cap; `freeLeft(...)`
  does NOT exist on this contract — use `freeMinted` + `FREE_PER_WALLET`.

## Verified selectors (keccak, do not guess)

| Function | Selector |
|----------|----------|
| `mintFree()` | `0x8ab53447` |
| `lastFreeMintAt()` | `0xfca4b80e` |
| `mintInterval()` | `0x0e726e6b` |
| `totalSupply()` | `0x18160ddd` |
| `FREE_PER_WALLET()` | `0xcd90e5af` |
| `freeMinted(address)` | `0x389fcf06` |
| `balanceOf(address)` | `0x70a08231` |
| `tokenOfOwnerByIndex(address,uint256)` | `0x2f745c59` |

Pitfall hit live: hardcoding `0x392e128e`/`0xdc1eaa42` for lastFreeMintAt/
mintInterval made `eth_call` return null and the wait loop spin forever.
Always compute selectors with `keccak(text=name+"(...)")[:4]` from the ABI.

## Race loop that worked

```python
# read state, wait for window, fire, retry on DripNotReady
while minted < cap:
    while True:
        last = call(SEL_LAST); iv = call(SEL_IV); now = block_timestamp()
        if (last + iv) <= now: break
        time.sleep(0.15)
    tx = cast send --nonce <n> <contract> mintFree()
    if DripNotReady/0x5273678a in stderr: continue   # lost race, next window
    if FreeWalletCapReached/0x53353903 in stderr: break
    wait receipt; if status==1: minted += 1
```

## Results

- 10/10 minted on Set 1, `freeMinted(Set1) = 10`, `balanceOf = 10`.
- Tokens #33075, #33077–#33085 (one gap = another wallet won a slot).
- 21 attempts for 10 successes (11 REVERTED = lost races) — normal.
- Gas only: ~0.00004 ETH total for 10 mints; value 0 on every tx.
- Nonce 31 REVERTED first (stale selector made the loop fire at wrong time),
  nonce 32–42 all SUCCESS after selector fix.

## Extension to other wallets

Same loop, swap `--private-key` per Set. All wallets share the same global
drip, so more concurrent wallets = more attempts lost to each other; keep one
miner process per wallet spaced slightly apart or accept lower per-wallet hit
rate. 100 wallets × 10 free = 1,000 NFTs if supply (40,000) lasts.
