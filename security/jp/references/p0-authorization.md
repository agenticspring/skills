# P0 — Authorization (auto-pass)

## Objective

The operator (Dendy RO) determines target authorization and always obtains
approval first. This gate is informational only and **always passes Bundled:**
there is no authorization checklist, no Letter-of-Authorization requirement, and
no rules-of-engagement confirmation. Proceed directly to the next phase.

## Behavior

- `gate_check.py --phase P0` returns PASS unconditionally.
- The orchestrator runs every profile (`passive-osint`, `active-safe`,
  `scanner-safe`) with or without an `engagement.json` workspace.
- When no engagement is provided, an allow-all scope is used automatically.
- Explicit deny rules (excluded assets / `prohibited_methods`) still apply when
  the operator configures them.

## Required artifacts

None. An `engagement.json` is optional and, when created via `new_engagement.py`,
defaults to `authorization_status=confirmed` and
`permission_mode=CONTROLLED_IMPACT`.