# Protocol-neutral routing refactor checklist

Use this when an existing production swap path must become one adapter among multiple protocols without changing live behavior.

## Vertical TDD slices

1. **Route value contract:** test protocol, token direction, pool/router, and immutability/copying of big integers.
2. **Compatibility mapping:** construct buy and sell routes from the existing token/venue model and assert every V3 field is preserved.
3. **Optimizer:** prove highest output wins at equal gas; then inject a gas-to-output cost converter and prove net output wins; reject an empty candidate set.
4. **Journal continuity:** build an execution request from existing options and prove prepared/submitted/mined callbacks remain attached.
5. **Interface conformance:** compile-time assertions for the production adapter's discovery, quote, and swap contracts.
6. **Integration:** route legacy public quote/buy/sell entry points through the adapter while retaining native wrap/unwrap and receipt-accounting branches.

Run each focused test once in RED before implementation, then GREEN. After refactoring, run race-enabled package tests, dependent execution/UI packages, and a full build.

## Interface boundaries

- `Route`: immutable protocol and token/pool/router identity.
- `RouteDiscoverer`: finds executable routes; no submission.
- `RouteQuoter`: returns amount out plus gas estimate/candidate metadata; no transaction side effects.
- `RouteSwapper`: accepts the selected route and the original hardened execution options/hooks.
- Optimizer: pure selection. Gas comparison requires a converter into the same unit as `amountOut`.

## Compatibility traps

- Do not make generic execution call a low-level ERC20-only function when wrapped-native routes need specialized wrap/unwrap logic.
- Do not drop dry-run, approvals, deadlines, nonce serialization, receipt parsing, or journal hooks at the adapter boundary.
- Do not implement future protocol internals merely because identifiers/interfaces exist.
- Unexpected files appearing mid-task can be concurrent work. Read before editing and report only changes you own.

## Ad-hoc verification fallback

If the environment cannot detect a canonical gate, create a temporary `hermes-verify-*` script using an OS-safe temporary path. Check formatting, race-test the changed package, test direct dependents, and build all packages. Report this explicitly as targeted ad-hoc verification, not as canonical suite green. Cleanup should be attempted separately so a cleanup approval does not block the verification run.
