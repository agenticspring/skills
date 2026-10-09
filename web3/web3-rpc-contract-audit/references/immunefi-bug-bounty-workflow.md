# Immunefi Bug-Bounty Workflow

## Pre-flight checklist

- Program URL and last-updated date
- In-scope contract addresses
- Chain IDs and deployment versions
- Source repository/commit and verified bytecode
- Accepted impacts and severity definitions
- PoC requirement
- KYC and payout requirements
- Out-of-scope items, known issues, duplicate policy
- Safe-harbor and disclosure rules

## Candidate finding format

- Title
- Affected contract/function
- Attacker capability
- Preconditions
- Step-by-step attack path
- Asset or invariant violated
- Measurable impact
- Safe local-fork/testnet reproduction
- Evidence: transaction simulation, trace, assertion, or test output
- CWE/severity rationale if applicable
- Minimal remediation

## Reject or downgrade when

- The target is not in scope.
- The issue is a normal economic risk or intended design behavior.
- There is no concrete attack path.
- The impact is theoretical or cannot be reproduced safely.
- It requires privileged access without showing how that access is obtained.
- It relies on external market failure, depegging, or third-party compromise outside the program's accepted impact.
- The issue is already known or duplicated.

## Reporting discipline

- Keep the report private.
- Do not test exploit transactions on mainnet.
- Do not include secrets or unnecessary personal data.
- Report only after confirming scope, novelty, accepted impact, and reproducibility.
