# Hermes Adapter Audit and Publish Checklist

## Discovery

- Load the Hermes skill and relevant security skill.
- Inspect live Hermes toolsets and config; never infer `team_*` availability from source docs.
- Query prior sessions for failed paths and corrections.
- Clone the requested repository and verify the remote before editing.

## Architecture

- Parent Hermes session owns orchestration and verification.
- Deterministic CLI owns scope, state, phases, and reports.
- Adapter writes a plan; it does not claim to spawn workers.
- One batch has no more than the live `delegation.max_concurrent_children` limit.
- Workers are independent leaf tasks; parent merges their results.

## Safety

- Bug bounty defaults: strict scope, passive-first, no DoS, no exfiltration, no exploit phase.
- Active tests require explicit scope/RoE.
- Use local fork/fixture/testnet PoCs.
- Reject theory-only findings.

## Drift audit

- Search duplicate engine copies and compare safety-critical blocks.
- Search for host-specific absolute paths.
- Search for OpenCode/team-mode claims in runtime docs and entrypoints.
- Add/execute an architecture gate.

## Verification

- Python syntax compile for every changed Python file.
- CLI `--version`, modes, and a non-network adapter-plan smoke test.
- `git diff --check`.
- Inspect `git status --short --branch`.
- Push only after all checks pass; record commit hash and remote status.
