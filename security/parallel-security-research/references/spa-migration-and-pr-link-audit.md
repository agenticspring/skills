# SPA Publisher Migration, Wayback Replay, and PR Link-Mapping Audit

Use with the public writeup-corpus workflow when a publisher has moved legacy articles into a client-rendered site and a PR claims to repair many links.

## Evidence-standard workflow

1. **Freeze the corpus base.** Read the exact requested README commit and capture original line, label, and URL. Do not let later row-number shifts become the identity.
2. **Test legacy URL first.** Record final URL, response code, byte count, and whether article-specific text is present. A tiny 404 body establishes that the listed source is unavailable; it does not establish a replacement.
3. **Reject SPA-shell false positives.** Compare several candidate routes. If they return the same document/title/body shell, do not call any of them retrieved. Extract public JS bundle references and inspect them read-only for public data routes/procedure names.
4. **Query published data read-only.** First request the index/list procedure, then item-by-slug. Mark body retrieved only when the item response contains matching title/date/body. A successful response containing `json: null` means that slug is not in the active migration dataset.
5. **Use archive correctly.** Query CDX against the exact legacy canonical URL, choose a `200 text/html` capture, then retrieve the timestamped `id_` replay. CDX metadata alone proves capture existence, not full-body access. Record both the legacy canonical URL and the replay URL.
6. **Seek official corroboration for non-publisher sources.** Prefer project postmortem, security advisory, patch/commit/PR, or raw report before archive. Verify that it describes the same report, not merely a similar vulnerability.
7. **Audit PR mapping independently.** Fetch raw README at base SHA and head SHA. Match rows by original line/old URL plus surrounding row context. Do not join solely by protocol label: labels such as a protocol name may legitimately recur. Report artifact mapping defects, submitted-head defects, and intentional source duplicates separately.

## TrustSec migration case (reusable reference, not a universal endpoint claim)

Observed public routes on `trustsec.xyz`:

- SPA shell at `/blog/<slug>` referenced a Vite bundle and used `/api/trpc`.
- `blog.list` supplied the active post inventory.
- `blog.getBySlug` supplied the article-specific `title`, `publishedDate`, `tags`, canonical Notion source URL, and `content`.
- `getBySlug` returned `{"result":{"data":{"json":null}}}` for legacy posts not carried to the active blog.

This established a defensible split:

- **Canonical replacement:** active slug with matching full `content` from the publisher's public API.
- **Archived primary:** legacy slug with full body in timestamped Wayback `id_` replay.
- **Unavailable:** neither active item nor usable replay has substantive content.

The technique applies to similar public SPA migrations, but route names and transport must be rediscovered per publisher.

## PR-mapping checks

For each proposed repair, retain a table such as:

| Base line | Original URL | Head line | Proposed URL | Source mode | Body verified | Mapping verdict |
|---:|---|---:|---|---|---|---|

Rules:

- A historical table's line can shift after the PR adds/removes rows; preserve **base line** as the report identifier.
- The same publisher/report URL assigned to two distinct old URLs is a suspected duplicate until both content identities are checked.
- A mapping file can be wrong even when the final PR head uses the right URL; do not attribute its error to the submitted README without checking the head SHA.
- Identical URLs in two corpus rows may be an editorial duplicate (for example, separate credited reporters) rather than a link-mapping bug. State that distinction.

## Report wording

Use explicit evidence language:

- `full body retrieved` only for article/report content, not 200 HTML or a title/snippet.
- `canonical source URL` means original canonical URL if archived, otherwise official moved/replacement URL.
- State root cause only when the retrieved body, official advisory, code change, or report supports it.
- Finish an exhaustive assignment with `## EXPAND`: enumerate genuinely unchecked leads, or `none — reason` after all known lead categories were tested.
