# Whitebox consensus-pool / event-handling recon

Class-level checklist for large local consensus codebases (Solana Alpenglow votor-style). Not a one-session narrative — use with `parallel-security-research` synthesis gates.

## Architecture probe order

```text
Votes (BLS)
  → sigverify vote_pool (per-rank conflict / duplicate)
  → consensus_pool (VotePool + AggregateAccumulator → certs)
  → SlotStakeCounters (SafeToNotar / SafeToSkip, pending intrawindow)
  → insert_certificate → ParentReadyTracker + Finalized
  → pool service: ProduceWindow, standstill cert refresh, pending STN repair
  → event_handler: try_notar / try_final / try_skip_window (VoteHistory)
  → timer_manager (TimeoutCrashedLeader / Timeout) + standstill scale
  → root_utils set_root
```

### BLS cert-verify / threshold plane

Independent of pool-local stake counters; this is what **accepts** a certificate cluster-wide:

```text
UnverifiedCertificate (wire + shred_version)
  → bls_cert_sigverify (group by CertificateType, future-slot bound, ban on fail)
  → Bank::verify_certificate
       epoch_stakes_from_slot → BLSPubkeyToRankMap
       max_validators = rank_map.len()
       total_stake    = rank_map.total_stake()   // FILTERED, not raw epoch total
  → cert_verify::verify_certificate
       get_vote_payload (primary [, fallback])
       Base2 path: decode must be Base2; Base3 → WrongEncoding
       Base3 path: Base2 accepted as primary-only; Base3 → check_disjoint + multi-msg verify
       collect_pubkeys (iter_ones + rank_map; MissingRank hard-fail)
       side-effect stake sum → verify_stake vs CertificateType::threshold
```

Thresholds (typical Alpenglow):

| Cert type | Threshold |
|---|---|
| Notarize / NotarizeFallback / Finalize / Skip | 60% |
| FinalizeFast | 80% |
| Genesis | GENESIS_VOTE_THRESHOLD (e.g. 82% migration) |

Use exact `Fraction` cross-mul (u128); do not reintroduce f64 threshold bugs.

Key files:

| Layer | Typical path |
|---|---|
| Cert verify entry | `bls-cert-verify/src/cert_verify.rs` |
| Cert types / thresholds | `votor-messages/src/certificate.rs` |
| Payload + wire decode | `votor-messages/src/unverified_vote_message.rs`, `wire.rs` |
| Fraction | `votor-messages/src/fraction.rs` |
| Bank wiring | `runtime/src/bank.rs` (`verify_certificate`) |
| Rank map / exclusion | `runtime/src/epoch_stakes.rs` (`BLSPubkeyToRankMap::new`) |
| Cert sigverify + ban | `bls-sigverify/src/bls_cert_sigverify.rs`, `bls_sigverifier.rs` |
| Vote conflict filter | `bls-sigverify/src/vote_pool.rs` |
| Local cert build | `votor/src/aggregate_accumulator.rs`, `consensus_pool/vote_pool.rs` |
| Genesis threshold | `votor-messages/src/migration.rs` |

### Reward-certificate / vote-reward / Tower→AG migration plane

Separate from consensus Safety, but same checkout and same accumulator class:

```text
Notar/Skip votes (Finalize/Genesis excluded)
  → bls-sigverify rewards_wants_vote (leader window: vote_slot+NUM_SLOTS_FOR_REWARD)
  → CertsBuilder PartialCert / NotarEntry (max-stake block_id)
  → footer: SkipRewardCertificate + NotarRewardCertificate (base2 only)
  → ValidatedRewardCert (slot == bank−8, BLS base2, HashSet union signers)
  → calc_vote_rewards_update_vote_states (stake-weighted half split + leader)
  → vote-account epoch_credits (+ AG_MIGRATION_EPOCH_CREDIT marker)
  → next-epoch PER (points.rs tower / migration / alpenglow)
```

Migration control plane (liveness / accounting, not pool Safety):

```text
FF activate (rooted) → MigrationStatus::Migration (migration_slot = FF+offset)
  → VoM, no OC/root report ≥ migration_slot
  → super-OC discovery → genesis vote/cert → ReadyToEnable → Poh off → AlpenglowEnabled
  → bank stores GenesisCert; get_alpenglow_migration_slot() == genesis.block.slot
  → FullAlpenglowEpoch after root in new epoch
```

Key files (agave-class):

| Layer | Typical path |
|---|---|
| Wire reward certs | `votor-messages/src/reward_certificate.rs` (`NUM_SLOTS_FOR_REWARD=8`) |
| Migration phases | `votor-messages/src/migration.rs` (`AG_MIGRATION_EPOCH_CREDIT`, thresholds) |
| Leader filter | `bls-sigverify/src/rewards.rs` |
| Accumulator | `votor/src/aggregate_accumulator.rs` |
| Cert builder | `core/.../rewards/certs_builder/**` |
| Leader footer | `core/src/block_creation_loop.rs` |
| Replay admit | `runtime/src/validated_reward_certificate.rs` |
| Credit path | `runtime/.../vote_reward.rs` + `epoch_inflation_account_state.rs` |
| PER / points | `runtime/src/inflation_rewards/{mod,points}.rs` |
| VAT / rank map | `runtime/src/bank.rs` (`MAX_ALPENGLOW_VOTE_ACCOUNTS`, burn VAT) |
| Epoch type | `runtime/src/alpenglow_epoch_type.rs` |

## High-yield hunt classes

| Class | What to read | Typical bug shape |
|---|---|---|
| Leader production | ParentReady batching, `highest_parent_ready` bookkeeping | Only max ParentReady processed; intermediate leader windows skipped forever |
| MissedWindow predicate | Cascade loops that advance highest for every connected slot | `highest > slot` treated as “already certified” when only skip-connected |
| Stake thresholds (pool) | Accumulator own-path vs external-path | Own rejects duplicate ranks; External `ranks \|=` + full stake add → double-count |
| Stake thresholds (verify) | `verify_stake` + `rank_map.total_stake()` | Denominator is **filtered** unique BLS+identity set; unauthenticated `node_pubkey` collision can eject honest stake and amplify adversary fraction |
| Rank-map admission | `BLSPubkeyToRankMap::new` filter | Duplicate BLS (PoP-bound) or duplicate `node_pubkey` (not PoP-bound) drops both; total_stake = survivors only |
| Base2/base3 certs | Primary+fallback stake sum vs cert-verify disjoint | Local build may sum without local disjoint; verify path enforces `check_disjoint` |
| Encoding looseness | `verify_base3` accepts Base2 | Dual-source cert types (NF/Skip) verified primary-only if Base2 encoded — often intentional post fallback-only fix |
| Cert ban attribution | `handle_cert_verify_error` + blockstore path | Failed cert bans attributed sender; blockstore attributes **carrier slot leader**, not cert producer → leader DoS |
| Fallback caps | sigverify max NF entries vs parent-ready max NF blocks | Constant skew (e.g. 3 vs 4) → honest 4th NF Invalid + ban |
| Intrawindow STN | Pending queue until parent NF or finalized | Sticky pending + short poll loop without timeout escape |
| Standstill / timers | First arm vs re-arm; what standstill scales | `or_insert` freezes first timeout; standstill only scales future arms |
| Root safety | Finalized + voted + frozen + block_id match | Finalize without notar must not root; bank-hash mismatch must hard-fail |
| Vote history | Notarize/Skip/Finalize assert gates | Skip insert without uniqueness assert is only safe if callers always gate `voted` |
| Reward cert builder selection | `NotarEntry::build_cert` sorts by `partial.stake()`; `add_aggregate` stake | Overlapping External aggregates inflate stake → wrong `block_id` packed; honest majority under-rewarded (bitmap OR, not double-pay) |
| Per-slot reward denominator | `EpochInflationState.slots_per_epoch` vs `get_slots_in_epoch` | Warmup: inflation budget uses short epoch length, divide uses fixed `slots_per_epoch` → underpay |
| Inflation account availability | Created only in `process_new_epoch` if alpenglow | Mid-epoch FF activate + AG blocks with reward certs before next boundary → hard-fail footer |
| Migration slot semantics | `get_alpenglow_migration_slot` vs `MigrationStatus.migration_slot` | Bank helper is **genesis slot**, not FF+offset VoM start; tower/AG slot counts key off genesis |
| Credit epoch vs marker | `increment_credits` uses **processing** bank epoch; marker only if `epoch == migration_epoch` | Reward slot in migration epoch, `+8` after boundary → marker may never land; PER classifies pre-marker as tower |
| VAT / rank-map exclusion | `clone_and_filter_for_vat` then burn | By design certs cannot name excluded ranks; not LoF unless filter/rank desync |

## Candidate template (ledger row)

```text
id: C-<AREA>-N   # or BC*/VP*/RW* when parallel workers share one ledger
title:
class: Funds | Safety | Liveness | DoS
confidence: low|med|high
files: path:line
root_cause_hyp:
attacker_model: (stake? asynchrony? crash? permissionless vote account?)
preconditions:
why_novel: (vs public issue #…)
falsify_plan:
repro_plan_local:
gate_passed: no until evidence
status: candidate|rejected|promoted
```

## Dedup baseline habits (Alpenglow / agave)

Before promoting, search open+closed consensus issues for siblings of:

- Event-channel deadlock / full channel stalls
- Standstill highest-finalized slot selection
- Chained merkle / dead-mark races (repair/replay, not pool STN)
- Reward certs by **count vs stake** on payout (`#13235` class) — payout path is stake-weighted; residual may be **builder stake selection**, not payout math
- Base3 fallback-only certs (`#13516` class) — residual may be Base2-on-dual-type acceptance, not empty-primary
- BLS certificate verification mega-threads (`#13792` class) — residual may be rank-map denominator / ban attribution, not empty bitmap
- Genesis conflicting votes / migration finalization not advancing (`#12925`, `#13795` class)
- Per-signature subgroup skip during vote aggregation (`#12943` class) — known TODO, not novel
- Intra-batch banlist reevaluation (`#13920` class) — residual may be **leader attribution** on cert fail, not vote reevaluation
- Pending reward drop across migration (`#13103` class)
- Leader omits own vote from reward aggregate (`#13790` class)
- Warmup epoch length bugs adjacent to closed `#13420` — check residual field choice (`slots_per_epoch` stored vs `get_slots_in_epoch`)

Public = usually OOS for payout; hunt residual/novel mechanisms, not rewrites of known titles.

## Dead-end patterns (do not re-file without new path)

- Empty bitmap / zero signers accepted as valid cert
- Base3 bitmap for pure Notarize/Finalize accepted as Base2
- Primary∩fallback bitmap overlap accepted
- Missing rank silently skipped in stake sum
- Oversized bitmap OOB panic without Decode error
- f64 threshold precision loss when `Fraction` cross-mul is in use
- Bank cert path using unfiltered `VersionedEpochStakes::total_stake` when it already uses `rank_map.total_stake()`
- BLS pubkey copy grief excluding honest stake when PoP is required on BLS set (node_pubkey grief is different)
- Tampered bitmap inflate stake when aggregate sig verify fails
- Conflicting Notarize two blocks/slot under honest majority when sigverify rejects double notar per rank
- Finalize rooting without Notarize when insert path only emits Finalized if notar cert present
- “Safe-to-skip ignores fallback” when primary Notarize/Skip already feed counters
- Root without vote when rootable check requires `vote_history.voted(slot)`
- Skip∩Notar same validator double-pay when `ValidatedRewardCert` uses `HashSet` of signers
- Leader-supplied `validators` list mismatch when replay re-verifies bitmaps via rank map
- Commission > 100% when code clamps bps and AG uses preserve-lamports split
- Genesis votes earning rewards when `rewards_wants_vote` excludes Finalize/Genesis/fallbacks
- Identity aggregate as free cert when builder omits identity signatures intentionally
- VAT-excluded validators “missing” from cert when rank map is post-VAT by design

## Verification order preference

1. Rank-map denominator grief (`node_pubkey` collision) if VAT/vote-program allows foreign identity — Safety
2. Leader ProduceWindow + MissedWindow (liveness, often unit-testable without full cluster)
3. Pure accumulator stake unit test (minutes) — only promote Safety if External overlap is reachable past sigverify
4. Fallback constant skew (sigverify max NF entries vs parent-ready max) — ban on honest 4th NF
5. Cert fail ban attribution (network vs blockstore leader) — DoS/liveness
6. Timer re-arm under standstill
7. Pending STN sticky — confirm protocol intent (required parent NF forever vs missing escape hatch)
8. Encoding looseness (Base2 on NF/Skip) — only if protocol forbids primary-only NF
9. Reward builder: overlapping External aggregates → assert packed `block_id` + validator set vs stake-correct majority
10. Warmup schedule: one full-stake voter; compare `calculate_reward` vs `max_possible / get_slots_in_epoch(e)`
11. Mid-epoch alpenglow activation: reward cert before next `process_new_epoch` → footer error vs silent skip
12. Migration credit delay: last slots of migration epoch as reward_slots; inspect `epoch_credits` for missing `AG_MIGRATION_EPOCH_CREDIT`

## Parallel worker merge discipline

When multiple leaf agents write recon on one checkout:

1. Namespace candidate IDs by plane: `BC` (bls-cert/thresholds), `VP` (votor pool/events), `RW` (rewards/migration).
2. Parent or last writer **reads** existing `notes/03-candidates.md` and deep recon files before rewriting.
3. Prefer append/merge over full overwrite; if overwrite is needed, preserve sibling rows.
4. Cross-link deep notes (`04-*-recon.md`) from the ledger; do not duplicate long prose in the ledger.

## Reporting discipline

- Cite exact commit; re-check unfixed on master at submit time
- Rank Safety > Liveness > DoS; for rewards plane rank **LoF/accounting > liveness > pure underpay dust**
- One finding per report; PoC required before GHSA
- Keep `notes/0N-*.md`: scope, recon, candidates ledger, deep recon writeup
- Deliverable shape for pure static recon: **surface map table → top N novel candidates (file:line / attacker model / impact class / novelty / falsify) → dead-ends table → done line**. Avoid re-litigating fixed public issues as findings.
