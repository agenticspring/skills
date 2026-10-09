# Reliable ERC20 Metadata Reads

Use this pattern when token cards or trade routing cache `?`, empty strings, zero decimals, or zero supply after a partial RPC/rate-limit failure.

## Root cause

Convenience helpers that collapse `(result, error)` into `nil` or a default conflate three states:

1. RPC/transport failure (`429`, timeout, gateway error),
2. successful call with empty/malformed ABI output,
3. valid metadata.

If state 1 or 2 is converted to `"?"`, symbol-as-name, `18`, or `0` and inserted into a long-lived cache, one transient failure becomes a persistent bad token card.

## Strict-TDD workflow

Use vertical RED→GREEN cycles:

1. Add a focused test where the first required metadata call fails and the next succeeds. Verify behavioral RED, not merely an undefined helper/import failure.
2. Implement the smallest bounded retry reader.
3. Add a test where the RPC succeeds but returns empty metadata; verify it remains an error after the retry budget.
4. Add a cache test proving incomplete `symbol`, `name`, `decimals`, or `totalSupply` is rejected.
5. Run focused Go race tests with shuffle/repetition, then affected-package race tests.

## Implementation contract

- Required metadata is an all-or-nothing tuple: `symbol`, `name`, `decimals`, `totalSupply`.
- Preserve errors until the caller can classify/report them; never use display defaults in the data layer.
- Treat empty/malformed output separately from transport errors, but neither is cacheable.
- Retry boundedly (normally two total attempts). No sleeps in unit tests; inject a call seam and return scripted results.
- Populate `TokenInfo` required fields only after the complete tuple succeeds.
- Cache insertion must independently enforce completeness as defense in depth.
- Optional launcher metadata (logo, description, socials, limits) may retain best-effort semantics.
- RPC fallback endpoints belong in the chain/venue registry, not hardcoded in token logic. Let the configured client pool own endpoint selection/failover.

A conservative cache predicate requires trimmed symbol/name to be non-empty and not `?`, decimals to be positive, and total supply to be non-nil and positive. If zero-supply ERC20s are a supported domain case, encode that explicitly in tests before relaxing the predicate.

## Concurrency and workspace integrity

Before editing, snapshot `git status --short`. In shared/parallel worktrees, re-read a file immediately before each patch and search for the helper symbol: another worker may already have created it. Never layer duplicate implementations or claim unrelated diffs.

If no canonical verifier is discoverable, use a temporary script made with `mktemp /tmp/hermes-verify-XXXXXX.sh`, install a cleanup trap, and run:

```sh
go test -race ./internal/trade -run 'Test(TokenInfoCache_|ReadRequiredMetadata_)' -shuffle=on -count=3
go test -race ./internal/venue -count=1
git diff --check -- <scoped paths>
```

Report this precisely as **targeted ad-hoc verification**, not full-suite green.

## Pitfalls

- A compile error is not valid RED. Fix test scaffolding until the assertion fails for the intended behavior.
- Do not silently default `decimals == 0` to 18 for required metadata; it masks an RPC/decoding failure.
- Do not cache first and validate later.
- Do not add fallback URLs unless the client path actually consumes the venue RPC list.
- Do not touch metrics or UI during a metadata reliability fix unless a failing integration test proves they are required.
