# MINECAT round-based NFT PoW (verified run 2026-08-17)

Round-based PoW mint on Robinhood Chain (4663), different from EIP-918
one-block races. Two confirmed claims on Set 1 with a 3-core Python miner.

## Contract

- Contract: `0x6147a5244e890Ef8d41F82CA80455cE1bc658b5c` (verified "MINECAT")
- Supply: 10,000 (MAX_SUPPLY), round cap 50 (ROUND_CAP), wallet cap 5
- Round: `currentRound() = block.number / roundBlocks` (5 blocks, ~60s)
- Difficulty: `diffTicket = 20000000`, `luckyDivisor = 6`
- `ticketTarget() = uint256.max / diffTicket` (1/20M per nonce)
- `luckyTarget() = ticketTarget / luckyDivisor` (1/120M → LUCKY)
- `mintPriceWei()` read live; claim is payable

## Flow

1. `openRound()` — anyone; seeds `keccak256(blockhash(block-1), r, contract)`.
   Only valid for the current round; reverts `already open` if someone else
   opened first.
2. Grind: `h = keccak256(seed(32) ‖ addr(20) ‖ nonce64BE(8))` (60 bytes).
   Valid when `uint256(h) < ticketTarget`.
3. `submitWork(uint64 nonce)` — value 0 (gas only):
   - `h < luckyTarget && roundMinted[r] < ROUND_CAP` → LUCKY: `voucher += 1`
   - else → `ticketFromRound[wallet] = r + 1` (BUST)
4. `claim()` payable `mintPriceWei`:
   - `voucher > 0` → use voucher
   - else `ticketFromRound != 0 && currentRound >= ticketFromRound` → use ticket
   - else revert `nothing claimable`

## Python miner core (pycryptodome, multiprocessing)

```python
from Crypto.Hash import keccak as _keccak
msg = bytearray(60)
msg[0:32] = seed            # bytes32 from roundSeed(r)
msg[32:52] = addr_bytes     # 20 bytes
msg[52:60] = nonce.to_bytes(8, 'big')
h = int.from_bytes(_keccak.new(digest_bits=256, data=bytes(msg)).digest(), 'big')
ok = h < ticketTarget
lucky = h < luckyTarget
```

Multiprocessing `Pool(cores)` over nonce ranges; terminate pool on first
solution. Verified at 3 cores, batch 3-4M nonces per worker.

## Bugs hit and fixes

| Error | Cause | Fix |
|---|---|---|
| `hash above target` | nonce found in round N submitted after round rolled to N+1 (new seed) | re-check `currentRound()` before submit; discard stale nonce |
| `solution replayed` | same nonce submitted twice after a successful `submitWork` | stop the round after first success; re-read wallet state |
| `nothing claimable` on claim | ticket/voucher already consumed | read `voucher`/`ticketFromRound` fresh before claim; expect this if balanceOf already incremented |
| `already open` on openRound | another miner opened the round first | treat as normal; read the seed and mine |

## Key selectors

- `currentRound()` `0x8a19c8bc`, `roundSeed(uint256)` `0x18edfe20`
- `openRound()` `0xe562dfd9`, `submitWork(uint64)` `0x98dc56f1`
- `claim()` `0x4e71d92d`
- `ticketTarget()` `0x8db09524`, `luckyTarget()` `0x155c7a56`
- `mintedBy(address)` `0x3cef28d2`, `voucher(address)` `0x17d7de7c`,
  `ticketFromRound(address)` `0xff25a924`
- `mintPriceWei()` `0x4f12b40f`, `totalMinted()` `0xa2309ff8`

## Results

Set 1 (`0xBff994004E9558A8e7e4CD0D817884dC7ff8e65d`):
- MINECAT #477 (claim tx `0x38d9decb...`) and #570 (claim tx `0x1deec363...`)
- `mintedBy=2`, `balanceOf=2`; cost per claim ~0.0001059 ETH + gas
- Balance after: ~0.0010768 ETH

## Source files

- `/root/projects/spring-mint-bot/minecat-auto.py` — full auto miner+claimer
  (openRound if needed, grind, submitWork, auto claim, stop at cap)
- Log: `/root/projects/spring-mint-bot/minecat-auto.log`
