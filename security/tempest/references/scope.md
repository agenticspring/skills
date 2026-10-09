# Scope And Authorization ((Hermes-native scope model))

## Core rule

Be adversarial inside an explicit contract. Preserve scope, evidence, and operator accountability.

## Authority layers

| Layer | Purpose |
|---|---|
| Human intent | plain-language mission |
| Scope receipt | target + allowed action class |
| Tool gate | safe_command / receipt_required / catalog_only / import_only |
| Evidence ledger | durable proof before claims |
| Finding ledger | impact + fix + evidence ids |
| Retest | validation before promotion |
| Memory proposal | human-reviewed durable learning |

## Execution modes

- `safe_command` — local-read / lab-safe, still logged
- `receipt_required` — active, networked, credential-adjacent, or higher risk
- `catalog_only` — known capability, not generic executable surface
- `import_only` — import external evidence only

## Non-negotiables

1. No third-party target without explicit scope
2. No production writes without named approval
3. No raw secrets in evidence
4. No generic unrestricted exploit shell
5. Findings need evidence + retest before high confidence
6. Memory needs acceptance before durable storage

## Reviewer checklist

- What target is in scope?
- What action class is approved?
- Which tool output supports each claim?
- Can it be retested?
- Can nontechnical stakeholder understand risk/next action?
- Can technical stakeholder reproduce evidence?

## Hermes default refusal

Refuse or stop when:

```text
no authorization text
target outside receipt
user asks to skip evidence
request expands to off-scope public hosts
```
