# Hermes Adaptation Checklist

## Discovery

- [ ] Load Hermes and security skills.
- [ ] Query session history.
- [ ] Identify every executable entrypoint.
- [ ] Inventory duplicate engines, skill copies, packages, docs, and installer payload.

## Runtime contract

- [ ] Parent Hermes is the only coordinator.
- [ ] Real `delegate_task(tasks=[...])` call is the only parallel backend.
- [ ] Worker count matches configured Hermes limit.
- [ ] Plan artifacts are not reported as executed delegation.
- [ ] Workers are leaf-isolated and parent performs deduplication/verification.

## Portable install

- [ ] No `/root` or operator-specific absolute paths.
- [ ] Main CLI and imported helper modules are installed together.
- [ ] Skill goes under `${HERMES_HOME:-$HOME/.hermes}/skills/`.
- [ ] Temporary prefix/profile install succeeds.
- [ ] No unnecessary apt/sudo or credential copying.

## Security and validation

- [ ] Bug-bounty mode: strict, passive-first, DoS/exfil/exploit off by default.
- [ ] Scope and RoE are persisted and enforced.
- [ ] Findings require evidence and safe reproducibility.
- [ ] `py_compile`, `bash -n`, architecture gate, CLI smoke, and `git diff --check` pass.
- [ ] Working tree and pushed commit are verified before reporting completion.

## Cleanup decision

Do not delete legacy material solely because it mentions another runtime. First determine whether it is copied by the installer or needed as an active playbook. If removing it, record the inventory and ensure the README and skill references point only to files that still exist.
