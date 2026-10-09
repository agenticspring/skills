# agenticspring portfolio + Vercel domain

## Repos / URLs
- Profile README: `https://github.com/agenticspring/agenticspring`
- Portfolio: `https://github.com/agenticspring/agentic-portofolio` (note spelling **portofolio**)
- Target domain: `https://agenticspring.dev`
- Secondary token: `GITHUB_TOKEN_2` / `GH_TOKEN_2` in `~/.hermes/.env`

## Static site shape (proven)
```text
index.html
styles.css
script.js
vercel.json
package.json   # optional, scripts only
README.md
.gitignore
```

`vercel.json` can be minimal (`cleanUrls`, security headers). No build step.

## Vercel import defaults
- Framework / Application Preset: **Other**
- Root Directory: `./`
- Build Command: empty
- Install Command: empty
- Env vars: none for static portfolio
- Click **Deploy** when the above is set

## Where to add domain
Not on the first Deploy form.

Path:
```text
Project → Settings → Domains → Add
```
or Production Checklist → **Add Custom Domain**.

Also add optional `www`.

## DNS (typical Vercel)
| Type | Name | Value |
|------|------|-------|
| A | `@` | `76.76.21.21` |
| CNAME | `www` | `cname.vercel-dns.com` |

Always prefer exact records from the Vercel Domains panel if different.

## Redirect policy
- Default after connect: custom domain + `*.vercel.app` both reachable
- User “only my domain” preference:
  1. Set `agenticspring.dev` as **Primary**
  2. Redirect `www` → apex (or reverse if primary is www)
  3. Redirect production `*.vercel.app` → primary custom domain
- Preview deployment URLs may still exist; that is normal

## Live verify
```bash
curl -I https://agenticspring.dev
curl -I https://www.agenticspring.dev
# body checks
curl -sL https://agenticspring.dev | rg -n "Spring|Autonomous Agent"
```

Observed once live:
- `agenticspring.dev` → `www.agenticspring.dev` (primary was www)
- portfolio content title: `Spring 🌸 — Autonomous Agent`

## Vercel MCP note
Docs: `https://vercel.com/docs/agent-resources/vercel-mcp`  
Remote MCP at `https://mcp.vercel.com` lets AI clients manage projects/deployments/logs/analytics via OAuth.  
Optional power-tool; **not required** to ship static portfolio + custom domain.

## Do not
- Put secrets in the public portfolio repo
- Treat Hermes design templates named “vercel” as a deploy skill
- Assume Framework=Next.js for this static site