# Source Access and Coverage for Public Writeup Corpora

Use this reference with `public-writeup-corpus-analysis.md` when analyzing a historical disclosure table or README range.

## Retrieval ladder — preserve provenance

Attempt the listed URL first and record status, final URL, content type, and whether it contains substantive technical text. If it does not, use the first applicable *public* fallback:

1. **Canonical migration:** publisher's moved article / official replacement page. Example: a publisher moved a Medium review to its own blog.
2. **Canonical raw source:** GitHub/Gist raw Markdown, official source repository, linked report file, or a forum JSON endpoint when it exposes the post body.
3. **Official retrospective:** project postmortem, governance/security-forum disclosure, fix review, or patch record that identifies the same report.
4. **Public archive:** Wayback CDX lookup followed by an archived page, when the original page is dead or removed.
5. **Reader-mediated retrieval:** text extraction against the exact original URL if a normal client is challenge-gated and the reader returns substantive article text. Label this separately; it is not browser-direct access.

Do not use a search-result snippet as the only evidence for a code-level root cause. A title can support an **inference-limited** row only.

## Host-specific practical notes

- **Medium:** ordinary fetches may return a challenge page. Prefer the publisher's official migrated article, then a public archive. Do not treat the challenge HTML as read content.
- **Mirror/Paragraph:** the linked Mirror URL may resolve to a Paragraph-hosted page. Preserve both URLs and treat the resolved publication as the listed-source content when it contains the article.
- **SPA publisher migrations:** a rendered `200` page can be only a generic app shell, while a public read-only site API serves the actual article. Inspect the app bundle/network shape, then query its documented public read endpoint (for example a JSON/tRPC slug lookup) and validate title plus substantive body against the original incident. Never promote a shell response alone.
- **Discourse forums:** request the topic's `.json` endpoint; extract `post_stream.posts[*].cooked` as the official post body. This often contains more text than a rendered scrape.
- **GitHub/Gists:** obtain raw Markdown or an API content response when possible; the UI page alone can truncate code/report text.
- **X/Twitter:** capture the post text and resolve any `t.co` URLs. If resolution leads only to a login-gated X Article or inaccessible Notion page, classify the technical source as limited/unavailable. A reachable teaser post is not a detailed primary source.
- **Wayback:** first query CDX for a timestamped `200` HTML capture, then fetch the `id_` rendition. Record it as archived primary/canonical evidence, not live direct access.

## Accessibility taxonomy

Use exactly one label per row, plus a concise qualifier where useful:

- **D — direct primary:** listed URL or its normal redirect returned substantive technical text.
- **R — reader-mediated primary:** original URL's substantive text came through a text reader after normal retrieval was gated.
- **C — canonical replacement:** an official moved page, raw canonical artifact, or official disclosure gave substantive text.
- **A — archived primary:** substantive text came from a public archive of the listed source.
- **P — partial:** source establishes payout, impact, timeline, or stated classification, but not enough to derive a technical root cause safely.
- **I — index/ambiguous:** list entry itself points to a portfolio/category index rather than a uniquely attributable report.
- **G — gated/unavailable:** source exists but does not expose technical content publicly; do not infer a root cause.
- **X — inference-limited:** only title/snippet metadata survives; describe the limitation, not a specific implementation bug.

Do not collapse `D + R + C + A` into a single count without publishing the breakdown. In particular, a social teaser that says “full report below” but whose report is inaccessible is **P** or **G**, not D.

## Coverage ledger

Create a ledger before analysis. Each requested line must occur exactly once in one mutually exclusive bucket: `D`, `R`, `C`, `A`, `P`, `I`, `G`, or `X`.

At the end, verify:

```text
requested rows == sum(all exclusive buckets)
substantive technical rows == D + R + C + A
```

Report all of the following exactly:

- requested rows / accounted rows;
- substantive technical rows by D/R/C/A;
- partial rows;
- index/ambiguous rows;
- gated and inference-limited rows;
- any payout/severity conflict between README metadata and source text.

For one link that documents two distinct reports, preserve the two README rows while clearly naming which issue maps to each line. For a multi-project writeup, preserve the list's aggregate protocol label and avoid inventing a single affected project.

## Safe synthesis rule

Turn source mechanics into only: root-cause category, violated invariant, and regression/audit heuristic. Omit active sequences, live endpoints, payloads, source addresses, and PoC instructions. If source detail is P/G/I/X, write `not determined from accessible source` rather than inferring implementation details from the declared severity or protocol type.
