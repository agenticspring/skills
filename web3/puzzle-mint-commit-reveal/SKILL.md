---
name: puzzle-mint-commit-reveal
description: Use for puzzle-gated NFT commit-reveal mints.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [web3, nft, puzzle, commit-reveal, brute-force, evm]
    related_skills: [transactional-trade-safety, token-launch-verify, web3-rpc-contract-audit]
---

# Puzzle-Gated NFT Minting

## Overview

Use this workflow for NFT collections where each token is unlocked by one or more deterministic puzzles and claiming uses an EVM commit-reveal flow. The core design is **prepare in parallel, broadcast in a serialized state machine, and never confuse a stale scan or a locally plausible answer with a claim**.

The reference implementation that motivated this skill has:

- a public puzzle corpus and word list;
- one to four sequential trials per token;
- AES-256-CBC sealed trials keyed by the previous answer;
- SHA-256 puzzle answers and a final answer hash;
- an EVM contract with `ownerOf`, `answerHash`, `commit`, `commitBlock`, `commitMinBlocks`, `commitMaxBlocks`, and `mint`;
- one funded wallet used for nonce-bearing commit/reveal transactions.

## When to Use

Use when a mint requires solving public puzzles before an NFT claim, especially when:

- later puzzles are sealed by earlier answers;
- many workers or native helpers are needed for brute force;
- other bots race for the same token IDs;
- claim submission is commit-reveal or otherwise delayed;
- a local corpus must be verified against an on-chain fingerprint.

Do not use this workflow for a normal ERC-721 mint with no puzzle, hash verification, or commit-reveal state machine.

## Phase 0: Scope and safety gate

1. Read the repository's `AGENTS.md`, claiming docs, puzzle docs, deploy manifest, ABI, and current miner implementation. Treat the checked-in miner as the reference until a focused diff proves otherwise.
2. Load secrets only from the local credential file/environment. Never copy a private key to a solver host, repository, logs, Obsidian, or worker payloads. Remote workers receive corpus and solver code only; the local signer performs transactions.
3. Verify chain ID, contract address, RPC endpoint, wallet address, balance, and gas estimate. Stop on any mismatch.
4. Query live `totalMinted`, `frontier`, `commitMinBlocks`, and `commitMaxBlocks`. Record the current block and remaining supply.

Completion criterion: the contract, chain, signer address, balance, gas estimate, and corpus fingerprint are all recorded as verified runtime facts.

## Phase 1: Verify the corpus and contract model

Run the repository's corpus verifier with the live RPC and contract. The local corpus fingerprint must match the on-chain corpus fingerprint before local answer hashes can replace a redundant `answerHash` read.

Verify the final answer formula from the miner, not memory. In the reference collection:

```text
final_hex = sha256(`${tokenId}|${answer1}|${answer2}|...`)
expected = keccak256(abi.encode(uint256 tokenId, bytes(final_hex)))
```

Verify the commitment formula from the actual ABI/miner. In the reference collection:

```text
commitment = keccak256(
  abi.encode(wallet, tokenId, salt32, utf8(final_hex))
)
```

Do not silently replace `bytes` with `bytes32`, change separators, normalize text, or add a `0x` prefix. Exact bytes matter.

Completion criterion: a known local fixture passes the same final-hash and commitment calculations used by the reference miner.

## Phase 2: Build a tri-state live availability scan

`ownerOf(tokenId)` is not binary at the RPC boundary. Classify results as:

| Result | State | Action |
|---|---|---|
| Address returned | claimed | discard |
| Protocol-specific revert meaning unclaimed | unclaimed | shortlist |
| 429, timeout, missing revert data, `UNSUPPORTED_OPERATION`, malformed response | unknown | retry or quarantine; never call it unclaimed |

For the reference contract, raw JSON-RPC `ownerOf` returned revert data beginning with `0xb1d04f08` for an unclaimed token. Confirm that selector from the current contract before hardcoding it for another project.

Use bounded concurrency and progress logging. A scan is a shortlist, not a reservation. Re-check the token exactly once immediately before commit, after the answer is already verified. Do not perform a slow second scan or a redundant `answerHash` call between that check and commit.

Completion criterion: the scan reports `claimed`, `unclaimed`, and `unknown` counts separately, with no RPC error counted as available.

## Phase 3: Sequential trial solver with pluggable handlers

Trials inside one token are sequential:

```text
solve trial 1
→ unseal trial 2
→ solve trial 2
→ unseal trial 3
→ ...
```

Parallelize different token candidates and independent work inside one trial. Never parallelize trial order.

For a sealed trial, use exactly:

```js
key = sha256(previousAnswer)                 // raw 32 bytes
iv  = first16(sha256(`${id}|iv|${trialIndex}`))
plaintext = AES-256-CBC-decrypt(base64, key, iv)
```

Treat readable plaintext as necessary but not sufficient. A wrong key can pass CBC padding by chance; the resulting candidate must solve the next trial or match the final answer hash.

Implement one handler per puzzle kind:

- `hunt-1`: hash every published word.
- `hunt-2`: use a native worker/helper over the 6,000² space; return all prefix hits, not only the first unverified hit.
- `hunt-3`: do not run naive 6,000³ brute force. Use a project-specific optimized index, GPU/native search, or deprioritize it with an explicit time budget. Never claim it is solved because a prefix candidate was found.
- `rule`: parse the exact required step count. Search permutations without repetition and test every worked example before applying the rule to the target. Cache step transforms.
- `cipher`: use the stated Vigenère key length. Prefer dictionary-constrained key recovery and retain enough candidates for sealed-trial validation. Frequency scoring alone is not proof.
- `hidden`: enumerate spacing and offset, then validate against the word list and final hash.
- `ottendorf`: parse both `-` and `/` pair formats; word and character indices are one-based.
- `lattice`: enumerate the small permutation space and evaluate every relation and exclusion.
- `construct`: parse arbitrary word count, initials, lengths, total length, and hash prefix. Use filtered pools. Native helpers must be generic for N words; never pass a 5-word problem to a 4-slot helper.
- `relic`: parse the specified token image/grid and coordinates exactly; expand SVG rectangles that cover multiple squares.
- `chain`: implement the exact stated normalization and transform sequence, including NFC/NFD and multi-part joins.

Every native helper must:

- validate argument count and word-slot count;
- bound input lengths;
- return all candidate hits or a clearly documented bounded top-K;
- never segfault on unsupported N-word input;
- be followed by AES/decrypt or final-hash validation.

Completion criterion: each returned answer has an evidence record containing the handler, exact input, exact answer bytes, and either the next trial successfully decrypted or the final hash matched.

## Phase 4: Candidate queue and brute-force budgeting

Use a persistent queue with these fields:

```json
{
  "tokenId": 0,
  "priority": 0,
  "trialIndex": 0,
  "status": "queued|solving|verified|commit_attempted|claimed|failed|unknown",
  "answers": [],
  "finalHex": null,
  "attempts": 0,
  "lastError": null
}
```

Prioritize:

1. unclaimed tokens with one trial;
2. small lattice/hidden/ottendorf/rule/cipher trials;
3. filtered construct with a small Cartesian product;
4. two-word hunt with a native helper;
5. multi-trial candidates whose first trial is cheap;
6. 3-word hunt or very large construct only when a measured native/GPU rate gives a realistic completion time.

Do not let one expensive child block the queue. Each worker has a timeout and cancellation path. Record `solving` before spawning it and recover stale jobs on restart.

Completion criterion: a worker crash, timeout, or host restart leaves a resumable queue and does not lose an already verified candidate.

## Phase 5: Commit-reveal execution

Preparation may be parallel. One funded wallet's nonce-bearing execution must be serialized.

For each verified candidate:

1. Re-check `ownerOf` immediately before commit. If claimed, mark `race_lost` and continue.
2. Run `commit.staticCall`/gas estimation with the exact commitment. This is free and catches contract-level failure.
3. Broadcast `commit(commitment)` immediately. Do not do another slow read first.
4. Persist the commitment, token ID, salt, answer, wallet, broadcast TxHash, and state **before** doing more work.
5. Wait for the commit receipt. Use the receipt's `blockNumber`, not a stale `commitBlock` read from another RPC node.
6. Wait until `receipt.blockNumber + commitMinBlocks()`.
7. Run `mint.staticCall(tokenId, answerBytes, salt)` repeatedly only for known propagation/age errors. Stop on definitive errors such as already claimed, wrong answer, expired commitment, or duplicate commitment.
8. Broadcast `mint` once after simulation succeeds. Persist the reveal TxHash immediately.
9. Wait for a successful receipt and re-read `ownerOf(tokenId)`.
10. Mark `claimed` only after receipt success and owner verification.

The 60-block delay is a contract rule, not a solver delay. Do not skip it or replace it with a wall-clock sleep. Public RPC pools can disagree on head height, so a free `staticCall` after the minimum age is the authoritative reveal preflight.

Completion criterion: every claimed item has both TxHashes, successful receipts, block numbers, and an owner read proving the signer owns the token.

## Empirical patterns from successful claimers

On-chain analysis of the completed reference collection showed patterns that should shape future runners:

- A successful operator did not stop after one candidate. The strongest observed wallet had dozens of successful final calls in the audited window, alongside many reverted attempts. Track `success` and `revert` separately; raw transaction count is not NFT count.
- Successful claimers kept a rolling queue of commitments and candidates. The right architecture is a bounded pipeline: solve/verify many candidates, submit valid commits as nonce permits, and maintain a reveal queue. Do not serialize the entire system around one solve, but do serialize nonce-bearing calls per wallet.
- Several claimers approved an operator/conduit before or around the claim flow and later transferred minted NFTs to a separate consolidation wallet. This is inventory management, not proof that the solver was correct. Verify approval target against the official contract/ABI and keep execution and storage wallet roles explicit.
- Explorer method decoding may be incomplete. The reference reveal/mint selector appeared as raw `0x0adc91c4` in some responses. Fingerprint methods by verified ABI selector and receipt/log outcome, not explorer display text alone.
- Aggressive failed reveals are expected in a race, but failed transactions still burn gas. Use static simulation, bounded candidate admission, and per-wallet budget ceilings; do not copy a high-failure strategy blindly.
- A third-party wallet sweep or consolidation is a separate operation after claim confirmation. It must never be coupled to the claim transaction or used to infer ownership before the receipt is final.

These are empirical observations, not a license to broadcast unverified answers. The invariant remains: final hash proof first, serialized commit state, reveal-age check, receipt, and direct ownership verification.

## Phase 6: Remote solver pattern

Remote compute is allowed only for public corpus and deterministic solving:

- copy corpus, wordlist, solver code, and immutable config;
- set `IA_ROOT`/project root explicitly; never hardcode the local path;
- keep wallet credentials on the signer host;
- use a bounded `screen`/service with a log and result JSON;
- upload only verified results back to the signer;
- re-check ownership locally before commit.

Remote workers must emit structured results, for example:

```json
{"tokenId":7688,"answers":["..."],"finalHex":"...","verified":true}
```

A worker saying “solved” without a final hash match is not evidence.

## Common Pitfalls

1. **Stale scan treated as reservation.** Fix: re-check immediately before commit and keep solving alternatives.
2. **RPC errors treated as unclaimed.** Fix: tri-state classifier; only the confirmed protocol revert means available.
3. **Answer prefix treated as full proof.** Fix: decrypt the next sealed trial or match the complete final hash.
4. **Hardcoded local path on a remote worker.** Fix: use `IA_ROOT` and test one imported file before launching a batch.
5. **4-slot helper called with 5 words.** Fix: generic N-word helper or explicit argument validation; never allow a segfault.
6. **Only 3 rule steps searched.** Fix: parse and honor `built from exactly N`.
7. **Construct/hunt brute force with unexplained caps.** Fix: measure search rate, use native helpers, and report ETA; do not silently return an empty result.
8. **Solver child monopolizes the queue.** Fix: per-candidate timeout, cancellation, and bounded worker pool.
9. **Commit delayed by redundant reads.** Fix: final hash verification first, one immediate owner check, simulation, then broadcast.
10. **Commit block read from a stale RPC node.** Fix: use the commit receipt block.
11. **Retrying an uncertain broadcast.** Fix: reconcile nonce, transaction hash, receipt, and contract state before retrying.
12. **Reporting preparation as success.** `prepared`, `funded`, `broadcast`, and `confirmed` are distinct states.

## Verification Checklist

- [ ] Current contract, chain ID, RPC, frontier, total minted, and remaining supply recorded.
- [ ] Corpus fingerprint matches on-chain.
- [ ] Owner scan reports claimed/unclaimed/unknown separately.
- [ ] Solver handles the exact trial kind and count.
- [ ] Every sealed answer decrypts to readable text and passes the next-stage/final-hash check.
- [ ] Final hash matches the seeding hash before gas.
- [ ] Commit simulation succeeds.
- [ ] Commit TxHash and receipt block are persisted.
- [ ] Reveal waits for the contract's minimum block age and passes static simulation.
- [ ] Reveal TxHash, receipt, and final `ownerOf` are verified.
- [ ] No private key was copied to a worker, log, repository, or note.
- [ ] Any failed/unknown item remains recoverable in the queue.
