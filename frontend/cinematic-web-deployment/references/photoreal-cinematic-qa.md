# Photoreal Cinematic QA Notes

## Asset review
A supplied image can be compositionally attractive yet fail the realism bar. Inspect snow geometry, blossom clusters, branch continuity, horizon artifacts, water reflections, and lighting consistency. If multiple reviewers call out malformed snow, melted blossoms, painterly water, or synthetic petals, do not describe it as photorealistic.

## Crop feasibility
For a 1168x784 wide plate:
- Desktop 1280x800: `object-position: 50% 44%` preserves tree, river, and Fuji.
- Tablet 768x1024: `object-position: 58% 50%` preserves the trunk gesture and Fuji summit but crops outer canopy/slopes.
- Mobile 375x812: a cover crop cannot preserve the full tree and Fuji together. Use a deliberate `58% 50%` cover crop if full-bleed immersion is more important than complete subjects; never use contain without checking for a large blank band. If all subjects must remain, commission a portrait-specific asset.

## Visual reset
When replacing a legacy theme, screenshot the live page and grep source for old headline/copy/class markers. Rewrite CSS rather than stacking override blocks. A successful reset has no old marketing copy, no synthetic scenery layers, no fake skyline/tree/river, and only minimal controls.

## Vercel proof
Local `next build` only proves the repo builds. After push, verify the exact commit is on the remote and request the actual Vercel alias/custom domain. A 200 on an old alias or a 404 custom domain is not deployment success. If the repo has an unrelated initial remote commit, inspect ancestry and obtain approval before `git push --force-with-lease`.

## QA matrix
At 375x812, 768x1024, and 1280x800 verify: no horizontal overflow, no console/page errors, scene crop, text/control safe zones, pause/resume interaction, reduced motion, and petal density. Use screenshots and vision review, not only DOM assertions.
