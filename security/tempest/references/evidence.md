# Evidence Gate ((Hermes-native evidence gate))

## Principle

A claim is only as strong as its provenance. Prose is not evidence.

## Tool evidence types (PASS)

```text
output
command
response
request
log
file
```

Content must be non-empty after trim.

## Live gate rules

1. If no tool evidence → FAIL  
   reason: no tool-output evidence
2. If severity is `critical` or `high` and evidence array empty → FAIL  
   reason: severity asserted with zero evidence
3. Provenance labels:
   - `tool` if any tool evidence exists
   - `context` if only non-tool evidence exists
   - `none` otherwise

## Hermes enforcement

Before reporting a finding as verified:

```text
[ ] at least one tool evidence blob attached
[ ] command/request and observed response saved
[ ] high/critical has tool provenance
[ ] secrets redacted
[ ] retest path defined
```

## Redaction

Never store raw:

- API keys / tokens
- cookies / session material
- private keys / seed phrases
- passwords / OTPs

Replace with `[REDACTED]`.

## Finding minimum fields

```text
id
title
severity
confidence
target
description / root cause
impact
evidence[]
reproduction
remediation
retest_status
```
