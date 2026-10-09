---
name: share-card-design
description: Design, preview, review, and implement shareable result cards such as PnL, achievement, receipt, and performance cards without prematurely changing production renderers.
version: 1.0.0
author: spring
license: Private
platforms: [linux]
metadata:
  hermes:
    tags: [design, share-card, pnl, preview, visual-qa]
---

# Share Card Design

Use this skill when creating or extending fixed-canvas cards intended for Telegram, social sharing, trading results, achievements, receipts, or performance summaries.

## Required workflow

1. **Inspect the existing renderer first.** Record canvas size, supported fields, fonts, colors, positive/negative states, and existing template compositions.
2. **Separate preview from implementation.** If the user asks to preview or approve designs first, do not add template keys, settings, callbacks, or renderer branches. Generate isolated preview assets only.
3. **Use one identical fixture across every concept.** Token/name, PnL, entry, current/exit value, network, wallet, and timestamp must remain identical so the user compares layout rather than data.
4. **Make layouts compositionally distinct.** New templates must differ in hierarchy and geometry, not merely palette or font.
5. **Render both a contact sheet and full-resolution individual images.** Label concepts with stable numbers/names.
6. **Run visual QA before presenting.** Check clipping, overlap, unsafe margins, long-number fit, missing decimal/sign/percent marks, footer collisions, and data consistency.
7. **Apply requested preview revisions only.** Re-render and visually verify the revised concept. Wait for explicit final approval before production implementation.
8. **Implement only approved concepts.** Preserve existing templates unless the user explicitly requests replacement.

## Composition checklist

A result card should communicate within one glance:

```text
asset/token → PnL result → entry/current or realized values → context/identity
```

Keep the PnL sign and percent symbol attached to the number. Treat diagonal dividers, rings, decorative lines, and oversized typography as collision zones. Reserve comfortable edge margins at the actual output resolution.

## Preview discipline

- State clearly that previews are not wired into the bot/application.
- Do not claim approval from praise alone when a revision is requested; track statuses such as `accepted`, `revision requested`, and `final approved` separately.
- When two concepts are liked, preserve both and revise only the named one.
- Use a vision/screenshot pass after generation. Do not rely on source coordinates alone.
- If QA finds a defect, fix the preview before asking the user to choose.

## Implementation verification after approval

- Add stable template IDs and human-readable labels.
- Add positive and negative fixtures.
- Test long token symbols, long quote values, `PctOnly`, and custom colors/fonts.
- Use integer/decimal-string formatting for financial values; never route large atomic integers through JavaScript floating point.
- Label valuation quality explicitly. Distinguish `UNAVAILABLE`, `INDICATIVE`, `EXECUTABLE`, and `PARTIAL`; when some positions are unvalued, show the count rather than presenting an aggregate as complete.
- Treat cost basis, gas, fees, and royalties as unsigned magnitudes; reserve `+`/`-` signs for actual PnL.
- XML/HTML-escape all untrusted labels and truncate them deterministically before SVG/HTML rendering.
- Decode generated output and assert canvas dimensions, format, metadata absence, and byte limits.
- Render identical fixtures twice and assert deterministic bytes. After visual QA corrections, lock approved hashes or snapshots as goldens and ensure the project's test discovery actually includes the golden file pattern.
- Visually inspect every supported aspect ratio after semantic label changes; source-coordinate review is not enough. Fix unequal margins, clipping, and footer collisions before locking goldens.
- For remote media, require HTTPS, validate every redirect, reject private/reserved IPs, cap MIME/bytes/pixels, disable animation, and re-encode without metadata. Avoid DNS-rebinding gaps by pinning the validated public IP while retaining the original TLS hostname.
- Telegram refresh should edit the original media message by its real message ID instead of posting repeated cards.
- Produce a golden/manual preview from the real renderer before enabling selection in UI.
- Do not change the default template unless explicitly requested.

## Reference

See `references/pnl-preview-review.md` for divergent PnL concepts and geometry lessons, and `references/deterministic-financial-cards.md` for truthful valuation semantics, golden verification, and hardened remote-media ingress.
