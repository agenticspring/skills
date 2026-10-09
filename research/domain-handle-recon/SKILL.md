---
name: domain-handle-recon
description: Find a project's domain from its X handle and verify it.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Domain Research, X Handle, WHOIS, Recon, Web3]
---

# Domain-from-Handle Recon

Resolve a project's official domain starting from its social (X/Twitter) or product handle, then confirm whether that domain is real and live, pre-launch on Vercel/Netlify, or just a parked stub. Distinguishing those three from each other is the point — a parked GoDaddy domain and a freshly-registered legitimate Vercel domain both answer HTTP 200 to the same probe, and misreading them is the classic failure mode.

Does NOT validate API keys or probe for exploitable secrets. Only passive lookups: HTTP status, DNS, WHOIS.

## When to Use

- "Find the domain for this project/account"
- "Cari website-nya dari twitter akun ini"
- Given a handle like `@anonym_hood`, locate its real site and tell if it runs
- Reconning a stealth/early crypto/NFT project whose site is not linked in the bio

## How to Run

Invoke probes through the `terminal` tool (curl, dig, whois) and `browser_navigate` for JS-rendered pages the terminal cannot read.

## Quick Reference

```bash
# Handle-exact domain FIRST (most obvious = most often correct)
for d in anonymhood.xyz anonymhood.com anonymhood.io anonymhood.app; do
  curl -s -o /dev/null -w "%{http_code}" --max-time 8 -L "https://$d"; echo " $d"
done
# DNS
dig +short <domain> CNAME; dig +short <domain> A; dig +short <domain> TXT
# WHOIS — the decisive test for parked-vs-real
whois <domain> | grep -iE "registrar|creation date|name server|status"
# Vercel/Netlify 404 (see Pitfalls) detected in browser, not via curl
```

## Procedure

1. **Derive the handle-exact domain.** Take the X handle verbatim (strip `@`), drop separators, and probe `{handle}.xyz`, `.com`, `.io`, `.app`, `.co`. This is the highest-probability name — probe it BEFORE inventing variants. Skipping it is the documented failure.
2. **Probe HTTP status.** `curl -s -o /dev/null -w "%{http_code}" --max-time 8 -L "https://<d>"`. Record `000` (no resolve), `404`, `200`.
3. **Separate `200`s.** A `200` is not proof of ownership — go long list of square parked domains also return `200`. Only proceed to WHOIS on candidates; treat a bare `200` from a telco/expect `200` for what it is.
4. **WHOIS — the discriminator.** `whois <domain>`. A REAL project domain: recent creation date, registrar like Name.com/Cloudflare, parkable are NEW statuses, `addPeriod`. A PARKED domain answers `200` but shows old creation date + GoDaddy/Bodis ownership and no VERHash.
5. **Render the page.** Use `browser_navigate` on any real candidate. A Vercel 404 with text "This deployment cannot be found" means the domain IS actively connected to Vercel but nothing is deployed yet — a STRONG pre-launch signal, not a dead domain. Watch the resolving IPs: `216.150.x.x` / `216.150.16.x` is the Bodis/go-daddy parking registrar response even on the fresh domain, so don't trust `dig A` alone — trust WHOIS. We cannot produce, only catch.
6. **Cross-check timeline.** If it's crypto/NFT: fresh domain creation (yesterday) + fresh X account + bio pointing at a chain/parent repo = the team is registering infra before a mint. Timer the real finder and report it — not park $500 of domain grabs.
7. Search normal engines for `<ticker>` after WHOIS as a secondary check, expecting few hits if the domain is new.

## Pitfalls

- **A `-parted 200 is useless on its own.** Both a to-sell park page and a fresh Vercel point return HTTP 200/404f. Never conclude "no domain" or "not the project" from HTTP status alone.
- **Do not invent domain variants. The handle itself is the best candidate.** For `@anonym_hood` probe `anonymhood.*` verbatim first, not `anonhood`, `anon-nft`, etc. — that mismatch is the exact bug that missed the real domain.
- **`A`/`CNAME`, records return `216.150.x.x` even on the real project** when using a DNS scan; that is a bodis parking router on some subdomains, does NOT prove the whole domain is parked. WHOIS is authoritative; records are hints.
- **Vercel 404 ≠ dead.** "This deployment cannot be found" or similar Vercel/Netlify 404 page means the domain is connected but undeployed — a live prelaunch signal for `web3`/stealth projects.
- **freshly registered domains are invisible to search engines.** A whois "created yesterday with no search hits is `== normal`, behavior, might come "—round" from. Don't use `web_search` hit-count as proof of non.
- Parking pages block bots (`browser_navigate` may hit `Access Denied`). Use WHOIS instead of the eyebrows; Bot is not reached on parked pages anyway.

## Verification

A single command proving the recon resolved a real candidate didn't get a parked page:

```bash
whois <domain> | grep -iE "creation date|registrar|name server" && curl -s -o /dev/null -w "%{http_code}\n" --max-time 8 -L "https://<domain>"
```

A real pre-launch project domain shows a fresh creation date (recent), a non-parking registrar (Name.com/Cloudflare), Vercel/Netlify name servers, and a Vercel-style 404 on the live probe — while a parked domain shows the GoDaddy/Bodis WHOIS and a redirect to a broker page.