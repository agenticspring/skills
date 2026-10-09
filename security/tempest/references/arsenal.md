# Arsenal (system tools)

## Mental model

```text
desired tool
→ is binary installed?
→ is use in scope?
→ run + save evidence
→ gate finding
```

Never invent tool output.

## Baseline often present

```text
nmap nuclei ffuf gobuster httpx subfinder
dig whois curl jq nikto sqlmap
```

## Often missing

```text
semgrep gitleaks trivy radare2
```

## Gates

```text
safe_local       read-only local checks
active_network   in-scope recon/scan
blocked          off-scope / destructive / no auth
```

Dangerous classes needing explicit approval:

```text
credential spraying
exploit payloads
privilege escalation
persistence simulation
DoS / destructive actions
```

## Ship criteria for a phase

```text
[ ] required tools present or step explicitly degraded
[ ] commands logged
[ ] outputs stored under evidence/
[ ] secrets redacted
[ ] findings only from tool-backed evidence
```

## Hermes rule

If tool missing:

1. state missing tool
2. offer install only if user wants
3. continue with alternatives or mark blocked
