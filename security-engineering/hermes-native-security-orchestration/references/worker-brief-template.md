# Bounded Worker Brief Template

Use one brief per isolated Hermes leaf worker. All workers receive the same scope and artifact root.

```text
Role: <surface-recon | auth-accounting | integration-falsification>
Target: <explicit target>
Scope/RoE: <explicit scope; if absent, passive-only>
Artifacts: <absolute or concrete artifact path>

Task:
- <one focused review area>

Required output:
- Evidence with file/function/transaction references.
- Attacker capability and concrete attack path.
- Impact and likely CWE/severity class.
- Safe local/fork/testnet verification idea.
- Rejected hypotheses and why.

Rules:
- Do not attack production.
- Do not use secrets or request credentials.
- Do not call a finding valid without reproducible evidence.
``` 
