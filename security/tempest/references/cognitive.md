# Cognitive Harness ((Hermes-native cognitive harness))

## Goal

Predictable offensive process under uncertainty. Prefer persistence + tool-backed falsification over recipe dumping.

## Loop

### Phase 1 — RECON (mandatory early)

Map attack surface before exploit hypotheses harden.

Must produce:

```text
STACK:    layers (proxy/app/db/auth)
SURFACE:  endpoints / inputs / assets
BUG-HYP:  specific claim with evidence pointer
WHY:      observations, not vibes
```

Anti-tunnel laws:

1. Proxy in front of app → inspect proxy first
2. Pinned dependency version → check known issues carefully
3. "Clean" app source → look at config/library/boundary

### Phase 2 — PLAN

Write:

```text
attack class:
preconditions:
expected effect:
ABANDON IF: <falsifier>
```

### Phase 3 — EXECUTE + STATE

After every tool call update:

```text
CONFIRMED:
REFUTED:
OPEN:
NEXT:
```

Hard rule: **3 failed variants of same attack class → switch class**.

### Phase 4 — REFLECT (every 5 iterations)

Ask:

```text
what progressed?
what is stuck?
which bias? (confirmation / anchoring / ignored layer)
next different class?
```

### Phase 5 — SELF-CRITIQUE before claim

Before emitting a final FLAG/finding:

- prove with live tool output
- include PROOF line / evidence id
- refuse writeup-only claims

## Min-iteration floor (v4.2 spirit)

If no proven claim yet and budget remains:

```text
reject early UNKNOWN / give-up
force another attack class
keep going until floor or real proof
```

Lesson from T3MP3ST: bottleneck is often persistence, not missing knowledge.

## Honesty

- Scrub contaminated writeup material from task files when benchmarking
- Prefer zero-recipe measurement when evaluating capability
- Separate stable single-agent results from unproven swarm results
