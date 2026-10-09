# EVM Claim Debugging Reference

Use this reference for free-mint / puzzle-claim workflows with live ownership races.

## Failure classification

- `ownerOf` returns an address: claimed.
- `ownerOf` reverts with the protocol's normal nonexistent-token behavior: potentially unclaimed; immediately re-check before broadcast.
- `UNSUPPORTED_OPERATION`: the Contract has no runner, commonly caused by `new Contract(address, abi)` without a provider/signer. Never classify as unclaimed.
- `missing revert data`, HTTP 429, timeout, network detection failure, and transport errors: unknown. Retry with bounded backoff or quarantine the candidate; never treat as unclaimed.

## Required preflight

1. Resolve one explicit project root and use it consistently. Do not mix a temporary clone with the active worktree.
2. Instantiate read contracts with an explicit `JsonRpcProvider`.
3. Verify chain ID, contract address, corpus fingerprint, and wallet balance.
4. Separate scan RPC from broadcast RPC if a provider has throughput limits, but do not silently switch networks.
5. Re-check ownership immediately before `commit`.
6. Validate the answer using the exact reference formula, e.g. `keccak256(abi.encode(uint256 tokenId, bytes UTF-8 final answer))`, not a similar-looking hash.

## Batch shape

- Parallelize local puzzle solving and read-only status checks with a bounded worker pool.
- Serialize nonce-bearing commit/reveal transactions from one wallet.
- Maintain a queue of verified candidates; if one is claimed before broadcast, try the next verified candidate rather than stopping.
- Keep batch attempts bounded and log progress before/after expensive scans. Infinite loops hide failures and leave orphan processes.
- After any ambiguous `sendRawTransaction`/`sendTransaction` result, reconcile the pending nonce and transaction receipt before retrying.

## Solver performance pitfalls

- Do not retain millions of brute-force plaintext objects for Vigenere. Use dictionary-constrained key recovery, frequency-analysis candidates, or a compiled worker, with a hard per-candidate timeout.
- Cache deterministic transforms in rule puzzles.
- Parse every published format: Ottendorf pairs may use hyphens (`4080-1`), construct acrostics may be quoted, and some trial outputs are encrypted again when the statement says "what you found is not the answer".
- Two-word SHA hunts require a dedicated bounded worker/search; a short JavaScript timeout silently producing no candidate is a false negative.
- Always validate the full final answer against the seed hash before spending gas.

## Reporting vocabulary

- `prepared`: local answers and hashes validated.
- `funded`: the exact execution wallet has a confirmed balance.
- `broadcast`: a transaction hash exists.
- `confirmed`: the receipt succeeded and target ownership was re-read.

Never report "minting" or "started" for a scan, delegation, or solver process alone.
