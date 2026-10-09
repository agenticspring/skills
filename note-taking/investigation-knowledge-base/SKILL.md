---
name: investigation-knowledge-base
description: Use when persisting investigation findings to the vault.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Notes, Vault, Obsidian, Durable, Investigation, KnowledgeBase]
    related_skills: [obsidian]
---

# Investigation Knowledge Base

For the moment a long investigation has to **outlive the conversation**: "simpan seluruh pengetahuan
mu di vault", "save everything you learned about X", or your own judgment that this work must survive
context loss, `/new`, and compaction.

Companion to the bundled `obsidian` skill, which covers *file-tool mechanics*. This skill covers
**semantics**: what the notes should be shaped like, and how to keep them honest when the verdict
changes mid-investigation.

## When to use

- The user explicitly asks to persist findings ("simpan di vault", "save all knowledge about X").
- An investigation ran 5+ tool calls across many topics and will obviously be referenced later.
- **A conclusion changed during the work.** This is the highest-value trigger — the notes already
  written now contain a *wrong* verdict, and nobody will notice unless you go fix them.
- Fragmented notes on one subject have accumulated across sessions.

## The structure: hub-and-spoke

Do **not** append one 700-line monolith. Split by question, so a future session can read only what
it needs:

```
<Subject> - Hub.md                  <- entry point: 10-second answer table, verdict, key numbers, links
<Subject> - <Aspect A>.md           <- one focused note per question the user actually asked
<Subject> - <Aspect B>.md
<Subject> - Risks and Verdict.md    <- risk matrix, scenarios, falsification criteria
<Subject> - Toolkit and Scripts.md  <- artifacts + reusable commands
<Subject> - Evidence Log (raw).md   <- chronological raw log; the appendix, linked last
```

- **Name notes `<Subject> - <Aspect>.md`.** A stable `Subject - ` prefix keeps names predictable and
  alphabetical in the folder.
- The **hub** answers the user's actual questions in a compact table (one row per question, ✅/❌/⚠️
  verdict). Someone in a hurry should get everything from the hub alone.
- Put the **raw log last** and label it an appendix. Raw evidence is valuable; unreadable walls are not.
- **Keep wikilinks pointing at the hub** from every spoke, plus `Home.md` or the local index.

## Three tiers of truth — label every claim

The most useful thing a recon note can do is tell the next reader *how much to trust each line*.
Tag claims as you write:

| tier | example |
|---|---|
| **Verified** — read directly from the live system | bytecode hash match, receipt decode, live balance |
| **Sourced claim** — from docs, registries, third parties | "docs say mainnet is under development" |
| **Unverifiable / open** | operator identity; anything only one endpoint can assert |

Give the unverifiable bucket its own section ("Yang BELUM bisa dibuktikan" / "What cannot be
proven"). An honest "not provable" section is a feature, not a gap — it stops a future agent
re-deriving the same dead end, and it stops an over-confident verdict.

## Revising a verdict that the notes already recorded

The trap: a note titled **`X - Fake RPC Verification`** survives into a session where the system
turned out to be **genuine**, but the opposite. The file name, the body, and every inbound link still
assert the old conclusion. Future sessions — including ones that never load this conversation —
will read the stale title and act on it.

Do all five steps. Skipping any one leaves a live trap:

1. **Rename notes whose title encodes a superseded verdict.** A title is a claim. When the claim
   flips, the name must change (`X - Fake RPC Verification` → `X - Evidence Log (raw)`).
2. **Repair every inbound wikilink.** A rename silently orphans links — Obsidian shows them as dead
   text, and a future agent will not find the note. Grep the **old basename** across the whole vault
   *before* declaring done:

   ```bash
   grep -rn "Old Note Basename" <vault>/          # expect hits in the index + sibling notes
   grep -rhno "\[\[<Subject>[^]]*\]\]" <vault>/   # list the links that now exist
   # then re-grep the old names -> must return nothing
   ```

   Hits typically land in the session index and in sibling notes that cross-referenced it. Fix each
   by hand; a global search-and-replace across a vault is how you corrupt unrelated notes.
3. **Banner the body, don't rewrite it.** When a raw log's middle sections still contain the wrong
   conclusion, prepend a `> [!warning]` callout at the top: this is the raw log, the earlier verdict
   was wrong, here is the correction, start from the hub. Rewriting hundreds of lines of evidence is
   both risky and dishonest — the record of the wrong turn is itself useful.
4. **Supersede older notes that reach a now-wrong conclusion.** When an earlier-session note says the
   opposite of today's finding, do **not** delete it — prepend a `> [!note] SUPERSEDED — <date>`
   banner stating what it got wrong, what is now true, and which note to read instead.
5. **Consolidate index bloat.** Once one subject owns 3+ bullets in the index, collapse them into a
   **single line** that summarises the verdict and links the hub. The index is a router, not a
   summary.

## Secret sweep before you declare done — and its one false positive

Vault notes must never carry credentials. Sweep, and **report the result rather than asserting it**:

```bash
# key prefix from the real key file, never the whole key
grep -rl "$(head -c 8 /path/to/pk.txt)" <vault>/            # want: no hits
grep -rE "g\.alchemy\.com/v2/[A-Za-z0-9_-]{15,}" <vault>/   # want: no hits (a real key VALUE)
grep -roE "\b[0-9a-f]{64}\b" <vault>/                       # expect some — triage each
```

Two things that look like leaks and usually are not:

- **A bare env-var NAME** (`ALCHEMY_API_KEY`, `GC_DISCORD_WEBHOOK`) in setup docs is a pointer, not a
  secret. Only a *value* is a leak. Check the match's shape, not just its presence.
- **A 64-hex string is ambiguous** — a private key, a transaction hash, and a SHA-256 digest all look
  identical. **Read the surrounding context before raising an alarm.** In the worked case three
  64-hex hits were all `SHA-256` checksums of PNGs and a bridge chunk, sitting right next to the
  words `SHA-256`. Grep with `-B2 -A2` and judge.

Report the sweep as a short pass/fail block. It converts "I was careful" into evidence.

## Verify by reading back

Never claim durable storage without a read-back. Re-open each note you wrote or renamed and confirm
it exists with the expected size, and re-grep the old names to confirm zero dangling links. Then say
what you verified — file list with sizes, link check, secret sweep — instead of "done".

## Pitfalls

- **Appending to one giant note instead of splitting.** It becomes unreadable and unlinkable exactly
  when the next session is looking for something specific.
- **Renaming without repairing links.** The rename is the easy half; the grep is the half that
  matters.
- **Deleting a contradicted older note.** Keep it, banner it. The record of a wrong earlier
  conclusion is what stops it being re-derived.
- **Overwriting a raw evidence log to "fix" it.** The stale verdict must be marked, not erased.
- **Storing the verdict only in chat.** If it is not in a file you read back, it does not exist.
- **Putting secrets, keys, tokens, or `.env` contents in the vault.** Sweep, and check before alarming.
- **A verdict with no expiry.** Every verdict note needs a **falsification criteria** section — the
  concrete signals that would overturn it (a counter hitting non-zero, an official announcement, a
  contradiction from an independent source). Without it the note quietly rots into misinformation.
- **One-session-shaped note names.** Name by subject and aspect, not by today's task.

## Worked example

A four-phase recon (leaked chain, contract audit, token discovery, live bridge test) consolidated into
an 8-note hub-and-spoke set, including the rename + link repair, two supersede banners, an index
consolidation, and a clean secret sweep:
`references/worked-consolidation.md`.

## Related

- `obsidian` (bundled) — file-tool mechanics for the same vault: read, search, create, patch, wikilinks.
