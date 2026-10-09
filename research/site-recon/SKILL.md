---
name: site-recon
description: Recon a URL to map its stack, APIs, and infrastructure.
---

# Site Recon

Systematic website reconnaissance to extract maximum intelligence from a URL.

## Process

Run all independent steps in parallel where possible to minimize latency.

### 1. First Contact (parallel)

Gather initial data simultaneously:

- **web_fetch** the URL (extract markdown, up to 15k chars)
- **browser open** the URL, resize to 1920x1080, screenshot
- **Evaluate** `document.documentElement.outerHTML.substring(0, 8000)` to get raw HTML/head tags

From the HTML head, extract: title, meta description, meta keywords, og tags, robots directives, framework hints.

### 2. Infrastructure Recon (parallel)

Run via exec in a single shell block:

```bash
# DNS
dig +short <domain> A
dig +short <domain> CNAME
dig +short www.<domain> CNAME
dig +short <domain> TXT
dig +short <domain> MX
dig +short <domain> NS

# IP geolocation
curl -s "https://ipinfo.io/<ip>/json"
```

Note the hosting provider, registrar (from IP), and email setup.

### 3. Route Discovery (parallel)

Probe common paths in a single shell loop. Adapt the path list to the site's apparent type.

**Universal paths:**
```
/robots.txt /sitemap.xml /manifest.json /api /api/health /api/status
/docs /about /pricing /terms /privacy /blog /login /signup /register
/dashboard /app /settings
```

**Crypto/Trading paths:**
```
/swap /portfolio /discover /tokens /markets /pairs /positions
/orders /watchlist /alerts /snipe /copy-trade /terminal
/bridge /earn /airdrop /leaderboard /referral /pro /premium
```

**DeFi/Agent paths:**
```
/api/vaults /api/yields /api/strategies /api/agents
/llms.txt /agent-card /agent-card.json
/.well-known/agent.json /.well-known/ai-plugin.json
/.well-known/openapi.json /openapi.json /agents.txt
```

Only report paths that return non-404 status codes.

### 4. JS Bundle Analysis

Extract URLs, API endpoints, and service references from JS chunks:

```bash
curl -s "<chunk_url>" | grep -oP 'https?://[^"'\'\s,\)\}]+' | sort -u
curl -s "<chunk_url>" | grep -oP 'wss?://[^"'\'\s,\)\}]+' | sort -u
curl -s "<chunk_url>" | grep -oP '"/api/[^"]+' | sort -u
```

Search for domain-specific patterns:
- **Auth:** cognito, supabase, firebase, clerk, auth0, privy, dynamic
- **Data:** birdeye, dexscreener, coingecko, defined.fi
- **Chains:** solana, ethereum, chainId, BSC, Base, Arbitrum
- **Wallets:** phantom, metamask, walletConnect, backpack
- **Features:** quickBuy, snipe, swap, slippage, amountSol, leverage, copy
- **Social:** twitter.com, x.com, discord.gg, t.me, github.com

### 5. Live API Probing

For discovered endpoints: hit health/status, try public data, check OpenAPI specs, inspect error responses.

### 6. External Intelligence (parallel)

```bash
web_search: "<domain>" OR "<project>"
curl -s "https://api.github.com/orgs/<name>/repos"
```

### 7. Content Files

Fetch discovered machine-readable files:
- `/llms.txt`, `/agents.txt`
- `/agent-card.json`
- `/.well-known/agent.json`
- `/openapi.json`
- `/robots.txt`

These often contain the most detailed technical information.

## Output Format

1. **What it is** — one-line summary
2. **Tech Stack** — frontend, backend, hosting, auth, data sources
3. **Features** — functionality from routes, JS, API probing
4. **Chains/Networks** — if crypto/DeFi related
5. **API Surface** — endpoints, live data samples
6. **Infrastructure** — hosting, DNS, registrar, IP geolocation
7. **Social/Public Presence** — GitHub, Twitter, Discord
8. **Interesting Findings** — stealth mode, exposed APIs, red/green flags
9. **Assessment** — stage, sophistication, comparable projects

Keep it dense and technical. Skip fluff.