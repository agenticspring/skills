---
name: token-launch-verify
description: Verify if a tweeted token is official or sybil-launched.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Web3, Recon, Token, Onchain, Verification]
---

# Token Launch Verification

Distinguishes a legitimately-official token (deployed by the named team) from a sybil/bot launch that only *looks* official. The classic trap: the infrastructure contracts are real (Uniswap factory, launcher), but the token itself was created by a bot-farm operator who front-ran the launch. This skill verifies claims in tweets: GitHub references, contract ownership, funding paths, and holder behavior — then separates "infra is legit" from "token is official".

Does NOT audit contract code for exploits. Uses passive lookups only: tweet APIs, GitHub, RPC `eth_call`, block explorer APIs, market APIs, OCR.

## When to Use

- "Recon token ini" / "Analisa token ini" / "Apakah token ini resmi?"
- A tweet claims a token was "deployed with the address in GitHub" or "launched earliest / this is first"
- New platform/launchpad launches and tokens appear before the official frontend goes live
- Need to determine if a contract address is the *official* one vs a squatted/sybil one
- Verifying funding-path connections between multiple token deployers

## Prerequisites

- `tesseract` for OCR of tweet screenshots (`apt-get install -y tesseract-ocr`)
- `ffmpeg` + `ffprobe` for video teaser analysis (`apt-get install -y ffmpeg`)
- `whois`, `dig`, `curl` (standard)
- No API keys required — all sources are public endpoints

## How to Run

Invoke through the `terminal` tool: `curl` for tweet/GitHub/market APIs, RPC POSTs, `dig`/`whois` for infra. Use `execute_code` for multi-step logic (paginated checks, pattern matching). Use `vision_analyze` for screenshots when the active model has vision; otherwise fall back to `tesseract` via `terminal`.

## Quick Reference

```bash
# Tweet content (bypasses X bot-wall, no auth)
curl -s "https://api.fxtwitter.com/i/status/<TWEET_ID>"

# GitHub file + history
curl -s "https://raw.githubusercontent.com/<org>/<repo>/main/<path>"
curl -s "https://api.github.com/repos/<org>/<repo>/commits?path=<path>"
curl -s "https://raw.githubusercontent.com/<org>/<repo>/<commit_sha>/<path>"

# Chain registry (find RPC + explorer for unknown chain)
curl -s "https://chainid.network/chains.json"

# ERC-20 reads (RPC eth_call selectors)
# name() 0x06fdde03, symbol() 0x95d89b41, decimals() 0x313ce567, totalSupply() 0x18160ddd
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"<TOKEN>","data":"0x06fdde03"},"latest"]}' \
  "<RPC_URL>"

# Blockscout v2 API (use FULL hashes, pagination broken)
curl -s "https://<explorer>/api/v2/addresses/<ADDR>"
curl -s "https://<explorer>/api/v2/addresses/<ADDR>/transactions?filter=to"   # incoming
curl -s "https://<explorer>/api/v2/addresses/<ADDR>/transactions?filter=from" # outgoing
curl -s "https://<explorer>/api/v2/addresses/<ADDR>/counters"                  # tx totals
curl -s "https://<explorer>/api/v2/tokens/<TOKEN>/holders"
curl -s "https://<explorer>/api/v2/transactions/<FULL_TX_HASH>/internal-transactions"

# Market data
curl -s "https://api.dexscreener.com/latest/dex/tokens/<TOKEN>"

# OCR a tweet screenshot
curl -s -o /tmp/img.jpg "https://pbs.twimg.com/media/<MEDIA_ID>.jpg?name=orig"
tesseract /tmp/img.jpg stdout 2>/dev/null

# Domain infra
dig +short <domain> NS A CNAME TXT; whois <domain>
```

## Procedure

1. **Fetch the tweet.** `curl -s "https://api.fxtwitter.com/i/status/<ID>"` — parse author, followers, verification, full text, media list, timestamps. Note tweet time in UTC; a claimed "first launch" must be checked against on-chain creation time.

2. **OCR any screenshots.** Download media from `pbs.twimg.com/media/<id>?name=orig` via `terminal` curl, then `tesseract` each image. Screenshots of GitHub files must match the live repo, not just look right.

3. **Verify GitHub claims.** If the tweet links a repo/file: fetch the raw file with `curl` (raw.githubusercontent.com), grep for the token address. ALSO fetch recent commits for that path and grep a few historical SHAs — the address may have been added then removed. Key distinction: infra addresses (factory/launcher/PositionManager) being in the repo ≠ the token itself being in the repo.

4. **Identify the chain + RPC.** Check `chainid.network/chains.json` if unknown. For Robinhood Chain: chainId 4663, RPC `https://rpc.mainnet.chain.robinhood.com`, explorer `https://robinhoodchain.blockscout.com`.

5. **Read token basics on-chain.** RPC `eth_call` for name/symbol/decimals/totalSupply. Confirms the contract is live and what it claims to be.

6. **Get creator + creation tx.** Blockscout `/api/v2/addresses/<TOKEN>` → `creator_address_hash`, `creation_transaction_hash`, `is_verified`. Then the creation tx's `/api/v2/transactions/<HASH>` for `from`, `to`, `timestamp`, `method`, and `/internal-transactions` for the deploy flow (create2 → factory → token). If created via a factory that IS in the official repo, note that the factory is permissionless — anyone can call it.

7. **Check market data.** Dexscreener: pairs, chain, dex label (v4/v3), volume, liquidity, FDV, price change, pair creation time. Cross-check pair age vs token creation.

8. **Trace the deployer's funding.** Blockscout `transactions?filter=to` on the deployer EOA — find who funded them and WHEN relative to the token creation (funding 1-2h before launch = coordinated). Check `counters` for total transaction volume.

9. **Detect bot/sybil operators.** A deployer's funder with 100K+ transactions and millions of token transfers is an automated bot farm, not a team wallet. Check for vanity address pairs: two addresses sharing a long common substring (e.g. 32 of 40 chars) = deliberately crafted by one operator. Real team wallets are usually simple EOAs or multisigs, not high-frequency bots.

10. **Cross-link multiple tokens.** If several tokens appeared around the same launch, check whether they share the same funder (same cluster) or came from different entities. Cluster-funded tokens are sybil plays; independently-funded ones may be separate actors.

11. **Recon the official platform.** For launchpad claims: `dig`/`whois` the domain, fetch the homepage HTML, inspect JS bundles for env vars (`VITE_*`), CSP `connect-src` headers (reveal which RPCs/backends the real app uses), and CloudFront/S3 assets (teaser videos often leak codenames). Compare NS servers with the official org's other domains.

12. **Synthesize.** Separate three claims: (a) infra is official, (b) token is the official one, (c) "first launch" narrative. (a) can be TRUE while (b) is FALSE — that is the whole point of this skill.

## Pitfalls

- **Blockscout v2 pagination is broken** (`?page=N` → HTTP 422). Use `filter=to`/`filter=from` and `counters` instead; page 1 holds the newest 50.
- **Blockscout requires FULL transaction hashes.** A prefix like `0xedbded...` returns 422. Always extract the full hash from list endpoints first.
- **Public RPC rate-limits aggressively** (HTTP 403 on bursts). Space `eth_call`s out or re-issue after a pause.
- **`vision_analyze` may have no vision support** on some models ("image omitted"). Fall back to `tesseract` — always available and reliable for address/text extraction.
- **"Uniswap v4" dex label ≠ official token.** Dexscreener labels the pool by protocol, not by who launched it.
- **Infra addresses in GitHub ≠ token endorsement.** Grep the actual token address; finding only factory/launcher addresses proves infra, not ownership.
- **Fresh domains invisible to search engines.** A domain registered 2 weeks before launch with matching NS to the official org is normal for stealth pre-launch — don't call it fake for being new.
- **A 200 HTTP status proves nothing about legitimacy.** WHOIS, NS comparison, and JS/CSP analysis are the discriminators.

## Verification

```bash
# Proves the token is real + who created it (the core of the skill):
curl -s "https://robinhoodchain.blockscout.com/api/v2/addresses/<TOKEN>" | python3 -c "import json,sys; d=json.load(sys.stdin); print('creator:', d.get('creator_address_hash'), '| verified:', d.get('is_verified'))"
```

A real result shows a creator address (often the factory) and `is_verified: true`; combined with the funding trace and deployer tx counts from Procedure steps 8-9, this is enough to classify official-vs-sybil.
