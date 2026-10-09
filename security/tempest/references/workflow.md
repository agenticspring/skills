# TEMPEST Full Mission Workflow (Hermes-native)

Self-contained. No external war-room repo required.

## 0) Preconditions

```text
[ ] Authorization exists (owner / written permit / lab / bounty scope)
[ ] Target list written
[ ] Out-of-scope list written
[ ] Tool availability checked
```

Preflight:

```bash
command -v nmap nuclei ffuf gobuster httpx subfinder dig whois curl jq nikto sqlmap || true
```

Done when blockers known.

## 1) Mission contract

```text
mission_name:
owner/authorization:
objective:
success_criteria:
target(s):
in_scope:
out_of_scope:
allowed_actions:
forbidden_actions:
max_detection_events:
approval_required_for:
report_audience:
deadline:
```

## 2) Scope receipt + RoE

### Default RoE

```text
maxDetectionEvents: 5
requireManualApproval:
  - credential use
  - command execution on target
  - privilege escalation
```

### Strict RoE

```text
forbidden:
  - data destruction
  - service stop / recovery inhibit
  - endpoint DoS
maxDetectionEvents: 2
```

Do not start active networked tools until receipt is filled.

## 3) Kill-chain order

```text
RECON
→ WEAPONIZE
→ DELIVER
→ EXPLOIT
→ INSTALL
→ C2
→ ACTIONS_ON_OBJECTIVES
```

Mission status:

```text
created → active → paused/resumed → completed | aborted
```

## 4) Phase playbook

### A — RECON

Goals: assets, DNS/subdomains/ports/services, tech fingerprint, surface map.

Typical tools:

```bash
dig +short <host> ANY
whois <domain>
subfinder -d <domain> -silent
nmap -sV -T4 --top-ports 100 <target>
curl -I https://<host>
```

Exit:

```text
[ ] STACK written
[ ] SURFACE written
[ ] open questions listed
[ ] evidence saved
```

### B — WEAPONIZE / SCAN

Goals: vuln candidates, misconfig, prioritization.

Typical tools:

```bash
nuclei -u https://<host> -silent
ffuf -u https://<host>/FUZZ -w <wordlist>
nikto -h https://<host>
nmap -sV -sC <target>
```

Exit:

```text
[ ] candidates ranked
[ ] each has tool evidence
[ ] FP risks noted
```

### C — DELIVER / EXPLOIT (only if allowed)

Goals: validate high-value candidates, prove impact, stop at RoE boundary.

Typical tools (authorized only):

```bash
sqlmap -u '<url>' --batch --level=1 --risk=1
# or targeted manual curl/ffuf/nuclei template validation
```

Exit:

```text
[ ] confirmed vs unconfirmed split
[ ] impact evidence-backed
[ ] secrets redacted
```

### D — INSTALL / C2 / persistence sim

Only when engagement explicitly includes it and RoE allows. Prefer report-only recommendations on production.

### E — ACTIONS / ANALYST

Goals: synthesize findings, remediation, residual risk.

Exit:

```text
[ ] findings gate-passed
[ ] retest status set
[ ] remediation actionable
[ ] unknowns listed honestly
```

## 5) Cognitive loop inside every phase

```text
RECON(1-3) → PLAN(+ABANDON IF) → EXECUTE+STATE → REFLECT(every 5) → SELF-CRITIQUE
```

State ledger:

```text
CONFIRMED / REFUTED / OPEN / NEXT
```

3 failed variants → switch class.

## 6) Evidence + promotion

```text
tool call → raw output saved → evidence gate → provisional finding → retest → verified/rejected → report
```

## 7) Hermes modes

1. Hermes-operator (default)
2. Whitebox source review
3. Capability checks with available tools

## 8) Abort / pause

Pause/abort when:

```text
scope unclear
authorization missing
detection budget exceeded
destructive technique requested outside RoE
off-scope target
secrets would be logged raw
```

## 9) Deliverables

```text
[ ] scope receipt
[ ] phase notes + evidence
[ ] findings table
[ ] remediation + acceptance tests
[ ] residual risk
[ ] redaction complete
```

## 10) One-shot recipe

```text
1. load skill tempest
2. write scope receipt
3. check tools
4. recon + evidence
5. scan + rank candidates
6. validate only approved candidates
7. gate findings
8. retest
9. report
```
