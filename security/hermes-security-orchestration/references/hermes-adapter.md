# Hermes Adapter Contract

The `omop-hermes` repository uses a deterministic CLI plus a parent Hermes session. The CLI must not pretend to have access to Hermes tool calls.

## Plan contract

`hermes_adapter.py` writes `.omop/engagement/hermes-delegation.json` with:

- `engine: hermes`
- `coordinator: hermes-parent`
- `backend: delegate_task`
- `max_concurrent_workers: 3`
- target and scope
- three independent worker briefs
- lifecycle status

The plan is data for the parent agent. It does not spawn children.

## Parent execution

The parent reads the plan and calls one Hermes batch:

```text
delegate_task(tasks=[
  {goal: surface brief, context: scope + artifacts, role: leaf},
  {goal: accounting brief, context: scope + artifacts, role: leaf},
  {goal: integration/falsification brief, context: scope + artifacts, role: leaf}
])
```

All three may run concurrently. The parent waits for their returned summaries, deduplicates candidates, and runs verification locally. If more workers are needed, start another bounded batch only after reviewing the first.

## Reconciliation record

Store a report with:

- worker role and completion status
- evidence paths/commands
- candidate IDs
- duplicate grouping
- verification result: reproduced, falsified, or unresolved
- scope/impact decision
- next action

Do not report `team_*`, mailbox coordination, or five-agent OMOP Team Mode unless the runtime output proves those tools were present and used.
