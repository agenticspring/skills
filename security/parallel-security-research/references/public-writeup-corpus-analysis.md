# Public Security-Writeup Corpus Analysis

Use this reference when a user asks to analyze many historical disclosures without giving exploit instructions.

## Evidence workflow

1. Parse the exact requested README/table range. Count real data rows; exclude separators and blank rows.
2. For every item, request the listed primary URL first. Record final URL, status, and whether substantive text was obtained.
3. When a publisher page is script/challenge gated, use a text-only reader against that **same primary URL** where policy and tooling allow. Mark this separately from direct access; do not silently call it direct.
4. If the primary is dead, look for a public canonical migration, raw GitHub source, official patch/postmortem, or clearly labeled secondary reproduction. Keep its evidence tier distinct.
5. Derive the root-cause category and broken invariant from source text, commit diffs, or official disclosures. When only title/search snippets survive, mark the row inference-limited and avoid code-level claims.
6. Keep summaries at cause/invariant/remediation-test level. Do not include transaction sequences, payloads, addresses, PoCs, or active exploit steps.

## Recommended row schema

| README line | protocol | stated payout | stated severity | root-cause category | broken invariant | source accessibility |

Accessibility labels:
- **D**: listed primary/resolved canonical page opened with substantive text.
- **R**: listed primary was challenge-gated, but its substantive text was obtained through a reader.
- **G**: listed GitHub primary was retrieved as raw source.
- **S**: primary unavailable; substantive public secondary/canonical migration used.
- **X†**: primary unavailable and only title/index evidence remains; classification is inference-limited.

## Coverage accounting

Report these separately:
- requested data rows / covered rows;
- primary URLs attempted;
- direct-primary substantive texts;
- primary texts via reader;
- raw-primary texts;
- secondary-only entries;
- inference-limited entries.

Do not claim all entries were "opened" if a host returned a challenge page or 404. State the limitation and the fallback used.

## Invariant prompts

Normalize findings into one or more of:
- authorization binds actor, asset owner, and capability;
- accounting conserves assets, shares, liabilities, and signs across all representations;
- state machine transitions are valid, unique, and irreversible only when intended;
- cross-domain/bridge evidence binds canonical data to a unique semantic event;
- oracle/price observations are authenticated, bounded, and atomic;
- liveness paths cannot be permanently blocked by untrusted callbacks, keys, or stale state;
- upgrade and initialization preserve trusted control and recoverability.

## Common source pitfalls

- A post title can be useful for a preliminary category but is not proof of a precise implementation claim.
- A historical repository artifact is not proof that the deployed instance remains vulnerable; verify runtime/deployment evidence for current-state claims.
- Do not conflate a protocol-reported severity with independent severity assessment.
- Preserve payout strings exactly as listed; they may mix tokens, USD, ETH, bonuses, "not paid," or out-of-scope status.
