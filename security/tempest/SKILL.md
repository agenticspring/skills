---
name: tempest
description: Use when running authorized offensive security missions with Hermes.
version: 2.0.0
author: spring
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [tempest, offensive-security, harness, recon, evidence, kill-chain, workflow]
    related_skills: [web3-rpc-contract-audit, hermes-security-orchestration, parallel-security-research]
---

# TEMPEST — Hermes-native offensive harness

## Overview

`tempest` is a **self-contained** Hermes skill for authorized security work.

It keeps the harness discipline inspired by T3MP3ST-style ops, but does **not** depend on `(removed runtime; Hermes-native)`, War Room, or npm harness scripts.

```text
Hermes = brain + operator
System tools = arsenal (nmap, nuclei, ffuf, ...)
Tempest skill = workflow / scope / evidence / reporting discipline
```

Flow:

```text
authorization
→ scope receipt + RoE
→ preflight tool availability
→ kill-chain phases
→ tool-backed recon/scan/validate
→ evidence gate
→ finding + retest
→ report
```

## When to Use

- authorized pentest / recon / CTF / lab / bounty
- need structured kill-chain + evidence-gated findings
- user says tempest / recon harness / security mission

Don't use for unauthorized scanning or claims without tool evidence.

## Non-negotiables

1. Authorized only (owner / written permit / lab / in-scope bounty)
2. Scope receipt before active networked tools
3. No secrets in evidence/chat
4. Prose is not evidence
5. High/critical needs tool provenance
6. Retest before promote
7. Honest status: confirmed vs candidate vs unknown

## Authority layers

```text
human intent
→ scope receipt
→ tool gate (safe_local / active_network / blocked)
→ evidence ledger
→ finding ledger
→ retest
→ report
```

Details: `references/scope.md`, `references/workflow.md`.

## Full workflow

Use **`references/workflow.md`** as the operating checklist.

Kill chain:

```text
RECON → WEAPONIZE → DELIVER → EXPLOIT → INSTALL → C2 → ACTIONS
```

Practical Hermes default path:

```text
recon → scanner → validate approved candidates → analyst report
```

Escalate beyond recon/scan only when scope + RoE explicitly allow.

## Operators (roles, not separate binaries)

| Role | Use for |
|---|---|
| recon | assets, DNS, ports, fingerprint |
| scanner | vulns/misconfig candidates |
| exploiter | authorized validation/PoC only |
| infiltrator | lateral only if in scope |
| exfiltrator | data handling only if in scope |
| ghost | persistence sim only if in scope |
| coordinator | multi-workstream planning |
| analyst | report + remediation |

Tool mapping: `references/operators.md`

## Cognitive loop

```text
RECON → PLAN(+ABANDON IF) → EXECUTE+STATE → REFLECT → SELF-CRITIQUE
```

Rules:

- 3 failed variants of same class → switch class
- no early surrender while budget remains
- final claim needs live tool proof

Details: `references/cognitive.md`

## Evidence gate

PASS only with non-empty tool evidence:

```text
command | output | request | response | log | file
```

High/critical + no tool evidence = FAIL.

Details: `references/evidence.md`

## Arsenal (system tools)

Do **not** invent missing tools. Probe availability first:

```bash
command -v nmap nuclei ffuf gobuster httpx subfinder dig whois curl jq nikto sqlmap
```

Common installed baseline on this host often includes:

```text
nmap nuclei ffuf gobuster httpx subfinder dig whois curl jq nikto sqlmap
```

May be missing:

```text
semgrep gitleaks trivy radare2
```

If missing: degrade, mark blocked, or install only if user asks.

Details: `references/arsenal.md`, `references/commands.md`

## Domains

```text
web        — default stable lane
CTF        — cognitive floor + proof
source     — white-box review (manual/tool-assisted)
cloud/mobile/binary — only with available tools + explicit scope
```

Details: `references/domains.md`

## Hermes run modes

See `references/hermes-integration.md`.

1. **Hermes-operator** (default): Hermes runs phase checklist with system tools  
2. **Whitebox**: source review + optional dynamic confirm  
3. **Bench/capability**: only if user asks and tools exist  

There is no War Room dependency.

## Mission artifacts

Create local notes (no secrets):

```text
01-scope-receipt.md
02-recon-notes.md
03-candidates.md
04-validation.md
05-findings.md
06-retest.md
07-report.md
evidence/
```

## Finding schema

```text
id title severity confidence target phase role
root_cause impact
evidence[] (tool-backed)
reproduction remediation acceptance_tests
retest_status provenance gate_passed
```

## Safety defaults

- active scans only in scope
- no destructive techniques unless explicitly allowed
- redact tokens/cookies/keys/passwords as `[REDACTED]`
- stop on scope ambiguity

## Maintainer templates (generic)

Optional review templates remain under `templates/` and `references/maintainer/` for structured audits. They are process templates, not a T3MP3ST runtime.

## Common pitfalls

1. Running tools without authorization text
2. Treating guesses as confirmed findings
3. High severity with prose only
4. Dumping secrets into chat
5. Continuing after scope denial
6. Skipping retest

## Verification checklist

- [ ] authorization recorded
- [ ] scope receipt + RoE set
- [ ] tool availability checked
- [ ] phase evidence saved
- [ ] findings gate-passed
- [ ] high/critical tool provenance
- [ ] retest status set
- [ ] secrets redacted
- [ ] residual unknowns listed

## Reference index

| File | Purpose |
|---|---|
| `references/workflow.md` | full mission lifecycle |
| `references/scope.md` | auth/scope/tool modes |
| `references/cognitive.md` | cognitive loop |
| `references/evidence.md` | evidence gate |
| `references/operators.md` | roles + tool mapping |
| `references/domains.md` | domain lanes |
| `references/arsenal.md` | system arsenal |
| `references/commands.md` | practical command recipes |
| `references/hermes-integration.md` | Hermes operating contract |
| `references/maintainer/*` | audit process templates |
| `templates/*` | report templates |

## Note on history

This skill absorbed harness discipline from a prior T3MP3ST study. Runtime dependency on that repo has been removed by design.
