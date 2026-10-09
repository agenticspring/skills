---
name: photoreal-cinematic-websites
description: Build and deploy image-dominant, photoreal cinematic websites with lightweight environmental motion, responsive art direction, and verified Vercel production delivery. Use when the user asks for realistic immersive scenes, cinematic landing pages, parallax, falling particles, water/light motion, or photo-led visual experiences.
category: frontend
---

# Photoreal Cinematic Websites

## Core rule
The approved photographic plate owns the scene. Do not redraw the subject with CSS geometry. A realistic hero is:

```text
licensed/final image plate
+ restrained grading and localized scrim
+ depth-aware environmental particles
+ subtle water/light motion
+ responsive art direction
```

It is not:

```text
photo placeholder + CSS tree + block skyline + fake river + generic particle blobs
```

## Workflow

1. **Preflight the repository**
   - Confirm the target repository and branch.
   - If the user names a replacement repository, do not inspect, copy, or reuse the previous project.
   - Inspect the repository before writing code. A fresh repo needs a design contract before UI code.
   - Load the frontend design/perfection guidance and strict TypeScript guidance when applicable.

2. **Validate the visual asset before implementation**
   - Inspect the exact image the user approved. Check whether it is genuinely photographic, AI-looking, or stylized.
   - Never claim photorealism if the asset has melted blossoms, malformed snow, painterly water, or synthetic geometry.
   - If the user requires “very realistic” and the approved asset is visibly synthetic, find a legal, attributable replacement or clearly flag the conflict before deploying.
   - Document asset provenance in `README.md`; never silently use scraped/copyright-unclear media.

3. **Create the design contract first**
   - Add `DESIGN.md` before components.
   - Define palette, typography, crop strategy, motion limits, touch targets, reduced-motion behavior, and explicit anti-patterns.
   - Add a one-line pointer to the asset provenance and crop reference if a supporting file exists.

4. **Build the visual plate**
   - Use `next/image` or equivalent with explicit dimensions/fill, `priority` for the hero, and `sizes`.
   - Use one final image plate. Optional blurred backdrop may fill letterbox areas on portrait screens, but it must not replace the sharp plate.
   - Use localized text scrim/shadow rather than a heavy global vignette that crushes the water and landscape.
   - Never place text over the Fuji summit, trunk, or the primary blossom detail. Use genuine negative space.

5. **Add motion without fake scenery**
   - Use Canvas or CSS transforms only for motion overlays.
   - Petals must vary in size, depth, blur, rotation, drift, and speed. Do not distribute them uniformly or render identical pink ellipses.
   - Wind direction should be consistent with the tree/river composition; let some petals settle toward the water instead of resetting visibly in a loop.
   - Water shimmer must be low-opacity, directional, and tied to the existing water region. Avoid decorative sparkles or random noise.
   - Parallax is capped, transform-only, passive-listener based, and paused when the tab is hidden.
   - Respect `prefers-reduced-motion`; provide a still-image fallback with minimal or no particle animation.
   - Keep interactive controls at least 44px, keyboard accessible, and touch friendly.

6. **Responsive crop strategy**
   - Do not assume one `object-fit: cover` crop works at every aspect ratio.
   - For wide image plates, calculate whether tree, river, and mountain can coexist in the viewport. They often can on desktop but cannot all fit in a narrow portrait crop.
   - Prefer art-directed crops or a sharp `contain` plate over destructive mobile cropping when preserving all subjects matters; use a blurred backdrop to avoid empty letterbox space.
   - Verify 375x812, 768x1024, and 1280x800. Record object-position decisions in `DESIGN.md` or a reference note.

7. **Quality gates**
   - Run install, tests, strict typecheck, lint, and production build serially. Do not run concurrent builds in the same workspace; `.next/lock` causes misleading failures.
   - Run a production server, not a dev server, for browser QA.
   - Use Playwright/real Chromium screenshots at mobile, tablet, and desktop widths.
   - Exercise loading, initial action, pause/resume or mode controls, reduced motion, and console/page errors.
   - Assert no horizontal overflow and verify safe-area spacing.
   - Inspect screenshots for real visual issues: empty unexplained regions, subject loss, malformed assets, petal blobs, crushed shadows, low contrast, and controls pinned to unsafe edges.
   - Do not declare completion from a successful build alone.

8. **Security and dependency gate**
   - Run `npm audit --omit=dev` or equivalent.
   - If transitive production advisories are fixable with non-breaking overrides, pin the fixed versions and regenerate the lockfile.
   - Never run `npm audit fix --force` blindly on a Next.js app; it may downgrade the framework to an unsafe, incompatible major.
   - Re-run tests/typecheck/lint/build after dependency changes.

9. **Push and deploy verification**
   - Commit only after the final gates pass; do not include screenshots, `.next`, tokens, or local QA artifacts.
   - Push with the configured credential without persisting secrets in the remote URL.
   - If Vercel is connected to GitHub, verify the production alias—not just local build or a preview URL.
   - Check both custom domain and `.vercel.app` alias with HTTP and browser content. A `200` on one URL does not prove the custom domain maps to the same deployment; a `308` followed by `404 NOT_FOUND` is a deployment/domain-linkage blocker.
   - If direct Vercel CLI management is unavailable, report the exact dashboard action required rather than claiming deployment succeeded.
   - **For Dez portfolio/cinematic sites: Vercel is production.** Local `next start` is QA-only and must be stopped before finishing. Do not present a VPS URL as the deployment.

## Known pitfalls

- A source repo can be correct while the Vercel custom domain still serves an old deployment or `404`; always verify both URLs after push.
- A visually attractive image can still be AI-looking. Inspect Fuji snow, blossom clusters, branch structure, horizon objects, and water reflections at full resolution.
- Large CSS-generated trees/buildings/bridges make a photo-led scene look like a game illustration. Remove them rather than layering more filters.
- A mobile screenshot with a large blank band can mean `contain` or fixed image height is misconfigured. Either make the band intentional or fill it with a blurred version of the same image.
- A button labelled “Resume” on initial load is a state bug. Use “Pause” initially and switch to “Resume” only after pausing.
- A temporary test alias failure is fixed by explicit Vitest alias config or a relative test import; do not misreport it as application failure.
- Concurrent Next builds create `.next/lock`; serialize the quality gate and clear only a stale lock after confirming no build process is active.
- A repo replacement is a hard boundary: no old code, assets, remote URLs, or styling should leak into the new project.
- **Leaving VPS `next start` running after a Vercel-bound push is a product mistake for Dez sites**—kill QA ports; production is GitHub→Vercel only.

## Support references

- `references/realism-qa.md` — visual inspection checklist and responsive crop notes.
- `references/vercel-verification.md` — deployment/domain verification matrix and failure interpretation.
