---
name: hermes-native-security-orchestration
description: Design, audit, and maintain security-orchestration engines and skills for Hermes Agent using real delegation primitives, durable artifacts, scope gates, and honest capability boundaries.
version: 1.0.0
---

# Hermes-Native Security Orchestration

Use this class skill when adapting an OpenCode/OMOP-style security workflow to Hermes, reviewing an existing adapter, or publishing such changes to a repository.

## Core contract

1. Load `hermes-agent` and the relevant security/audit skill before changing code.
2. Query session history before execution; use prior failures as constraints, not as permanent tool refusals.
3. Treat the Hermes parent session as the orchestrator.
4. Use actual Hermes `delegate_task(tasks=[...])` for parallel workers. Do not claim OpenCode `team_*` tools, mailbox lifecycle, or Team Mode unless runtime discovery proves they exist.
5. Keep one deterministic engine as the source of truth for scope, state, phase transitions, and report generation.
6. Bound one delegation batch to the configured Hermes child limit (normally three); workers are isolated leaf agents and cannot coordinate directly.
7. Parent must deduplicate, reproduce, and verify candidate findings before recording them as valid.

## Architecture

```text
User -> Hermes parent -> deterministic CLI
                         |-> scope/RoE gate
                         |-> engagement state + resume
                         |-> recon/enum/report
                         |-> delegation-plan artifact
                              -> delegate_task batch (<=3 leaf workers)
                              -> parent cross-check + safe local/fork PoC
                              -> verified finding gate -> report
```

The CLI should generate a machine-readable delegation plan, but it must not pretend that writing the plan spawned agents. The parent consumes the plan and executes real Hermes tool calls.

## Safety defaults

- Bug-bounty mode is strict, passive-first, non-destructive, and exploit/DoS/exfiltration disabled by default.
- Require explicit scope and rules of engagement for active testing.
- Third-party targets default to passive collection.
- Use local fixtures, testnets, or local forks for PoCs; never attack production to prove a finding.
- A finding requires attacker capability, concrete attack path, impact, evidence, and reproducible verification.
- Do not store secrets in source, state, reports, delegation plans, Obsidian, or persistent memory.

## Repository audit checklist

- Discover all entrypoints and eliminate host-specific absolute paths.
- Inventory the complete payload before pruning legacy trees; preserve only playbooks the Hermes installer actually copies.
- Keep one canonical engine. Remove duplicate skill-local engines or enforce parity with a test.
- Verify an installed CLI can import every local module it needs; installing only the main script is insufficient when it imports an adapter.
- Test installation with a temporary `OMOP_PREFIX` and `HERMES_HOME`, not only the live profile.
- Make the installer profile-safe: no apt/sudo requirement for the core CLI, no credential copying, and no `/root` assumptions.
- Find duplicate engines/skills and add parity checks for safety-critical behavior.
- Search code/docs for `team_mode`, `team_*`, OpenCode-only assumptions, and unsupported model/provider claims.
- Verify the adapter's worker schema matches the real `delegate_task` contract.
- Verify state writes are atomic, resume is deterministic, and reruns do not silently erase findings.
- Add an architecture gate that checks entrypoint portability, safety-mode parity, and delegation limits.
- Run syntax checks, CLI smoke tests, architecture gate, diff checks, then inspect git status before publishing.
- Push only after verification and report the commit hash and actual outputs.

## Documentation rules

Use honest terminology: `parallel Hermes security audit` for the Hermes path; reserve `OMOP Team Mode` for a verified OpenCode runtime with `team_*`. Keep OpenCode packages as clearly labeled reference material or remove them only with a complete migration plan. Never claim “full port” or “all tools active” without runtime evidence.

## Durable work tracking

For complex changes, record objective, constraints, architecture decisions, files changed, verification outputs, remaining gaps, and next step in the user's configured local Obsidian vault. Update the session index before completion. Do not include credentials.

## References

- See `references/hermes-adapter-checklist.md` for the reusable audit/publish checklist.
- See `references/worker-brief-template.md` for bounded worker prompts.
- See `references/custodial-bot-audit.md` for private-chat authorization, wallet-secret lifecycle, SQLite sidecar permissions, polling, and ad-hoc verification gates.
