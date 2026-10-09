# Alpenglow Bug Bounty — program card (verified 2026-08-01)

Resume reference for the Anza Alpenglow consensus bug bounty. Full source of
truth: `https://github.com/anza-xyz/alpenglow` README.md + RULES.md (read live
before any submission — rules may change).

## Program facts

```text
Prize pool:        up to 50,000 SOL (unlocks by highest valid severity)
Window:            2026-08-05 16:00 UTC → 2026-08-19 16:00 UTC (2 weeks)
Adjudication:      2026-09-02, lump-sum after KYC, 12-month locked SOL
Submit channel:    GitHub Security Advisory on anza-xyz/alpenglow (one finding/advisory)
Code under review: anza-xyz/agave master (MOVING window — cite exact commit)
GH identity:       agenticspring (GITHUB_TOKEN_2)
Local workdir:     /root/alpenglow-bb (scope receipt, recon notes, candidates ledger)
```

## Severity → pool unlock + award ranges

| Highest valid finding | Pool | Per-finding award |
|---|---|---|
| Loss of Funds | 50,000 SOL | 6,250–25,000 |
| Consensus / Safety | 30,000 SOL | 3,125–12,500 |
| Liveness / LoA | 20,000 SOL | 1,250–5,000 |
| DoS / Other only | 10,000 SOL | 315–1,250 / discretionary |

## Scope (Alpenglow-specific only)

Core crates: `votor/`, `votor-messages/` (incl `migration.rs`), `bls-sigverify/`,
`bls-cert-verify/`. Integration: cluster_info_vote_listener, block_creation_loop
rewards, validated_reward_certificate, validated_block_finalization, epoch_stakes,
block_component_processor(+vote_reward), entry block_component,
alpenglow_epoch_type, bank VAT, bank_forks, repair block-id, replay_stage(+update_parent),
blockstore_processor UpdateParent, turbine retransmit FirstShred, window_service.

Features active for relevance: `alpenglow` (SIMD-0326), `alpenglow_fast_leader_handover`
(SIMD-0337), validator-admission (SIMD-0357), TowerBFT→Alpenglow migration.
Paths only reachable with `alpenglow` inactive = TowerBFT = out of scope.

## PvP / duplicate rules (critical)

- First GHSA timestamp wins at **assessed** severity (not claimed).
- Finding must be reproduced at cited commit AND still unfixed on master at submit.
- Same root cause / single fix = duplicate → later reports unpaid.
- PoC required for all severities (local fork / multi-node harness / sim only —
  never mainnet/public testnet). Argument-only accepted only with Foundation sign-off.
- No public disclosure before fix ships (public = ineligible).
- Known-issue baseline: agave issues labeled `blocking-ag` / `consensus-team` +
  anything public. Check before writing any candidate up.

## Recon state (2026-08-01, paused by user)

- Sparse agave checkout at HEAD `132ac3296e5e917701e0111180388ae872747680`
  (votor / votor-messages / bls-sigverify / bls-cert-verify / core / runtime /
  entry / ledger / turbine).
- 3-worker parallel recon complete (deleg_d9d526be): **0 gate-passed bugs**;
  ~12 candidates ranked in `/root/alpenglow-bb/notes/03-candidates.md`.
- Top candidates: BC1 (node_pubkey rank-map denominator shrink → Safety),
  VP1+VP2 (ProduceWindow max-only + MissedWindow overshoot → Liveness),
  RW1 (aggregate stake inflate → reward block_id bias), BC4 (invalid cert bans
  carrier leader), VP5 (timer first-arm sticky).
- Resume = falsify BC1 first (write local test on rank_map exclusion filter vs
  vote-init authorization), then VP1/VP2 unit tests.
- Skills in play: `tempest` (Hermes-native harness) + this orchestration skill.

## Workflow reminders

- Load `tempest` + this skill; read `notes/01-scope-receipt.md` and
  `notes/02-recon-notes.md` before touching code.
- Whitebox / local sim only; no broadcast; no public GH issues with exploit detail.
- Evidence gate before any GHSA: tool-backed repro at cited commit.
