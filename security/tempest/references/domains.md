# Domain Coverage (Hermes-native)

| Domain | Status | Notes |
|---|---|---|
| Web apps | primary | default lane with nmap/nuclei/ffuf/httpx |
| CTF | supported | use cognitive floor + proof |
| Source code | supported | manual/whitebox + optional scanners if installed |
| Cloud/IaC | limited | only with cloud tools + explicit scope |
| Mobile | limited | needs mobile tooling |
| Binary/RE | limited | needs reverse tooling |
| Smart contracts | limited | needs specialized analyzers |

## Entry patterns

### Web

```text
recon surface → fingerprint → candidates → validate → gate → retest → report
```

### CTF

```text
mandatory recon iters → plan with ABANDON IF → execute → reflect → proof before claim
```

### Source white-box

```text
map entrypoints/sinks → review authz/input boundaries → optional dynamic confirm
```

## Honesty rule

If tooling is incomplete for a domain, say so and keep findings provisional.
