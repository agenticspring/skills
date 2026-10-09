# Evidence-First Taxonomy for Public Disclosure Corpora

Use this reference when asked to classify every entry in a historical bug-bounty/write-up list by root cause, especially when source accessibility varies.

## Non-negotiable assignment rule

Assign a root-cause category only when one of the following supports the **same incident**:

1. substantive body from the listed primary source;
2. reader-mediated/canonical replacement text tied to that URL;
3. a SCV/database row whose URL matches the entry URL after normalizing scheme, trailing slash, and tracking parameters;
4. an official retrospective/crosslink tied by exact URL or uniquely corroborated incident metadata.

Otherwise use the literal bucket **`unverified metadata/title only`**. A title, protocol label, payout, severity, generic theme tag, or search snippet is never enough for a precise technical cause.

## Identity before taxonomy

Do not join evidence on protocol name alone. Protocols often have multiple unrelated reports. Build one evidence record per README row first:

```text
readme line | protocol | listed URL | payout | severity |
primary access/status | source archive path | SCV URL match |
official URL match | supported cause | evidence tier | notes
```

Normalize URLs before matching, but preserve original URLs in the artifact. Treat these as **not automatically the same incident**:

- repeated protocol labels with different URLs;
- an official post from the same protocol but a different date/title;
- a database row whose URL differs from the README row;
- a social post whose visible body exposes only a title or external short-link.

## Source-access ladder and strength

Use the corpus access labels consistently:

- `direct-full`: substantive original body;
- `fallback-full`: reader/canonical replacement body;
- `direct-partial`: classify only what the retained portion explicitly supports;
- `unavailable`: classify only if an exact incident-level SCV/official source independently supplies the cause.

Archive ingestion may contain portfolio pages, unrelated site navigation, SPA shells, or pages aggregating several reports. Confirm the text actually refers to the current line before using it.

## Classifying safely

1. Extract a defensive root-cause statement and broken invariant, not an attack recipe.
2. Use an exclusive primary category per README row. If the row deliberately contains multiple distinct reports, assign `multi-root row` rather than collapsing them into a made-up single cause.
3. If the same official post describes two issues and distinct README rows name different reporters/claims, use reporter/date/issue labels in that post to map each row before assigning.
4. Record the evidence basis for every assigned row in the machine-readable output.
5. Do not convert tool-generated keyword themes into evidence; use them only to locate source passages.

## Compact output contract

Deliver both JSON and readable Markdown. At minimum include:

```json
{
  "scope": {"pinned_commit": "...", "readme_data_lines": "...", "data_row_count": 0},
  "evidence_policy": {"assignment_rule": "..."},
  "categories": [{"id": "...", "count": 0, "lines_compact": "...", "entries": []}],
  "unverified_metadata_title_only": {"count": 0, "lines_compact": "...", "entries": []},
  "audit_invariants": {}
}
```

For each category give a compact list/range of README lines, count, and per-row basis. Preserve the required literal unverified label.

## Required audit invariants

Check mechanically before finalizing:

```text
assigned_supported + unverified = requested data rows
all expected data rows accounted for exactly once
no blank/separator README row counted
sum(category counts) = assigned_supported
no category line overlaps the unverified set
parsed JSON is valid
Markdown ends with the user-required final section/value
source-status counts equal the evidence matrix counts
```

State material-source coverage separately from row coverage. A complete taxonomy can legitimately contain unverified rows; do not pretend every source was opened.

## Common pitfalls

- **False corroboration:** inheriting a historical SCV/official issue merely because the protocol name matches.
- **Evidence laundering:** treating a title, social preview, or automated `themes` field as a root-cause proof.
- **Row collapse:** assigning a single cause to a row that explicitly aggregates two findings.
- **Mis-mapping shared postmortems:** mapping repeated README rows to the first issue in a common official post without reporter/date/issue reconciliation.
- **Overclaiming access:** calling a challenge page, SPA shell, or social login wall substantive primary access.
- **Unsafe synthesis:** copying exploit steps, payloads, addresses, or live-target procedures into a taxonomy; write the invariant instead.
