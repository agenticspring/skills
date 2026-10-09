# Hermes Integration for TEMPEST (self-contained)

## Always load

```text
skill_view(tempest)
then needed refs: workflow, scope, evidence, cognitive, arsenal, commands
```

## Bootstrap

```bash
command -v nmap nuclei ffuf gobuster httpx subfinder dig whois curl jq nikto sqlmap || true
```

No war-room server required.

## Decision tree

```text
authorized? no → stop
scope receipt? no → write it
tools available? check
domain lane? web/ctf/source/other
mode? hermes-operator | whitebox | limited-domain
```

## Mission artifacts

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
evidence[]
reproduction remediation acceptance_tests
retest_status provenance gate_passed
```

## Long jobs

Use background terminal + notify for long scans. Don't babysit unless asked.

## Failure handling

| Failure | Action |
|---|---|
| no auth | stop |
| tool missing | degrade/block explicitly |
| scope unclear | pause |
| gate blocked | keep candidate, not verified |
| user cancel | archive notes, stop active tools |

## Anti-patterns

- scans without auth text
- fake output for missing tools
- secrets in Discord
- skip retest on high severity
