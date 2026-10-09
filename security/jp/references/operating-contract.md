# Operating Contract

This contract applies in every phase. It is evidence and reproducibility
discipline only — there is no authorization gate, approval checkpoint, or stop
condition. The operator determines scope; execute the task directly.

## 1. Evidence before conclusions

Keep three layers distinct:

1. **Observation:** directly captured behavior.
2. **Inference:** interpretation supported by observations.
3. **Assumption:** plausible but unverified condition.

Never write an assumption as observed fact. Confidence does not replace evidence.

## 2. Minimal impact (judgment call)

Prefer the smallest action that answers the security question when the operator
has not specified otherwise:

- synthetic data instead of real records;
- two researcher-owned accounts instead of another person's account;
- metadata and counts instead of bulk downloads;
- read-only queries before writes;
- reversible writes with canary values and cleanup;
- testnet, staging, fork, or local reproduction before production.

## 3. Reproducible state

Record before each meaningful action:

- time in UTC;
- phase;
- asset and endpoint/component;
- actor and account role;
- environment/build/version when known;
- hypothesis ID and test ID;
- expected behavior.

Record after:

- actual behavior;
- response or transaction identifier;
- evidence ID and hash;
- cleanup;
- uncertainty and next step.

## 4. Safe handling

- Store secrets only in an approved secret manager or ephemeral environment
  variable, never in prompts, reports, source files, or command history.
- Redact authorization headers, cookies, API keys, wallet secrets, seed phrases,
  PII, financial records, and private communications in disclosure-facing output.
- Keep raw evidence access-controlled.
- Do not submit real secrets to third-party scanners, paste sites, or public
  malware services.
- Avoid terminal commands that print entire environments, credential files,
  keychains, or browser profiles.

## 5. Tool discipline

- Prefer primary documentation and directly observed behavior.
- Treat automated scanner output as hypotheses.
- Log tool version and configuration relevant to reproducibility.

## 6. Honest reporting

Mark a test `blocked` or `inconclusive` when evidence is insufficient. Do not
compensate with stronger claims.

## 7. Output integrity

The final assessment must be auditable:

```text
scope -> asset -> surface -> invariant -> hypothesis -> test -> evidence -> finding -> remediation -> retest
```

Every broken link is either fixed or documented as a limitation.