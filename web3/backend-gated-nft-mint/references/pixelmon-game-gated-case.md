# Pixelmon game-gated mint — deterministic battle engine bypass (verified)

Verified 2026-08-21. Target: `https://pixelmon.mom` — GenesisCapsule on Robinhood
4663, contract `0x7dE3B4eC32929c7252276bc1b33e4A9FE724180f`. One mint landed
(commitId 942, finalize status 1). All values redacted of secrets.

## Mint economy (why this is a backend gate, not free)

- `price()` = 0.0001 ETH (source verified shows 0.00015; live call = 0.0001 —
  re-read live, never trust UI or even verified source constants blindly).
- `MAX_PER_WALLET = 6` lifetime. Credits only from winning BOSS battle:
  `MINTS_PER_WIN = 3` per clear, clamped to 6.
- Flow: `startBattleSession` → server signs a win voucher only after replaying
  your action transcript → `redeemWinVoucher` on-chain (+3 credits) →
  `commitMint` (pays price, spends 1 credit) → `finalizeMint(commitId)`.
- So the "game" is the gate. Mint itself is PAID.

## Key insight: the engine is deterministic and shipped client-side

- Site serves `engine.mjs` (JS reference implementation) at
  `/engine/src/engine.mjs`. Comment says it must match `contracts/lib/BattleEngine.sol`
  and `BotAI.sol` **bit for bit**.
- Damage model: fixed % of max HP from a table `(move x defender element x weather)`
  → NO damage RNG. Only AI decision noise + speed ties consume the seeded PRNG.
- `startBattleSession` returns `{sessionId, seed, expiresAt}`. With the seed +
  both teams, the whole battle is replayable locally with identical results.
- Client battle loop: `battleSteps(team, bot, difficulty, seed, {log})` generator;
  yields `{phase:'action'}` per turn; resume with `it.next(action)`.

## Winning team discovery

- Fixed `BOT_TEAM` (read from `app.js`): `[ {2,[0,2]}, {1,[0,1]}, {3,[3,0]} ]`.
- `decide(st, true, DIFFICULTY[3])` (exported from engine) is the bot's own
  smart policy — use it as the player policy (same function, `isPlayer=true`).
- Winning team depends on the seed. Brute-force team compositions
  (3 species x slot pairs) against a battery of seeds and pick a team that
  wins ≥80%. Verified winner (15/15 seeds):
  `[ {3,[0,1]}, {1,[0,1]}, {2,[0,1]} ]` (VERDANT/PYRON/TIDRA, first two moves).
- **Pitfall: rebuild the bot team fresh for every simulated battle.**
  `battleSteps` mutates pet objects (hp/pp). Reusing one bot array across the
  brute-force loop yields fake wins (turns:0, exhausted opponents). This bug
  produced a false "winning team" — caught when the real server seed lost.

## Transcript must mirror the client exactly

- Client pushes EVERY value it passes to `it.next()` into the transcript,
  **including `null` on `faintSwitch` phases**:
  `actionTranscript.push(action)` where action is `null` for faintSwitch.
- Server error `400 "battle replay is incomplete"` = your transcript is missing
  the `null` entries. Replay script must do:
  ```js
  actions.push(phase === 'faintSwitch' ? null : act);
  cur = it.next(phase === 'faintSwitch' ? null : act);
  ```
- Claim: `POST /api/battle/claim {sessionId, wallet, actions}` → 200
  `{voucher: {player, voucherId, deadline}, signature}`.

## On-chain redeem ABI encoding (the trap)

`redeemWinVoucher((address player,bytes32 voucherId,uint64 deadline),bytes)`

Correct calldata (verified equal to ethers `Interface.encodeFunctionData`):
1. selector `0xe8ce4bd9`
2. struct fields INLINE first: player (32B padded) + voucherId (32B) + deadline (32B)
3. THEN the dynamic offset word = 0x80 (128 = 96 struct + 32 offset word)
4. then bytes length + signature padded to 32B

My first attempt put the offset BEFORE the struct fields → `revert 0x`.
ABI rule: for `(struct, bytes)`, tuple fields are encoded in place, the dynamic
bytes offset word comes after the whole struct.

Cross-check any hand-rolled encoding against ethers before broadcasting:
```js
const iface = new ethers.Interface(["function redeemWinVoucher((address,bytes32,uint64),bytes) returns (uint8)"]);
iface.encodeFunctionData("redeemWinVoucher", [voucher, signature]);
```

## Finding the commitId to finalize

- `totalCommitted()` is a counter of ALL commits ever; the commitId for YOUR
  tx comes from the `MintCommitted` event, indexed topic[1]:
  `MintCommitted(uint256 indexed commitId, address indexed player, uint64 commitBlock)`
  → commitId = topics[1], commitBlock = data. Example: totalCommitted 1053 at
  that moment but our commitId was 942 (other players' commits interleave).
- Don't scan `commits(id)` down from totalCommitted expecting your id there —
  read the event from your own commit tx receipt (Blockscout
  `/api/v2/transactions/<hash>/logs` decodes it).
- `finalizeMint(commitId)` is callable by anyone; verify `balanceOf(wallet)` → 1
  and `mintedBy(wallet)` incremented after.

## Project structure used

- `/root/projects/pixelmon-bot/`: `pixelmon_mint.py` (orchestrator),
  `sim_battle.mjs` (replay + transcript), `engine.mjs` (vendored from site).
- Full flow log: battle start → sim PLAYER_WIN → claim 200 → redeem status=1 →
  commit status=1 → finalize status=1. Set 1 ended balanceOf=1, credits=3
  (2 more mints possible), cost ≈ 0.000106 ETH total.
