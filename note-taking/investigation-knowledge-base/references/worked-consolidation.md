# Worked example — consolidating a four-phase investigation

Subject: a leaked pre-launch EVM chain (referenced generically below; the findings themselves live
in the vault, not here). The investigation ran across two sessions and four phases:

1. Chain/RPC authenticity recon (probe, registries, domain forensics, block census)
2. L1 contract-suite code audit (bytecode-hash baseline, admin authority, exit path)
3. Token / contract discovery (chain-wide topic census, contract inventory, deploy ordering)
4. Live bridge execution (fresh wallet, deposit, end-to-end verification)

By the time the user said *"simpan seluruh pengetahuan mu di vault"*, the vault already held
**fragmented, partly-stale notes** — including one session-long note that had grown to 777 lines with
the verdict recorded backwards.

---

## Starting state (the mess)

| file | problem |
|---|---|
| `Web3/<Subj> Chain Fake RPC Verification 2026-09-26.md` | 777 lines. **Title asserted the opposite of the final verdict** (started as "fake", ended as "genuine but pre-launch"). Body still contained the wrong early conclusion mid-file. |
| `Web3/<Subj> Chain 9134 Contract Inventory.md` | Fine content, inconsistent naming. |
| `Research/<Subj> - Mainnet RPC Review.md` | Written months earlier by a *passive* review; concluded **"no RPC leak found"**. Now directly contradicted. |
| `00-Inbox/Session Index.md` | **4 long bullets** on this one subject, each hundreds of words — the index had become a second summary. |
| `Home.md` | No pointer to any of it. |

## Ending state (8 notes, hub-and-spoke)

```
Web3/<Subj> - Hub.md                          (85 lines)   entry point + answer table + verdict
Web3/<Subj> - Chain Recon.md                  (171)        identity, endpoint quirks, census, timeline
Web3/<Subj> - L1 Contract Audit.md            (155)        bytecode baseline, admin, exit path
Web3/<Subj> - Contract and Token Inventory.md (167)        full addresses, ordered by creation
Web3/<Subj> - Bridge Playbook.md              (172)        proven procedure, gas, pitfalls
Web3/<Subj> - Risks and Verdict.md            (128)        risk matrix, scenarios, falsification
Web3/<Subj> - Toolkit and Scripts.md          (125)        artifacts + command cheat sheet
Web3/<Subj> - Evidence Log (raw).md           (790)        the old monolith, bannered, as appendix
```

Note the shape: one note per *question the user actually asked*, not one note per session. The raw
log was **kept** and demoted to an appendix rather than deleted or rewritten.

## The rename + link repair, in order

The title was a claim and the claim had flipped, so the rename was mandatory:

```bash
cd <vault>/Web3
mv "<Subj> Chain Fake RPC Verification 2026-09-26.md" "<Subj> - Evidence Log (raw).md"
mv "<Subj> Chain 9134 Contract Inventory.md"          "<Subj> - Contract and Token Inventory.md"
```

Then find what just broke:

```bash
grep -rn "<Subj> Chain Fake RPC Verification\|<Subj> Chain 9134 Contract Inventory" <vault>/
```

It returned **three** hits, all in `00-Inbox/Session Index.md` — precisely the ones that would have
silently rotted. Each was hand-fixed to point at the right new target (the first two →
`[[<Subj> - Hub]]`, the third → `[[<Subj> - Bridge Playbook]]`). A global `sed` across the vault was
deliberately avoided — it would have rewritten unrelated notes.

Final check that must return nothing:

```bash
grep -rn "<Subj> Chain Fake RPC Verification\|<Subj> Chain 9134 Contract Inventory" <vault>/
```

## Banner the body instead of rewriting it

The 777-line log was left intact; a callout was **prepended after the H1** by script so the wrong
early conclusion could never be read as the verdict:

```markdown
> [!warning] THIS IS THE RAW LOG, NOT THE SUMMARY
> Its original title was "...Fake RPC Verification" — **the early verdict was wrong** (I first
> guessed fake; the chain is in fact genuine and merely pre-launch). The correction is inside.
>
> **Start at the hub:** [[<Subj> - Hub]]
> Focused notes: [[...]] · [[...]] · [[...]]
```

Anchoring the insert on the first `# ` line keeps it idempotent and puts it above everything a reader
sees first.

## Supersede banners on older notes

The months-old passive review was **not** deleted. It got a callout at the very top:

```markdown
> [!note] SUPERSEDED — <date>
> This review concluded **"no leak found"**. That is **no longer true.** The leak was subsequently
> found and verified.
>
> **What still holds from this note:** the official launch-status statement and the documented
> endpoint list. The "no leak" conclusion is stale.
>
> Continue at: [[<Subj> - Hub]]
```

Distinguishing *what still holds* from *what is stale* is what makes a supersede banner useful rather
than just a retraction.

## Index consolidation

Four long bullets → one router line:

```
- **<Subj> — full knowledge base at [[<Subj> - Hub]].** <one-paragraph verdict: what is real, what
  the risk is, the single blocking fact.> Notes: [[hub]] · [[recon]] · [[audit]] · [[inventory]] ·
  [[playbook]] · [[risks]] · [[toolkit]] · [[raw log]]
```

The index is a **router**. Long per-subject summaries belong in the hub note, not here — otherwise the
index becomes a second, diverging summary that nobody keeps in sync.

`Home.md` gained one line under a "Sorotan"/highlights heading pointing at the hub, because every
subfolder link in it was already dangling (`[[Web3]]`, `[[Research]]`, … with no matching notes).

## Secret sweep — and the false positive

```bash
grep -rl "$(head -c 8 <pk-file>)" <vault>/                  # -> no hits                     OK
grep -rE "g\.alchemy\.com/v2/[A-Za-z0-9_-]{15,}" <vault>/   # -> no hits (real key VALUE)    OK
grep -roE "\b[0-9a-f]{64}\b" <vault>/                       # -> 3 hits                      TRIAGE
```

The three 64-hex hits looked like private keys. Grepping with context showed every one was a
**`SHA-256` checksum** — two deterministic PNG hashes and one bridge-chunk digest — each sitting
immediately after the literal text `SHA-256`. **No leak.** Reporting them as "possible keys" would
have been a false alarm on an otherwise clean sweep.

The env-var hits (`ALCHEMY_API_KEY`) were likewise just **names** in setup documentation pointing at
`~/.hermes/.env` — a pointer, not a value. Both classes are worth *saying out loud* in the report,
because the distinction is exactly what the next reader needs.

## Verification reported instead of asserted

The completion message listed, rather than claimed:

- the 8 files with line counts and byte sizes
- the link repair, with the grep that proves zero dangling links
- the secret sweep as a pass/fail block, including the triaged 64-hex hits
- the pointer added to `Home.md`

## The durable payoff

Three things in the finished set earn their keep later and are worth deliberately writing every time:

1. **A hub answer table** — the whole verdict readable in ten seconds.
2. **A "what cannot be proven" section** — stops the next session re-deriving a dead end and stops an
   over-confident verdict.
3. **Falsification criteria** — for this subject, the concrete signals that would *revise the verdict*
   (a protocol counter going non-zero, an official announcement, the endpoint disappearing). A verdict
   with no expiry quietly rots into misinformation.
