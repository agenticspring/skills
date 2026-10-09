---
name: parallel-security-research
description: "Run exploitability-driven security research with parallel specialist agents, safe PoCs, scope gates, and evidence-backed synthesis."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [security, research, web3, bug-bounty, delegation, parallel]
---

# Parallel Security Research

Use this class-level workflow for authorized security reviews, Web3 bug-bounty work, and exploitability analysis where independent perspectives improve coverage.

## Core rule

Do not call a finding high or critical without a concrete attack path, affected asset, realistic attacker capability, and reproducible evidence. Keep production systems safe: use source review, local fixtures, testnets, forks, dry-runs, or static proofs. Never send destructive exploit transactions to mainnet or third-party systems.

## Pre-flight

1. Load the most relevant security/audit skill and any target-specific skill.
2. Search session history for prior attempts, failures, and known workarounds.
3. Define the target, authorization, chain/environment, exact scope, exclusions, and reporting channel.
4. Verify live program scope before testing a bug-bounty target: addresses, chain IDs, versions, PoC requirement, KYC/payout constraints, duplicate policy, and out-of-scope impacts.
5. Record the objective and constraints in the durable project note before parallel work starts.

## Public writeup-corpus research

When reviewing a public disclosure list rather than a live target, treat every list row as a coverage unit and read the linked primary source before categorizing its cause. Use a source-access ladder: original linked source → canonical publisher mirror/migration → moved canonical repository/report → official retrospective or fix record. Do not substitute a search snippet for full technical evidence.

Keep four exclusive access buckets: direct original source, canonical replacement source, limited content, and unavailable content. If a text reader obtains substantive content from the original linked URL after the host blocks ordinary retrieval, record it as **reader-mediated primary**, never as direct-primary access. Final reporting must give both (a) total rows accounted for and (b) the material-source count (`direct + replacement`); label missing evidence rather than guessing. Use a structured table with line, protocol, payout, stated severity, root-cause category, broken invariant, and source accessibility. Abstract exploit mechanics into defensive invariants and audit heuristics; do not provide active exploit steps, target-specific execution commands, private keys, or live-target transaction recipes.

### SPA migrations and mapping-audit discipline

A publisher migration can make every `/blog/<slug>` URL return the same successful SPA shell. A 200 response, shared page title, or large JS bundle is **not** article retrieval. Verify that an item-specific title, publication metadata, and substantive body were returned. Inspect the public bundle only read-only to identify its published data route; request the listing route and the per-slug route separately. Treat an item result of JSON `null` as a non-migrated post, then continue the source ladder with the exact legacy canonical URL and Wayback CDX → timestamped `id_` replay.

When auditing a proposed README/PR link repair, compare raw base and PR-head rows by their stable table identity and exact old/new URL, not protocol name alone. Protocol labels can repeat; detect URL swaps and duplicate assignments separately. Report (1) an actual mapping error in an auxiliary mapping artifact, (2) an error in the submitted PR head, and (3) a deliberate duplicate in corpus data as distinct outcomes.

For a reusable extraction template and evidence rules, read `references/source-access-and-coverage.md` and `references/public-writeup-corpus-analysis.md`. For exhaustive, machine-readable root-cause taxonomy, read `references/evidence-identity-and-taxonomy-audit.md` before assigning any category: it requires exact incident identity matching, an explicit `unverified metadata/title only` bucket, and coverage invariants. For the SPA/API, CDX replay, and PR mapping pattern established in a TrustSec migration, also read `references/spa-migration-and-pr-link-audit.md`. The former contains concrete retrieval fallbacks for moved, gated, archived, forum, GitHub, and social-shortlink sources; a social post that only exposes a short-link or login wall is not substantive technical access.

## Parallel orchestration modes

### Native team mode

If the target runtime exposes `team_*` tools, use the security-research team workflow with three hunters and two PoC engineers. Confirm the team is actually created and members return evidence; never claim team execution from configuration alone.

### Hermes delegation fallback

If `team_*` is unavailable but Hermes delegation is enabled, use a batch of up to three independent leaf agents. Do not pretend this is native Team Mode. Assign non-overlapping roles:

- **Surface/proxy hunter:** map contracts, entry points, trust boundaries, proxy slots, upgrade paths, privileged roles, and external calls.
- **State/accounting hunter:** derive invariants for balances, shares, assets, pricing, withdrawals, rewards, messages, and replay protection.
- **Exploitability/falsification hunter:** test candidate paths with local or forked fixtures, search exclusions, and try to disprove speculative findings.

Give every child the same scope, target addresses, safety limits, and required output schema. Children must not edit the same files. The orchestrator deduplicates, cross-checks, and owns the final report.

Recommended output schema per child:

```text
candidate title
affected contract/file/function
attacker capability
attack path
preconditions
impact and affected asset
CWE/severity candidate
exact evidence
safe verification or PoC
confidence
``` 

## Synthesis gate

After parallel results:

1. Normalize and deduplicate candidates by root cause.
2. Reject generic hardening advice and findings outside scope.
3. Check every surviving candidate against the attack path, impact, and evidence requirements.
4. Reproduce only the strongest candidates using a safe local method.
5. Ask whether the candidate depends on privileged access, leaked credentials, basic economic behavior, lack of liquidity, external depeg, or another explicit exclusion.
6. Downgrade or remove anything not reproduced.
7. Save the verified result and residual risks to the durable project note and update the session index.

## Bug-bounty report format

```markdown
## Security Research Result
### Verdict
PASS | PASS WITH FINDINGS | BLOCK
### Scope
- Target:
- Chain/deployment:
- Program scope and exclusions:
- Commands/tests run:
### Findings
| Severity | Title | Asset | Attack path | Evidence | PoC | Fix |
|---|---|---|---|---|---|---|
### Finding details
- Preconditions:
- Root cause:
- Reproduction:
- Impact:
- Severity rationale:
- Minimal remediation:
- Regression test:
### Rejected candidates
| Candidate | Reason rejected/downgraded |
|---|---|
### Residual risk
```

## Durable notes

For complex reviews, maintain a target note containing objective, scope snapshot, target addresses, roles assigned, candidate findings, verification results, failures/pitfalls, and next action. Update the session index at start, on scope/decision changes, on blockers, and before completion. Verify note writes by reading them back. Never store secrets or raw credentials in notes.

## Whitebox consensus / event-loop recon (Alpenglow-class)

When the target is a large local consensus codebase (vote pools, certificates, parent-ready, standstill, timers) rather than on-chain contracts:

1. **Pin commit first** (`git rev-parse HEAD`) and map the file surface before deep reads.
2. **Trace data-plane order:** network votes → sigverify / rank dedupe → pool stake counters → certificate insert → parent-ready / events → voting history gates → rooting / timers.
3. **If scope includes BLS cert verify / thresholds:** also trace cert plane (`UnverifiedCertificate` → bank rank_map → `verify_certificate` base2/base3 + stake fraction → banlist attribution). See checklist section *BLS cert-verify / threshold plane*.
4. **If scope includes rewards/migration:** also trace reward-cert plane (vote filter → CertsBuilder → ValidatedRewardCert → vote_reward credits → PER) and migration phases (FF → VoM → genesis → AlpenglowEnabled). Treat `get_alpenglow_migration_slot()` as **genesis slot**, not FF+offset.
5. **Rank candidates Safety > Liveness > DoS** (consensus). On rewards plane: LoF/accounting > liveness (footer hard-fail) > dust underpay. Prefer invariant breaks over style/hardening.
6. **Cross-check public tracker before promoting** (open + closed mega-threads). Mark public-adjacent siblings as OOS for payout unless residual/novel (e.g. payout count-vs-stake fixed ≠ builder stake-selection residual; empty/tampered bitmap / base3-fallback-only fixed ≠ rank-map denominator grief residual).
7. **Separate latent vs reachable:** e.g. stake double-count in an accumulator is only Safety if an unfiltered External path exists; otherwise label defense-in-depth until the bypass is shown. Same rule for reward-builder stake inflation and base2-on-dual-type cert encoding looseness.
8. **Falsify each candidate** with a unit-level plan (ParentReady batch, overlapping ranks, sticky pending set, timer re-arm, rank-map node_pubkey collision, base3 encoding, ban attribution, warmup denominator, mid-epoch FF + reward cert) before any GHSA language.
9. **Write durable artifacts:** surface map, ranked candidates with file:line evidence, dead-ends table, verification order. Keep a candidates ledger separate from long recon prose. Static recon deliverable: surface map → top N novel candidates → dead-ends → done.
10. **Parallel workers on one checkout:** merge ledgers with namespaced IDs (`BC*` cert-verify, `VP*` votor-pool, `RW*` rewards). Read existing `notes/03-candidates.md` before rewrite; never clobber a sibling worker's ledger with a full overwrite.

Session checklist and hunt classes (pool + BLS cert-verify + reward/migration): `references/whitebox-consensus-pool-recon.md`.

## Pitfalls

- Configuration that mentions Team Mode does not prove `team_*` tools are loaded; verify tool availability and actual team creation.
- Parallel agents are not automatically coordinated. Use explicit role boundaries and a synthesis gate.
- Do not let multiple workers edit the same report or source tree unless isolated worktrees are used.
- A proxy address and its implementation are separate audit surfaces; verify upgrade authority and initializer state.
- A theoretical loss, price movement, or centralization concern is not automatically a bounty-valid vulnerability.
- In a corpus, a matching protocol name is not corroboration. Match the row's exact source URL or uniquely reconciled incident identity before transferring SCV/official evidence.
- If an archived social post only reveals an external short-link, a title, or login shell, retain it as metadata-only rather than deriving a technical category.
- “Submitted” or “reproduced” is not evidence unless the output, fixture, trace, or transaction simulation is captured.
- For consensus whitebox recon: do not promote Safety from accumulator double-count without proving a path past sigverify rank uniqueness; do not re-file public standstill/channel-deadlock titles without a residual mechanism.
- For BLS cert-verify recon: do not re-file empty bitmap, Base3-on-Notarize WrongEncoding, BitmapOverlap, MissingRank, or fixed base3-fallback-only (#13516) without a residual; distinguish **filtered** `rank_map.total_stake()` from raw epoch total; treat unauthenticated identity/node_pubkey exclusion as a Safety hyp only after VAT/vote-program falsify; ban-on-fail DoS needs correct attribution model (network sender vs carrier slot leader).
- For reward-cert recon: do not re-file payout count-vs-stake, pending reward drop, migration finalization, or leader-own-vote omissions without a residual mechanism; distinguish builder selection stake inflation from payout math; do not treat VAT exclusion or intentional identity-aggregate drop as LoF.
- Parallel workers: never overwrite a shared candidates ledger without reading sibling content first; namespace IDs by plane.
