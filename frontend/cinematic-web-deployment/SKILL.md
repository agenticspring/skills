---
name: cinematic-web-deployment
description: Build and ship image-led cinematic websites with Next.js, Tailwind, Canvas motion, strict visual QA, and Vercel deployment. Use when the user wants a realistic immersive scene, animated landing page, or a fresh redesign deployed from GitHub to Vercel.
---

# Cinematic Web Deployment

## Trigger
Use for a new or redesigned cinematic visual website, especially when the user provides an image/reference and asks for Next.js, responsive motion, production quality, GitHub, or Vercel deployment.

## Non-negotiable workflow

1. **Respect repository boundaries.** Inspect the exact repository named by the user. If they say a previous repo is deleted/replaced, do not read, copy, or reuse its source, styling, assets, or visual language. Start a fresh tree and state the active repo explicitly.
2. **Pre-flight context.** Load the relevant frontend/design and TypeScript guidance, inspect prior session history, then create `DESIGN.md` before UI implementation. Store durable project state in Obsidian when the task is complex.
3. **Define the visual source of truth.** A realistic scene must be image-led. Use a verified, repository-owned, licensed/high-quality asset. Do not synthesize trees, buildings, mountains, rivers, or reflections with CSS shapes when the user asks for realism. Motion layers may add petals, subtle shimmer, mist, wind, and parallax only.
4. **Do not silently substitute assets.** If the user-approved image is stylized/AI-looking or does not meet the requested realism/location, flag that before presenting it as photorealistic. Search for a legal alternative or ask the user for an asset; never call a placeholder final.
5. **Design reset means reset.** On “redesign / jangan tema lama / desain ulang,” remove old copy, classes, components, and motifs. Do not append overrides to old CSS. Rewrite cleanly and **grep old-theme markers** before shipping (legacy headlines/CTAs, project cards, scene classes). Partial restyle of the previous hero is a failure.
6. **Dez portfolio vs cinematic scene (pick what was asked).**
   - **Cinematic scene:** image-led, minimal UI, environmental motion only.
   - **GitHub account portfolio:** stop the sakura/scene product. Build an account portfolio. For `agenticspring`, default is **bio-led agent positioning** (identity, focus, principles, public profile links)—**not** a fabricated selected-work list of repos we just built unless Dez explicitly asks for project cards.
   - “Dari bio aja / tanpa project yang dibuat” ⇒ strip project sections; GitHub/X profile links only.
   - Keep palette + banner copy aligned with live profile: sakura pinks from avatar (`#e692af`, `#f5c5da`, `#d9789a`) and banner strings when present (`Spring`, `Autonomous Agent`, `automation · orchestration · infrastructure`, `AUTO`/`RUNTIME`/`PIPELINE`/`OPS`, status online). See `references/agenticspring-portfolio.md`.
7. **Prefer one strong surface.** Visual experience: no SaaS chrome; artwork dominates; controls ≥44px. Bio portfolio: one editorial page, not a scene with leftover marketing residue.
8. **Responsive art direction.** Calculate crop feasibility before coding. Wide plates often cannot keep tree+river+Fuji under portrait `cover`; choose explicit object-positions or mobile art direction. No accidental letterboxing. Test 375x812, 768x1024, 1280x800.
9. **Motion must be environmental.** Transform/opacity-only parallax, DPR≤2, adaptive particles, varied shape/depth/drift, visibility pause, `prefers-reduced-motion`. No autoplay audio. Canvas decorative + `aria-hidden`.
10. **Production gates.** Tests when logic exists, typecheck, lint, production build, real-browser QA when UI changed. No “production-ready” without gates.
11. **Deploy via GitHub → Vercel for Dez portfolio sites.** Push the active repo (`agenticspring/spring`). **Do not leave long-running `next start` on the VPS**—Dez deploys on Vercel. Kill local QA ports when done. Inspect divergent remote history before force-with-lease (needs explicit approval). Verify commit + live Vercel/custom domain; 404 ⇒ project/repo linkage, not “code missing” if build is green.

## Required deliverable
- `DESIGN.md` with tokens, layout, motion, asset rules, and anti-patterns.
- Next.js App Router + TypeScript + Tailwind project.
- Repository-owned image under `public/images/` with provenance in README.
- Scene component + adaptive particle component + pure logic tests.
- SEO metadata, Open Graph, favicon, accessible controls.
- README with local, test, build, and Vercel deployment instructions.
- Verified commit hash, test/typecheck/lint/build output, visual QA matrix, and live deployment status.

## Pitfalls learned
- Local green build ≠ live Vercel content; custom domain can still 404 or serve an old alias.
- CSS trees/skyline/rivers make “photoreal” requests look illustrative—remove, don’t filter forever.
- Mobile `contain` can letterbox; `cover` can drop a subject—choose deliberately and screenshot.
- Old theme markers linger—grep before commit.
- Unrelated initial remote commit → non-fast-forward; inspect, ask, then force-with-lease only if approved.
- **VPS `next start` after “push for Vercel” angers Dez.** Short-lived local QA only; kill ports.
- **Bio-only means no self-built repo “selected work”.**
- **Banner/README home text drifts**—OCR/read live `agenticspring/agenticspring` banner and surface exact strings when asked.
- **Pink “close enough” fails for agenticspring**—use avatar-sampled pinks on site + README badges together.
- **User anger signals are product rules:** “Jangan deploy di VPS”, “tanpa project yang dibuat”, “tambah kata di banner”, “warna pink sesuai foto profil” — apply immediately (kill local `next start` ports, strip project cards, OCR banner text, sample avatar hexes). Do not re-argue or leave residual scene/marketing CSS.

## Reference
- `references/photoreal-cinematic-qa.md` — crop/realism/deploy lessons.
- `references/agenticspring-portfolio.md` — agenticspring product rules, palette, banner copy, Vercel-only deploy.
