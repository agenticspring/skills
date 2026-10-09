# Position accounting correctness

Use this workflow for changes to `internal/store/positions.go` and its PnL/Positions callers. Keep DB schema/journal and engine state-claim behavior out of scope unless explicitly requested.

## Invariants

1. **Parse numeric strings at the store boundary.** `amount_in_usdc`, `tokens_out`, sold quantity, and proceeds are positive base-10 integers. Malformed, zero, and negative values return a sentinel/typed error; never silently coerce them to zero.
2. **Transferred inventory attribution.** If actual sold quantity exceeds tracked inventory, cap the tracked closed slice and attribute proceeds proportionally:
   `trackedProceeds = totalProceeds * trackedTokens / actualSoldTokens`.
   Never attach all proceeds to the smaller tracked cost basis. An alternative API may reject the mismatch, but it must do so explicitly before mutating rows.
3. **Cumulative lifecycle PnL.** Token-level PnL is not the latest closed row. Aggregate all closed slices plus remaining open semantics:
   - lifecycle cost = sum(closed realized costs) + open cost;
   - lifecycle value = sum(closed proceeds) + current quoted value of open holdings;
   - lifecycle PnL = lifecycle value - lifecycle cost.
   The PnL card must consume this aggregate.
4. **Wallet filter symmetry.** Positions balances and cost basis must use the same wallet set. A selected-wallet view must not compare one wallet's current balance against all wallets' cost basis.
5. **No fabricated accounting.** Missing/malformed accounting data is an explicit error state, not zero PnL.

## Strict TDD slices

Run one vertical red→green cycle at a time:

1. Transferred inventory: tracked 600, actual sold 1,000, proceeds 200 → closed tokens 600 and attributed proceeds 120.
2. Invalid values: malformed/zero/negative buy cost, bought tokens, sold tokens, and proceeds must fail with the accounting error.
3. Partial-sale lifecycle: cost 100; sell 500 for 60, then 250 for 40; remaining current value 35 → lifecycle cost 100, value 135, open cost 25.
4. Wallet filter: wallet A cost 100 and wallet B cost 300; selecting A yields cost 100.
5. Preserve existing partial/full sell and average-buy regression tests.

## Caller integration

- PnL card: quote current open holdings, then pass that current value to the store lifecycle helper. Display aggregate lifecycle cost/value, including when holdings are now zero.
- Positions: derive the wallet filter first, then aggregate open cost basis only for matching positions. Reject malformed stored cost rather than skipping it.
- Real sell callers should handle and surface store errors; do not discard `RealizeSell` failures in new code.

## Verification

When the repository has unrelated build failures, create an OS-safe temporary verifier with `mktemp /tmp/hermes-verify-XXXXXX.sh`, check `gofmt -l` on changed files, run focused store and caller tests with `-count=1`, and remove the script. Report this explicitly as **ad-hoc targeted verification**, not full-suite green. Still run the full suite when it is available.

Do not run live transactions, restart the bot, or commit unless explicitly requested.
