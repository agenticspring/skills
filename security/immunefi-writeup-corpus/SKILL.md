---
name: immunefi-writeup-corpus
description: "Use when analyzing Immunefi writeup lists exhaustively."
version: 1.0.0
author: spring
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [security, web3, immunefi, bug-bounty, research, source-validation]
---

# Immunefi Writeup Corpus Research

Use this skill when Dez asks to study an Immunefi/Web3 public writeup list thoroughly, derive defensive audit knowledge, or validate a curation repository before using it as security evidence.

## Scope and safety

- This is **public historical-disclosure analysis**, not permission to test live targets.
- Keep output at root-cause, broken-invariant, remediation-test, and audit-heuristic level.
- Do not provide active exploit recipes, private credentials, target-specific attack steps, or broadcast transactions.
- Do not label a historical pattern as a live finding. A real target review still requires current scope, deployed version, accepted impact, exclusions, and safe local/fork/testnet verification.

## Proven result: `sayan011/Immunefi-bug-bounty-writeups-list`

Pinned study revision:

```text
b8277a4a55d21e7b49fb268d8f1e56ce0720bb6e
```

Verified repository shape:

```text
1 tracked file: README.md
147 non-empty table entries (README lines 11–158; line 38 blank)
146 distinct writeup URLs
```

Final evidence coverage for that exact pin:

```text
D direct substantive:                59
R reader-mediated original:          15
C canonical/raw/API replacement:     42
A archived primary:                  16
---------------------------------------
Substantive technical bodies:       132

P partial:                            6
I index/ambiguous:                    3
X social/title-only:                  6
---------------------------------------
Limited, no code-level claim:        15
```

Research artifacts are local-only:

```text
/root/.hermes/research/immunefi-writeups-20260730/
```

Read first when resuming this exact corpus:

```text
SYNTHESIS.md
entry-taxonomy-v1.md
entry-evidence-matrix-v3.json
source-access-ledger-v3.md
verify-evidence-matrix.json
verify-source-access-v3.json
```

## Required workflow

### 1. Pin and inventory

1. Clone read-only or inspect the supplied repository.
2. Record the immutable commit SHA.
3. List tracked files and parse only real data rows—exclude Markdown separators and blanks.
4. Preserve every row as a coverage unit:

```text
README line | protocol label | payout as listed | severity as listed | original URL
```

5. Keep raw payout/severity as attribution metadata. Do not normalize or aggregate them without an explicit method.

### 2. Source-access ladder

For each row, use this order:

```text
original linked source
→ reader against the exact original URL if ordinary access is gated
→ current official/publisher migration
→ canonical repository, advisory, forum, fix record, or raw report
→ Wayback CDX lookup and timestamped id_ replay
→ partial/index/social-only label if substantive body cannot be obtained
```

Use one exclusive evidence label per row:

```text
D = direct substantive source
R = reader-mediated original source
C = canonical replacement/raw report/publisher API
A = archived historical source
P = partial source
I = index/ambiguous source
G = gated/unavailable source
X = inference-limited social/title-only source
```

Never classify a title, payout, severity, HTTP 200, search snippet, generic homepage, or social teaser as full technical evidence.

### 3. SPA migration pitfall — TrustSec lesson

A migration may make all paths return:

```text
HTTP 200
same generic page title
large JavaScript bundle
```

That is an **application shell**, not proof the article was retrieved.

For the Trust Security migration in this corpus:

1. Old `www.trust-security.xyz/post/...` routes were retired.
2. `trustsec.xyz/blog/<slug>` rendered the same generic SPA shell.
3. The public read-only tRPC routes contained the actual articles:

```text
/api/trpc/blog.list
/api/trpc/blog.getBySlug
```

4. Promote a migrated page only when all are true:
   - slug/listing resolves to an item-specific result;
   - title matches the historical incident;
   - substantive body is present;
   - source and body are locally archived.
5. If API returns JSON `null`, continue with exact legacy URL → CDX → timestamped `id_` Wayback replay.

Successful TrustSec body recoveries in this pin include Fluidity, Oasis, Fringe, O3, Permission Denied, LayerZero Parts 2/3, and RAI.

### 4. Audit curation PRs correctly

When auditing an unmerged README link-repair PR:

- Compare base and PR-head rows using stable table identity and exact old/new URLs.
- **Never join rows by protocol label alone**—the same protocol may appear multiple times.
- Separate these outcomes:

```text
actual error in helper/mapping artifact
actual error in submitted PR head
intentional duplicate source URL for distinct issues
```

In the studied repo, PR #22 was unmerged. A previous name-based helper falsely reported Iron Bank/Brahma duplicate mappings; raw PR head retained their distinct URLs. Record and correct analysis errors explicitly.

### 5. Derive only defensive invariants

For every row with a substantive body, derive:

```text
root-cause category
broken invariant
one regression/audit heuristic
source authority and URL
```

Core invariant families observed in the pinned corpus:

1. **Accounting/conservation/units** — assets, shares, debt, collateral, rewards, fees, signs, and rounding stay coherent.
2. **Liveness/governance/state machine** — valid transitions progress; queues, claims, callbacks, retries, and validator work cannot be permanently blocked.
3. **External interaction/oracle/ordering** — prices, callbacks, router state, allowance, and transaction ordering cannot alter settlement semantics.
4. **Cross-domain/proof/consensus** — source event, domain, nonce, proof, message, recipient, and final settlement bind exactly once.
5. **Authorization/capability/token semantics** — caller, owner, spender, target, selector, value, and lifecycle all bind as intended.
6. **Initialization/upgrade/execution context** — implementations are locked; upgrades and delegated execution preserve critical state/authority.
7. **Historical deployment verification** — an article/repository is not a live vulnerability without matching active bytecode, version, and scope.

### 6. Required completion gate

Before reporting complete:

```text
all parsed rows appear exactly once in the evidence matrix
D + R + C + A + P + I + G + X = total rows
all full-body rows have an existing local source artifact/provenance
all P/I/G/X rows have no invented code-level root cause
raw corpus worktree remains unmodified
```

## Reusable audit prompt

For an authorized target, start with the surface:

```text
bridge | lending/vault | AMM/router | staking/rewards | governance | L1/L2/consensus
```

Then write and test the relevant properties locally:

```text
authorization binds capability
accounting conserves value
claims/messages/actions are exact-once
cross-domain evidence has one canonical meaning
external price/callback state is bounded and atomic
upgrade/initialization preserves recovery and control
```

## Pitfalls

- `Critical` in a curated table is not an independent severity assessment.
- Payouts may be token-denominated, composite, unpaid, rejected, duplicated, or absent.
- One post may document multiple distinct issues; URL count is not issue count.
- A 403 from Medium is access-gating, not proof the article no longer exists.
- A 200 SPA page is not content retrieval.
- Do not report a historical case as current until deployed code, scope, and exploitability are verified safely.
