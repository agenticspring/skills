# EVM Puzzle Claim Reference

## Commit/reveal state machine

Use this sequence for a puzzle-gated NFT claim:

1. Discover candidates with a tri-state ownership probe.
2. Solve trials sequentially; parallelize independent candidate solving only.
3. Verify the final answer locally against the exact contract formula and corpus fingerprint.
4. Persist candidate ID, all trial answers, final answer, salt, and intended commitment.
5. Minimize the final pre-commit path. A stale scan is not a reservation.
6. Broadcast `commit(bytes32)` and persist the returned transaction hash immediately.
7. Wait for live `commitMinBlocks()`; do not hardcode 60.
8. Run `mint.staticCall(tokenId, answerBytes, salt)`.
9. Broadcast `mint(tokenId, answerBytes, salt)` only after simulation passes.
10. Verify receipt success and re-read `ownerOf(tokenId)`.

## Ownership probe classification

For Inference Angels, `ownerOf(tokenId)` returns an address when claimed and reverts with selector `0xb1d04f08` when unclaimed. Treat all other errors—429, timeout, missing revert data, unsupported runner, transport failure—as `unknown`, never as available.

## Answer verification

The final answer is the lowercase SHA-256 of:

```text
<tokenId>|<trial1>|<trial2>|...
```

The on-chain comparison form is:

```solidity
keccak256(abi.encode(uint256(tokenId), bytes(finalAnswerHex)))
```

A prefix match from a brute-force helper is only a candidate. Validate it by opening the next sealed trial or by matching the final seeding hash.

## Brute-force worker rules

- Parse word count and rule-step count from the statement; do not assume four construct words or three rule steps.
- Filter by initial letters and exact lengths before enumerating combinations.
- Keep helpers dimension-safe: a 5-word helper must reject 4-word input and vice versa.
- A remote worker must receive all band files, the wordlist, dependencies, and a configurable corpus root (`IA_ROOT`); verify its runtime path before solving.
- Record `prepared`, `broadcast`, and `confirmed` separately. A solver result is not a broadcast.

## Evidence checklist

Before reporting success, retain:

- commit TxHash;
- commit receipt block;
- reveal TxHash;
- reveal receipt status;
- token ID;
- final owner address;
- gas spent.

A mint/reveal transaction exposes answer bytes and salt in calldata. That is expected; the protection is the earlier commitment and minimum-age window.
