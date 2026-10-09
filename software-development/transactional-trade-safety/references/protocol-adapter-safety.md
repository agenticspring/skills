# Protocol Adapter Safety

Use this checklist when adding a DEX/router adapter to an existing transaction-journaled trade engine.

## Modeling

- Keep route identity protocol-agnostic: protocol, token-in, token-out, pool, and router are the common contract.
- Put protocol-specific fields behind a concrete route type (for example, V2 factory) rather than adding optional fields to every token model.
- Reject zero-address routes at construction.
- Keep chain registries separate from adapter mechanics. Add a chain only when factory/router/wrapped-native addresses are authoritative in repository context or official documentation; otherwise ship a chain-neutral adapter.
- Do not modify unrelated protocol implementations merely to make the new abstraction compile.

## Strict TDD slices

Use vertical red → green cycles, running each focused test before production code:

1. Route construction, reversal, and immutable quote values.
2. Factory discovery (`getPair`) against the configured wrapped-native quote.
3. Pair reserve decoding (`getReserves`).
4. Exact-input router quote (`getAmountsOut`) with path/output-shape rejection.
5. Native buy calldata using the fee-on-transfer Router02 entrypoint.
6. Native sell calldata using the fee-on-transfer Router02 entrypoint.
7. Receipt decoding for actual post-tax output.
8. Transaction submission integrated with journal hooks and exact approval.

## Journal and approval boundaries

- Reuse the hardened prepared → submitted → mined hooks at signing, accepted-broadcast, and confirmed-receipt boundaries.
- Preserve the transaction hash and submitted flag on every post-broadcast failure.
- Approve exactly the sell amount, not an unlimited allowance.
- For tokens requiring allowance reset, use `0` then exact amount when the existing non-zero allowance is insufficient.
- Perform approval and swap under the same per-wallet nonce lock. Be careful not to call a helper that acquires that same non-reentrant lock again.

## Fee-on-transfer output accounting

- A router return value or pre-trade quote is not the realized output.
- Native buy: sum canonical output-token `Transfer` events to the recipient. This yields actual post-tax token output.
- Native sell: decode the wrapped-native `Withdrawal` emitted during pair/router payout, using the source address required by that router implementation.
- Reject a mined receipt if a positive output cannot be decoded; leave it reconcilable rather than fabricating proceeds.
- Add fixtures containing irrelevant logs, malformed event data, multiple matching transfers, and wrong recipient/source topics.

## Verification

- Run focused adapter, journal, EVM transaction, and engine tests with `-race -shuffle=on -count=1`.
- If the repository-wide suite is blocked by an unrelated incomplete package, report the blocker precisely and do not claim suite green.
- When no canonical command is discoverable, create an OS-safe temporary `/tmp/hermes-verify-*` script that checks formatting plus the focused packages, run it, remove it, and label the evidence **ad-hoc focused verification**.
- Never perform a live transaction unless separately authorized.
