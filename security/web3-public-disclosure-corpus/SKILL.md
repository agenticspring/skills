---
name: web3-public-disclosure-corpus
description: Use when acquiring source-backed public Web3 cases.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [web3, security-research, disclosures, audit-reports, provenance]
    related_skills: [immunefi-writeup-corpus]
---

# Public Web3 Disclosure Corpus Acquisition

## Overview

Build a local-only, source-backed corpus of historical Web3 findings. Prefer final/adjudicated reports and original project postmortems over raw submissions, social posts, indexes, or test fixtures. This skill is for research and defensive study only: do not probe targets or run historical exploit PoCs.

## When to Use

- A study needs hundreds of public, technically source-backed Web3 disclosure cases.
- The corpus emphasizes asset loss/drain, authority, initialization, upgrade, configuration, deployment, or cross-domain errors.
- Existing Immunefi cases must be excluded or merged without inflating the count.

Do not use a title, payout, dashboard row, HTTP 200 SPA shell, test file, or alert post as proof of a technical finding.

## Source Priority

1. **Code4rena final reports** — enumerate `code-423n4` repositories; prefer `*-findings` repos with immutable `report.md`. Use only final H/M primary issues.
2. **Sherlock judging repos** — enumerate `sherlock-audit`; use `*-judging` final README/PDF. Older repos use a family directory; `1-report.md` is the representative issue. Later reports use top-level `Issue H-n` / `Issue M-n` in README.
3. **Original audit-firm reports** — use Solodit content as a discovery/reader layer, then preserve publisher/fix/canonical source evidence. It is not a universal final adjudicator.
4. **CodeHawks** — scrape official contest/result pages as reader-mediated sources. Separate First Flights as `training/seeded`; do not treat them as production disclosures.
5. **Cantina/Spearbit** — acquire individual official portfolio PDFs/reports. The public OpenAPI documentation is evidence of schema only; client endpoints are not evidence of anonymous access.
6. **Ethereum Foundation disclosures** — use official UID tables for client/spec/consensus/deployment categories; dedupe linked Immunefi report URLs.
7. **GitHub Advisory Database** — use GHSA IDs for verified dependency/library vulnerabilities only, not as a broad on-chain vulnerability source.
8. **Incident catalogues** — use DeFiHackLabs/DefiLlama-derived datasets to discover candidates only; promote after original postmortem/fix/advisory evidence.

## Acquisition Workflow

1. **Snapshot the source.** Record acquisition timestamp, source URL, repository SHA or HTTP validator, and SHA-256 of every downloaded artifact.
   - Completion: every candidate has immutable provenance before parsing.
2. **Parse final units.** Extract one candidate per final H/M/C finding, with its platform issue ID, report URL, title, text, status, source code commit, and remediation links.
   - Completion: parser preserves report section/heading and page/line provenance.
3. **Classify source evidence.** Follow this ladder:
   `original report → reader-mediated original → official final/raw/advisory/fix → archived primary → partial/index/social`.
   Use one label: D, R, C, A, P, I, G, X. Count only D/R/C/A as technical study cases.
   - Completion: each counted case has a stored substantive body, not merely metadata.

   **Final-report parser boundary:** a selected H/M section must end at the next finding heading of **any** severity (`H`, `M`, `L`, `G`, `N`, `QA`, informational) or at a report-level end heading such as `Disclosures`. Stopping only at the next H/M can absorb low/gas/report boilerplate and corrupt section evidence. Persist section line range plus SHA-256; reject a section containing a report-level ending heading.
4. **Filter defensively.** Prioritize case text with drain/accounting/withdrawal/cross-domain or authority/initializer/proxy/upgrade/configuration keywords, but treat keyword results only as triage.
   - Completion: root cause and impact come from the source body, not keyword inference.
5. **Deduplicate.** First use `{platform, immutable primary issue ID}`. Then canonical report URL, audited code commit + normalized title + location/function, and fix PR/CVE/GHSA/incident transaction linkage. Retain `same_issue_as` relationships instead of silently deleting records.
   - **Code4rena identity pitfall:** report display labels such as `H-05` / `M-02` are not globally or even report-uniquely reliable—some `report.md` files embed a later mitigation round that reuses those labels. Prefer the GitHub issue URL in the finding *heading* as the primary identity. If absent, use report immutable commit + bounded section SHA-256 and label that fallback. Never use the first issue URL appearing anywhere in the section; it may be an “also found by” duplicate.
   - Completion: raw duplicate submissions and label reuse do not inflate a final finding count.
6. **Exclude the existing Immunefi corpus.** Block exact source URLs/normalized aliases, then review soft matches by protocol, code commit, title, and fix link. EF tables commonly point back to Immunefi reports.
   - Completion: each import records `new`, `duplicate_of_existing`, or `ambiguous`.
7. **Separate study lanes.** Keep (a) production/adjudicated disclosures, (b) realized incident postmortems, (c) educational/seeded labs, and (d) dependency advisories in distinct datasets.
   - Completion: severity, loss, and authority claims are never aggregated across lanes.

## Canonical Keys

| Family | Primary case key |
|---|---|
| Code4rena | `c4:{contest_id}:{primary_github_issue}` |
| Sherlock | `sherlock:{judging_repo_sha}:{H/M-number}` or final primary issue ID |
| CodeHawks | `codehawks:{contest_slug}:{unique_finding_id}` |
| Cantina | `cantina:{report_id_or_sha}:{heading_or_page_anchor}` |
| EF | `ef:{UID}` |
| GitHub Advisory | `ghsa:{GHSA-ID}` |
| Incident | `incident:{chain}:{primary_tx_hash}` when independently established |

## Local Reference Snapshot (2026-07-31)

- Source research plan: `/root/.hermes/research/web3-public-disclosures-20260731/ACQUISITION_PLAN.md`
- Primary corpus: `/root/.hermes/research/public-disclosure-drain-corpus-20260730/`.
  - `2,834` D/R/C/A source-body cases after evidence/dedup gates.
  - `2,328` Code4rena final H/M sections are locally archived and immutable-commit-pinned; each has source/report/section SHA-256 plus line bounds.
  - `1,661` v3 extended-study cases are preserved separately; 555 B-tier ScaBench benchmark bodies are never aggregated into primary-source authority claims.
  - Offline verifier: `uv run verify_primary_corpus_v4.py` in that corpus directory.
- Code4rena inventory: 350 final reports recovered from 376 `*-findings` candidates; report heading inventory is ample for a >=500 first tranche.
- Sherlock inventory: 229 judging repos, with 2,683 H/M final issue headers recovered.
- Solodit pin: `a8ab1ebc8a73b32f95040cd96d2f7e4ac2529098`.
- EF pin: `721e3fff1ec08c297adf5bd8eeb5f9bccd0395b0`.
- GitHub Advisory DB pin: `8cd347ead1e47f4e19e934d6386c8d8ee0443633`.

Treat inventory counts as snapshot input, not unique cases until section/source-level dedup passes.

## Common Pitfalls

1. **Counting submissions instead of adjudicated findings.** C4 and Sherlock retain duplicates; use designated primary/final findings only.
2. **Treating a generic SPA as retrieved content.** Require specific title, finding body, and per-item result before assigning R or C.
3. **Classifying a DeFiHackLabs fixture as source evidence.** It is a locator/reproduction artifact; verify project postmortem or fix independently.
4. **Assuming a documented API is publicly available.** Cantina's client API documentation does not authorize anonymous bulk collection.
5. **Mistaking GitHub Advisory coverage for DeFi coverage.** GHSA is best for packages/dependencies and often lacks on-chain incident details.
6. **Failing to remove Immunefi overlap.** EF and aggregators can contain canonical Immunefi URLs.

## Verification Checklist

- [ ] Every counted record is D/R/C/A and has a local body/provenance artifact.
- [ ] The immutable source revision and artifact hash are stored.
- [ ] Final primary issue identity is distinct from raw reporter submission identity.
- [ ] Existing Immunefi URLs and cross-platform duplicates are marked, not double-counted.
- [ ] Production, postmortem, training, and dependency lanes are distinct.
- [ ] No live system was tested and no historical exploit fixture was executed.
