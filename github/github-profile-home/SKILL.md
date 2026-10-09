---
name: github-profile-home
description: Customize GitHub profile home (bio fields + username/username Profile README) for multi-account setups; professional human-facing tone by default.
version: 1.0.0
author: spring
license: MIT
platforms: [linux]
---

# GitHub Profile Home

Use when the user wants the **home profile page** polished (what appears at `https://github.com/<user>`), not a PNG share-card, and not just a random repo README.

## What "home profile" means

Two layers:

1. **Profile fields** (sidebar): name, bio, location, blog/website, twitter, hireable  
   - Requires token scope **`user`** (classic) or fine-grained **Profile: Read and write**
2. **Profile README** (Overview embed): public special repo **exactly** `username/username` with root `README.md` on default branch  
   - Requires `repo` (create/push public special repo)

User correction: when they say "tampilan home profile" / "yang muncul langsung ketika buka profile", they mean **both** — especially the Overview README embed. Do **not** deliver a local PNG card as the answer.

## Dual-token ops (this environment)

| Key | Account | Typical use |
|---|---|---|
| `GITHUB_TOKEN` | primary (`<HANDLE_REDACTED>`) | private ops repos, harvester inject |
| `GITHUB_TOKEN_2` / `GH_TOKEN_2` | secondary (`agenticspring`) | public profile + clean public ships |

Store both in `~/.hermes/.env` only. Never commit tokens. After paste in chat, prefer rotate later.

Before profile PATCH, check scopes:

```bash
curl -sI -H "Authorization: token $TOKEN" https://api.github.com/user | tr -d '\r' | grep -i x-oauth-scopes
```

- Missing `user` → profile field PATCH returns 404; still can create Profile README with `repo`
- Missing `repo` → cannot create/push special repo

## Workflow

### 1) Identify account + work identity
Pull live repos/bio with the correct token. Profile copy must match **that account's real work**:
- `<HANDLE_REDACTED>` → security research, reverse engineering, Web3/smart-contract security, automation tooling
- `agenticspring` → cleaner public face by default; switch to **Autonomous Agent** branding when user asks “tema agent”

### 2) Update profile fields (if scope allows)

```http
PATCH /user
{
  "name": "...",
  "bio": "...",
  "location": "...",
  "blog": "...",
  "twitter_username": "...",
  "hireable": true
}
```

### 3) Create/update special Profile README repo

```text
POST /user/repos  name=<login>  private=false  auto_init=true
PUT  /repos/<login>/<login>/contents/README.md
```

Also push `assets/banner.svg` if using a header image.

### 4) Verify embed (not just raw README)

```text
GET https://github.com/<login>
  must contain profile-readme / markdown-body markers
GET https://raw.githubusercontent.com/<login>/<login>/main/README.md
  content matches latest commit
```

If special repo + README exist but Overview still has no `profile-readme`:
- brand-new accounts can lag
- user may need **Share to profile** while logged into that account
- hard refresh / incognito on mobile

Do not claim "home done" from raw README alone when user explicitly wants Overview embed.

## Tone preference (user-corrected)

Default for public profile home:
- **Professional human developer bio**
- Not "AI agent operating autonomously"
- Not terminal farm copy (`$ whoami`, `$ ls ~/capabilities/`, anti-bot capability cards) unless user asks for that style
- Prefer: Full-stack / backend / security / Web3 engineer language
- Avatar-matching banner colors OK; keep text professional

When user says "jangan terlalu agent" / "buat seperti bio Dev profesional":
- rewrite immediately to human professional
- strip agent/autonomous/operated-by-AI language

### Explicit agent theme override
When user says **tema agent** / **bio agent** / wants autonomous-agent branding (e.g. `agenticspring`):
- switch fields + README + banner to agent identity on purpose
- keep clean product branding, not farm capability dump
- proven labels: `Autonomous Agent`, tags like `AUTO` / `RUNTIME` / `PIPELINE` / `OPS` (OPS = operations)
- do not force “professional human only” against an explicit agent-theme request

## Account-specific content guide

### <HANDLE_REDACTED> (account 1)
Emphasize:
- cybersecurity research
- reverse engineering
- smart contract / Web3 security
- automation tooling
- public samples only if **owned work** (e.g. AgentX)
- **Do not list forks as selected work** (user corrected: captcha-solver was a fork — remove)

### agenticspring (account 2)
Emphasize:
- public agent / automation / infra face when asked
- otherwise clean engineering face (backend, APIs, infrastructure)
- profile README repo: `agenticspring/agenticspring`
- portfolio site repo: `agenticspring/agentic-portofolio` → domain `agenticspring.dev`

## Banner / media rules
- Animated GIF/SVG banners are OK for Overview README
- Prefer **original** identity; user rejects “same as someone else’s profile”
- If matching avatar sakura flower:
  - do **not** keep avatar white studio plate/circle
  - aggressive alpha cutouts on glossy translucent petals can create **holes** — if cutout looks damaged, restore last good commit or use gentler bg-removal and re-QA frames before push
  - hard-refresh note for mobile GitHub/Vercel cache

## Portfolio site + Vercel (companion flow)
Static portfolio is enough:
```text
index.html + styles.css + script.js + vercel.json
```
- Framework preset: **Other**
- Build/Install empty; root `./`
- After deploy: **Project → Settings → Domains → Add Custom Domain**
  - not on the first Deploy screen
  - Production Checklist item **Add Custom Domain** is correct
- Default: custom domain + `*.vercel.app` both live
- If user wants only custom domain as public face: primary domain + redirect www + redirect production `*.vercel.app`
- No dedicated Hermes `vercel` skill required for this class; keep steps here / multi-account ops
- **Silent visual override**: user may replace agent portfolio copy with full-canvas art only (no text UI) — e.g. sakura riverside + Fuji; keep mobile-friendly full-viewport canvas
- Vercel MCP (`https://mcp.vercel.com`) is optional AI bridge for project/deploy/logs — **not required** for static deploy + custom domain

## Pitfalls

- Delivering a PNG profile card when user asked for GitHub home UI
- Copying another user's Profile README structure/wording (e.g. Waguri) after user rejected sameness
- Profile PATCH without `user` scope — fails; explain and still ship README if possible
- Claiming Overview embed works after only pushing README while `profile-readme` marker absent
- Putting secrets/API keys into Profile README
- Using wrong token for wrong account (primary vs `GITHUB_TOKEN_2`)
- Overwriting live batch projects while doing profile cosmetics
- Listing forks as flagship projects
- Pushing broken flower cutouts without visual QA frames

## Quick commands

```bash
# fields
curl -X PATCH -H "Authorization: token $T" -H "Accept: application/vnd.github+json" \
  https://api.github.com/user -d '{"name":"Spring","bio":"...","location":"Remote"}'

# special repo + readme push via local git is fine
git clone https://x-access-token:$T@github.com/<user>/<user>.git
# edit README.md + assets/banner.svg
git add -A && git commit -m "docs: update profile home" && git push origin main
```

## References

- `references/profile-readme-embed.md` — special-repo rules, lag, Share to profile, dual-token scopes
- `references/agenticspring-portfolio-vercel.md` — portfolio static ship + domain/redirect checklist
