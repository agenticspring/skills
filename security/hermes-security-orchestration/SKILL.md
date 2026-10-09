---
name: hermes-security-orchestration
description: Orchestrate scope-controlled Web3 and application security research in Hermes using bounded parallel delegate_task workers, durable artifacts, and evidence-gated reporting.
version: 1.0.0
category: security
---

# Hermes Security Orchestration

Use this skill when Dez asks for an OMOP-style full scan, parallel security review, bug-bounty research, or multi-agent vulnerability investigation in Hermes.

## Core model

Hermes is the **only runtime and team coordinator**. The deterministic scan engine owns scope parsing, phase state, artifacts, and report rendering. Hermes owns reasoning, worker delegation, deduplication, reproduction, and final severity decisions.

The canonical team backend is Hermes `delegate_task(tasks=[...])`, bounded by the configured child limit (normally three workers per batch). Workers are isolated leaf agents; the parent reconciles their reports. Do not invoke, require, or imply an OpenCode runtime, `team_*` tools, `team_mode`, mailbox lifecycle, or OpenCode-specific agents/packages for this workflow. Call it a **parallel Hermes security audit**, not OMOP Team Mode.

## Preflight

1. Load the relevant security and Web3 skills.
2. Query session history for prior target-specific decisions and failures.
3. Read the relevant Obsidian notes when resuming or after compaction.
4. Confirm target, chain/contract, authorization, scope, rules of engagement, and allowed testing mode.
5. For Immunefi, read the live program scope, impact table, exclusions, PoC requirement, duplicate policy, and payout/KYC terms.
6. Default to passive analysis and local fork/testnet simulation for third-party targets. Never send destructive exploit transactions to mainnet.

For the Anza Alpenglow consensus bounty (or resuming its archived harness), use
`references/alpenglow-bug-bounty.md` — program card with window, severity→pool
table, scope crates, duplicate policy, and the paused recon state.

## Parallel worker design

Use one `delegate_task(tasks=[...])` batch with at most three independent workers. Give every worker the same scope and safety constraints, but a distinct role:

- `surface-recon`: map assets, entry points, proxy/implementation relationships, trust boundaries, external calls, and privileged selectors.
- `auth-accounting`: analyze authorization, upgradeability, initialization, ERC-4626/share accounting, state transitions, and invariants.
- `integration-falsification`: inspect oracle/bridge/message/token integrations and actively try to falsify candidate attack paths using local fixtures or fork simulation.

Workers are leaf agents. They cannot coordinate directly. The parent must merge their reports and request a second pass only for concrete candidates.

## Required worker output

Each worker returns:

- exact asset/file/function/address
- attacker capability and prerequisites
- step-by-step attack path
- expected impact
- CWE or vulnerability class when applicable
- evidence and commands/tests used
- safe reproduction or reason reproduction is unsafe
- confidence and likely scope status

Generic hardening advice is not a finding.

## Verification gate

Before recording or reporting a vulnerability:

1. Deduplicate overlapping reports.
2. Confirm the asset is in scope and the claimed impact is accepted.
3. Reproduce with a local fixture, Anvil fork, testnet, static proof, or dry run.
4. Check access control, existing mitigations, slippage/rounding assumptions, and realistic prerequisites.
5. Try to falsify the finding.
6. Record only verified findings; label unresolved candidates separately.

No severity without a concrete attack path. No Critical/High label without demonstrated impact and realistic exploit preconditions. Never fabricate a PoC, transaction hash, reward, or exploit result.

## Durable state

Keep deterministic artifacts under `.omop/engagement/` and update the local Obsidian vault for complex work. Record objective, constraints, scope, decisions, worker outputs, verified results, rejected candidates, pitfalls, and next steps. Update the session index before completion. Never place credentials, private keys, API keys, or tokens in artifacts, Obsidian, or memory.

## Hermes adapter reference

The repository adapter writes a worker plan rather than spawning workers itself. Use the plan as input to the parent Hermes `delegate_task` call. See `references/hermes-adapter.md` for the exact contract and reconciliation pattern. For passive Web3 launch/RPC checks, use `references/passive-mainnet-rpc-verification.md`. Separate registry metadata from live evidence: verify official docs/repo, inspect chain-registry `rpc`/status fields, and use only published endpoints with read-only `eth_chainId`, `net_version`, and `eth_blockNumber` checks. A chain entry with `rpc: []` and `status: incubating` is not proof of deployment or a leaked RPC; compare candidate IDs against the known testnet and record block numbers as time-bound evidence.

## Skill and tool availability

Do not claim that the full bundle is active merely because it exists in the repository. After installing the Hermes package, verify the root skill, the count of installed `SKILL.md` files, and the actual tool binaries separately. Use `omop skills` for the bundled playbooks and `omop-tools` for the tool inventory/version check. A catalog or source directory is not an installed executable. The current bundle inventory is 240 playbooks and 109 catalog tool entries; those numbers are documentation counts, not installed-binary counts. `omop-tools` must enumerate the whole catalog and report available, missing, failed, and manual/unsupported entries explicitly. Missing third-party tools must be installed through the secure-tool-install pipeline; never silently download or overwrite them from the OMOP installer. Treat the repository's portable installer as profile-safe: use `${HERMES_HOME:-$HOME/.hermes}` and `${OMOP_PREFIX:-$HOME/.local}`, never `/root` or `/usr/local/bin` assumptions.

For repeatable setup, use the repository's one-click installer only with explicit local confirmation; it installs the CLI and all bundled skills, attempts catalog recipes without stopping on one failure, and writes a final status report. Never report 109/109 merely because the installer completed: verify the final inventory. If a mass-install run becomes dependency-heavy or stalls, stop it, preserve the log, and report the partial result rather than claiming completion. `omop skills | head` is normal CLI usage and should exit cleanly on a closed pipe.

## Terminology

Use **parallel Hermes security audit** for the Hermes workflow. Reserve **OMOP Team Mode fullscan** for a real OpenCode runtime with `team_mode.enabled` and verified `team_*` tools.

## Pitfalls

- Do not silently substitute `delegate_task` for Team Mode and then report that Team Mode ran.
- Do not trust a repository README claiming full parity; verify available Hermes tools and actual execution output.
- Do not treat a proxy address as the implementation without reading EIP-1967/transparent/UUPS slots and verifying the chain.
- Do not infer a deployer/dev wallet from a sequencer or system transaction.
- Do not call a theoretical economic downside a code vulnerability without a broken invariant and an attacker path.
- Do not run broad active scanners against a third-party target when the bounty rules permit only passive or local testing.
