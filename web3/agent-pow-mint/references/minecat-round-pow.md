# MINECAT round-PoW mint — verified mechanics (2026-08-17)

Site: `https://minecatnft.com` ("Proof-of-Luck", Robinhood 4663).
Contract: `0x6147a5244e890Ef8d41F82CA80455cE1bc658b5c` (verified, `MINECAT`,
symbol `MCAT`). Supply 10,000 hard cap. Wallet cap 5. Docs at `/docs.html`.

## Contract mechanics (from verified source)

- Round = `block.number / roundBlocks` (`roundBlocks=5` ≈ 60s on Orbit).
- `openRound()` (free, anyone): `seed = keccak256(blockhash(block.number-1),
  r, address(this))`; reverts `already open`.
- Valid solution: `uint256(keccak256(abi.encodePacked(seed, msg.sender,
  nonce64))) < ticketTarget()` where `ticketTarget = type(uint256).max /
  diffTicket` (diffTicket=20,000,000 live).
- LUCKY: `hv < luckyTarget()` (`luckyTarget = ticketTarget / luckyDivisor`,
  luckyDivisor=6) AND `roundMinted[r] < ROUND_CAP` (50) → `voucher[user]+=1`
  → claimable any time.
- BUST (valid but not lucky): `ticketFromRound[user] = r+1` → claimable when
  `currentRound() >= ticketFromRound`.
- `claim()` payable: `require(msg.value == mintPriceWei)`; voucher first,
  else ticket; mints next id; `wrong price` / `nothing claimable` reverts.
- `submitWork` checks wallet cap: `mintedBy + voucher + (ticket?1:0) < 5`.

## Verified run (Set 1, tokens #477 + #570)

- Balance went 0 → 2 via two `claim()` txs (method `0x4e71d92d`, blocks
  39041271 and 39042500, gasUsed ~100-130k). Price paid:
  `mintPriceWei = 0x6056f4f0bae4 = 0.0001059 ETH` (~$0.20) — NOT free.
- Mining/submitWork is 0-value (gas only); claim is the paid step.
- Two successful `submitWork` (BUST) earned tickets that later claimed.

## Miner script behavior (`scripts/minecat-auto.py`)

- Reads `currentRound()`; if seed zero → `openRound()` (mirrors site button).
- Grinds `keccak256(seed‖addr‖nonce8BE)` (60-byte message, nonce big-endian
  in last 8 bytes) via multiprocessing (pycryptodome).
- Re-verifies `currentRound()` unchanged before submit — discards stale
  nonce (would revert `hash above target`).
- Stops after one successful submit and re-reads state (avoids `solution
  replayed`); stops grinding when holding voucher/ticket; auto-claims when
  claimable; stops at `--max-mints` or wallet cap 5.
- Round changes often (~60s) vs expected solution time (~90s on 3 CPU cores
  at 1/20M difficulty) — expect many `no solution this pass` / `round changed
  before submit` lines; that is correct fail-closed behavior, not a bug.

## Pitfalls

- `openRound` "already open" is normal — someone else opened; read seed.
- `solution replayed` = same nonce submitted twice (wasted gas); break loop.
- `hash above target` on submit = round rolled; discard, re-grind.
- "Free mint" here = mining free, claim costs `mintPriceWei`; verify price
  before claiming.
- Do NOT re-grind from 0 each round for the same nonce space without
  tracking used nonces — cache per round seed.

## Manual state check

```bash
cast call <c> 'mintedBy(address)(uint256)' <addr> --rpc-url <rpc>
cast call <c> 'ticketFromRound(address)(uint256)' <addr> --rpc-url <rpc>
cast call <c> 'voucher(address)(uint256)' <addr> --rpc-url <rpc>
cast call <c> 'currentRound()(uint256)' --rpc-url <rpc>
```
