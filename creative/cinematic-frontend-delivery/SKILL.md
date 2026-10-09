---
name: cinematic-frontend-delivery
description: Build, debug, and ship immersive fullscreen frontend experiences with a photo-first visual pipeline, layered motion, responsive scene controls, and verified Vercel delivery. Use for cinematic landing pages, interactive visual scenes, animated portfolios, and photoreal background experiences.
version: 1.0.0
---

# Cinematic Frontend Delivery

## Trigger
Use when a user asks for a cinematic, photorealistic, animated, fullscreen, immersive, or scene-based website, especially when it must deploy to Vercel.

## Non-negotiable visual rule
Start with the actual photographic/illustrated hero asset as the scene. Do not redraw trees, buildings, flowers, bridges, or landscapes with CSS blobs or generic geometric placeholders when the requested result is photorealistic. Use procedural layers only for motion and atmosphere: petals, rain, mist, grading, parallax, and subtle water shimmer.

If the supplied asset is a placeholder or depicts the wrong location, state that explicitly and keep it in a clearly named placeholder path. Do not claim a Tokyo scene when the asset is a Fuji scene or generic image.

## Delivery workflow
1. Inspect the destination repository, current deployment URL, and source URL before changing architecture. For a **fresh build into an existing destination directory**, inventory it first and preserve only explicit contracts such as `DESIGN.md`; do not overlay a scaffold and assume stale source/scripts disappeared. After scaffolding, scan project-owned files (excluding generated/vendor directories) for forbidden repository names, obsolete imports, placeholder copy, and old QA scripts. Delete or rewrite every stale artifact before verification.
2. Create or read `DESIGN.md` before UI implementation. Define palette, typography, scene layers, motion budget, breakpoints, accessibility, and asset licensing status. When the design contract deliberately specifies one route, one title, and one action, it overrides generic landing-page recipes such as navigation, AIDA sections, bento grids, and GSAP.
3. Choose the lightest architecture that satisfies the brief. Prefer Next App Router + strict TypeScript + Canvas/CSS overlays over Three.js when a full 3D runtime is unnecessary.
4. Split responsibilities: scene shell, photographic background, particle layer, weather/rain layer, controls, audio hook, environment/performance hook, and pure scene logic.
5. Keep UI subordinate to the scene. Use a small glass control layer, safe-area padding, explicit accessible labels, and no large dashboard panels over the hero.
6. Make all external sound opt-in after user interaction. Generated Web Audio or local licensed assets are acceptable; never autoplay audio.
7. Add reduced-motion behavior, low-performance particle tiers, mobile crop rules, and a fallback that still renders without WebGL.
8. Use seeded variation for particles. Vary size, depth, rotation, speed, drift, and phase; avoid visibly repeating paths. Include a small fraction of particles that settle or interact with the water layer.
9. Add mode controls only when they have real scene effects. Each mode must change grading, light/reflection intensity, wind/particle density, and rain state as appropriate.
10. Run quality gates serially: install, tests, strict typecheck, lint, production build. If any gate fails, fix it and then rerun the **entire requested gate sequence** so the final report is backed by one fresh all-green run. Do not run overlapping Next builds; a shared `.next/lock` makes the second process fail even when code is valid. Generate ICO favicons from an RGBA source because Next/Turbopack can reject palette/RGB-backed ICO payloads.
11. Run real-browser QA at 375x812, 768x1024, and 1280x800. Verify no horizontal overflow, loading/enter state, keyboard activation, focus visibility, reduced motion, and touch-safe controls. Capture screenshots and visually inspect at least desktop plus the narrowest viewport for subject crop, text contrast, and control placement. If the browser daemon fails, install **project-local** Playwright Chromium and use a project-local QA script; never import Playwright or helpers from an unrelated repository.
12. Push only after source and local build pass. Verify the exact deployed URL and custom domain separately. A healthy local build does not prove Vercel is serving the new deployment.

## Deployment verification
After pushing:
- Check the Vercel project URL and the custom domain independently.
- Confirm status `200`, expected page title, expected new asset/chunk markers, and no `404 NOT_FOUND`.
- If the Vercel alias redirects to a custom domain that returns `404`, the project/domain deployment linkage is stale. Redeploy from Vercel with Next.js preset and repository root before claiming the site is live.
- Never report a successful production deployment based only on `git push` or local `next build`.

## Common pitfall
A first implementation often mixes a photo with synthetic CSS tree/skyline/river layers. This reads as a cartoon overlay and fails a photorealistic brief. Remove those synthetic scene layers; retain only photo plus animation/atmosphere overlays.

## Verification report
Final response must include:
- changed architecture and main features;
- exact test/typecheck/lint/build results;
- browser breakpoints and interaction states tested;
- asset provenance/placeholder status;
- separate Vercel alias and custom-domain status;
- any remaining deployment blocker.

## Supporting detail
See `references/photo-first-scene.md` for the photo-first rule, asset checklist, and failure patterns.
