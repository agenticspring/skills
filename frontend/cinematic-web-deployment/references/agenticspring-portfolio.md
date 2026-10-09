# agenticspring portfolio product rules

Active site repo: `https://github.com/agenticspring/spring`  
Profile README special repo: `https://github.com/agenticspring/agenticspring`  
Domain: `agenticspring.dev` via **Vercel only** (GitHub push → Vercel). Do not leave VPS `next start` running for this product.

## Product modes (user chooses)

| Ask | Product |
|---|---|
| Cinematic / sakura / Fuji scene | Image-led immersive page (no SaaS portfolio chrome) |
| Portfolio / profile website | Account portfolio for `agenticspring` |
| “Dari bio aja” / “tanpa project yang dibuat” | **Bio-led only** — no selected-work cards, no list of repos we just created |

## Bio-led defaults

Positioning (keep consistent unless user overrides):

- **Spring 🌸**
- **Autonomous Agent**
- Tagline: `automation · orchestration · infrastructure`
- Capability tags: `AUTO` · `RUNTIME` · `PIPELINE` · `OPS`
- Status line style: `status: online` / always shipping
- Public links: GitHub `agenticspring`, X `@springhermes`
- No fabricated project portfolio

When user says “tambahkan kata-kata di banner README home”, read the live banner asset under `agenticspring/agenticspring` (`assets/agent-banner.gif` / frame OCR) and surface **those exact strings** on the site hero—not paraphrases only.

## Sakura pink palette (from avatar sample)

| Role | Hex / value |
|---|---|
| Main | `#e692af` |
| Soft | `#f5c5da` |
| Deep | `#d9789a` |
| Dark rose UI | `#1a1016` |

Apply together on website tokens **and** GitHub profile README badges when restyling pink.

## Design-reset checklist

Before claiming redesign done:

```bash
# example markers that must not remain after a reset
grep -RInE 'Spring, softly|A moment held|Hold this moment|Resume scene|scene-copy|scene-plate|Virtuals Browserless|selected work|project-card' src README.md || true
```

Rewrite CSS/components rather than stacking overrides on the previous theme.

## Deploy / QA discipline for Dez

1. Implement in `/tmp` or dedicated workdir, gate: typecheck + lint + build (+ tests if present).
2. Commit + push to `agenticspring/spring` `main` with `GITHUB_TOKEN_2`.
3. Vercel deploys from GitHub; report commit SHA.
4. If local production QA was used, **stop the port** (`4310–4340` class ports) and confirm no spring VPS listeners before finishing.
5. Custom domain 404 after push ⇒ Vercel project linkage / Redeploy issue, not “code missing,” once build is green.

## Retired / do not reuse

- Old portfolio repo name `agentic-portofolio` (deleted/replaced by user).
- CSS-synthesized trees/skyline/rivers for “photoreal” requests.
- VPS as production host for this site.
