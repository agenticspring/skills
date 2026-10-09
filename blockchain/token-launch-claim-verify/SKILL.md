---
name: token-launch-claim-verify
description: Verify token-launch claims from social shill posts.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Verification, Token Launch, Social Claims, EVM, GitHub, Memecoin]
---

# Token Launch Claim Verification

Verify shill tweets about newly-launched tokens whose claims sound technical: "deployed with the address in official GitHub", "launched earliest, this is first", "official Uniswap launcher". These posts mix TRUE infrastructure facts with misleading implications. The job is separating: (a) what is real on-chain, (b) what the claim actually proves, (c) whether the implication (token is special/endorsed) holds.

Distinct from `onchain-claim-verify` (fund-trace claims: bridge → exchange): here the claim is about a token's DEPLOYMENT provenance and launch priority.

## When to Use

- Tweet/post shills a token with a GitHub repo link or factory/launcher address as proof
- "This is the first token launched via <protocol> on <chain>"
- "Deployed with the address in their GitHub" — need to check what address actually lives in the repo
- Recon on a fresh memecoin before deciding to ape or skip (Dez's standard: verify before trust)

## Key Insight (the whole ballgame)

**An infrastructure address in an official repo is NOT the token address.** Factory/launcher/position-manager contracts are permissionless — ANYONE can call `createToken()` on an official factory. So "factory address appears in Uniswap's GitHub" proves the token used official infra, NOT that the token is official or endorsed. Always grep the repo for the TOKEN address itself; it is almost always absent, and that absence is the finding to report.

## Procedure

1. **Read the tweet without a browser.** `curl -s "https://api.fxtwitter.com/i/status/<id>"` returns JSON: full text, author, media URLs, stats. Fast, no X login, works when the browser stack is down. Extract: contract address, GitHub link, all media URLs.
2. **Grab the tweet's screenshots** (media URLs from fxtwitter) and OCR them with `tesseract <img> stdout` — they often contain the "proof" (GitHub code snippet, transfer trace). Vision models may be unavailable; tesseract is the reliable fallback.
3. **Check the GitHub file the claim cites.** `curl -s "https://raw.githubusercontent.com/<org>/<repo>/<branch>/<path>"` → save to /tmp → `grep -i <token-address>` and also list all `0x...` addresses. Then check git history: `curl -s "https://api.github.com/repos/<org>/<repo>/commits?path=<path>&per_page=10"` and grep each commit's raw file for the address — proves whether the token address EVER appeared.
4. **Verify the token on-chain.** RPC `eth_call` name/symbol/decimals/totalSupply, `eth_getCode` for code size. Then Blockscout (or explorer API) address endpoint: `creator_address_hash` + `creation_transaction_hash` identify the deploying factory — cross-check THAT against the repo, not the token address.
5. **Check launcher/position-manager deployment timeline.** Creator of the launcher contract (usually a deterministic CREATE2 deployer `0x4e59b448...`), deploy timestamp vs token creation timestamp. "First launch" = token created shortly after launcher went live AND no earlier pool/tx on the launcher — verify, don't trust the tweet's ordering.
6. **Trace the deployer EOA.** Fresh wallet funded hours before launch by an active trader = launchpad pattern, not a team wallet. `coin_balance`, first tx, funding source.
7. **Dexscreener for market state.** `https://api.dexscreener.com/latest/dex/tokens/<addr>` → chain, pair age, liquidity, MC, 24h vol/price change. Pair age matching token creation time confirms the launch moment.
8. **Cross-check MULTIPLE tweets about the same token.** Shillers disagree on launch ordering and even on which token is #2 — each names a different "second token" to pump their bag. Verify EVERY named token on-chain and build the TRUE timeline. (Real case: tweet A said UNIFROG→FRONG, tweet B said UNIFROG→FORK; on-chain showed FORK created 06:05 UTC, FRONG 08:21 — tweet A's ordering was wrong. The research-question tweet was more accurate than the shill.)
9. **Interpret "fees" claims via the protocol, not the token.** A tweet saying "first fees coin" usually means the LAUNCHER STRATEGY has fees (GitHub file has `INSTANT_LAUNCH_STRATEGY_FEES_ON/FEES_OFF_ROBINHOOD_*` pairs), NOT that the token has a transfer tax. Probe token fee selectors (`fee()`, `buyFee()`, `tax()`, `owner()`) → they return 0/absent for these launches. Grep the cited repo for `FEES_ON`/`FEES_OFF` to decode what "fees coin" actually means.
10. **Attribute the platform when the claim implies officialdom.** To check "is this the official launch platform?" use 3 signals in combination:
    - **Nameservers match the parent org's domain**: `dig +short <site> NS` == `dig +short <org>.com NS` (pools.trade shares `damian`/`gemma` Cloudflare NS with uniswap.org — strong ownership signal).
    - **Backend gateway under the org's domain**: JS root bundle leaks `VITE_ENTRY_GATEWAY_URL`/`VITE_WEBSOCKET_URL` (pools.trade → `entry-gateway.backend-prod.api.uniswap.org`, `/health` returns ok).
    - **CSP `connect-src` enumerates supported chains**: DeFi sites list every RPC they talk to (pools.trade: Robinhood, Ethereum drpc/blastapi, Unichain, Base).
    Note a privacy-registrar WHOIS (GoDaddy + Domains By Proxy) on a supposedly-official domain is a mild flag, NOT decisive — NS + backend gateway outweigh it.
11. **Check for a teaser/demo asset named after a token.** Official teaser media can leak which token the team showcased (pools.trade served `frong.mp4` on CloudFront, last-modified 2026-07-28 — a week BEFORE any launch — while the "first" token was UNIFROG). That mismatch is a finding: the showcased token and the launch-order token differ, implying insider/tester awareness or deliberate demo naming.
12. **Deliver verdict with the nuance.** State clearly: what's VERIFIED (repo real, factory real, token created via it), what's MISLEADING (token address not in repo; permissionless factory; deployer is random EOA), and the risk framing (fresh memecoin, low MC, huge % move).
13. **Trace the funding cluster ACROSS tokens.** When several tokens launch through the same factory, the shills name different "firsts" — the funder links them. For each deployer EOA, fetch incoming txs (`blockscout /addresses/<deployer>/transactions?filter=to`) and find who funded the wallet before launch (look at earliest/largest inbound, not the deployer's own sends). Same funder address across multiple deployers = ONE operator cluster behind several tokens. (Real case: POOLS and UNIFROG deployers were both funded by `0xf70da978...` — a link no tweet mentioned.) This reveals the operator and lets you rank which token in the cluster is the "main" one.
14. **Rank candidates by launch-generation + name + fee-beneficiary.** When evaluating which token is the likely official/insider one: (a) check WHICH launcher generation it used (old `LiquidityLauncher` vs new `LIQUIDITY_LAUNCHER_ROBINHOOD` — the file pins both; "first" claims must be scoped per-launcher); (b) a token whose name/symbol matches the platform itself (POOLS/"pools.trade") launched BEFORE the platform's public launch date is the strongest candidate; (c) a deployer actively calling `collectFees` on the repo's `INSTANT_LAUNCH_FEE_SPLITTER_FEES_ON_*` address is the fee-beneficiary/creator pattern — that's who actually profits from the launch. Also check whether the deployer still holds: deployer ABSENT from top holders = already realized profit (risk signal).
15. **Keep the platform-frontend thread for attribution.** If the claim implies an official platform, recon the website too: `dig NS` vs parent org, JS root bundle for `VITE_ENTRY_GATEWAY_URL`/`VITE_WEBSOCKET_URL`, CSP `connect-src` for chains, subdomain enum (`dev.`/`staging.` resolving to separate ELBs = real infra), and CloudFront/S3 asset probing (a teaser video named after one token leaks which token the team showcased, and its `last-modified` date can PREDATE all launches — a finding).

## Quick Reference

```bash
# Tweet JSON (no browser)
curl -s "https://api.fxtwitter.com/i/status/<id>"

# Screenshot OCR
tesseract /tmp/img.jpg stdout 2>/dev/null

# Raw GitHub file + address grep
curl -s "https://raw.githubusercontent.com/<org>/<repo>/main/<path>" > /tmp/f.ts
grep -i "<tokenaddr>" /tmp/f.ts || echo "TOKEN ADDRESS NOT IN REPO"
grep -oE "0x[a-fA-F0-9]{40}" /tmp/f.ts | sort -u

# Commit history for the file
curl -s "https://api.github.com/repos/<org>/<repo>/commits?path=<path>&per_page=10"

# Token metadata (Robinhood chain example)
RPC=https://rpc.mainnet.chain.robinhood.com
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"<token>","data":"0x06fdde03"},"latest"]}' $RPC

# Blockscout address (creator + creation tx)
curl -s "https://robinhoodchain.blockscout.com/api/v2/addresses/<addr>"

# Dexscreener
curl -s "https://api.dexscreener.com/latest/dex/tokens/<addr>"
```

## Pitfalls

- **"Address in GitHub" is ambiguous by design.** Grep the repo for the TOKEN address; the shill's screenshot usually shows a FACTORY/POSITION-MANAGER address (which IS in the repo). Both claims can be technically true while the token is still a random permissionless launch. Report both halves.
- **Blockscout v2 pagination is flaky.** `?page=N` returns 422 on some endpoints; the `total` field is often None. Pull what you can from page 1 + the address endpoint instead of looping pages.
- **Blockscout needs FULL tx hashes.** `transactions/<hash>` 422s on truncated hashes. Get the full hash from the tx list endpoint (`items[].hash`) before fetching details.
- **`created_contract` on a tx ≠ the token.** A factory deploy tx may show a different created contract than the token address (token is created in an internal/factory call). Use the TOKEN's address endpoint `creator_address_hash` for provenance.
- **Total supply in hex.** `0x33b2e3c9fd0803ce8000000 / 1e18 = 1e9` — do the math; memecoins often report 1B not 10B.
- **Vision model may be unavailable** — don't stall; tesseract handles code-snippet screenshots fine.
- **Deploy wallet via CREATE2 factory** (`0x4e59b448...`) is the deterministic-deployer standard used by real protocol teams — its presence is expected, not proof of a scam.
- **Twitter timeline ≠ launch timeline.** Different shillers name different "second tokens". On-chain creation timestamps are the only truth. A token named by a research-question tweet (author openly says "not confirmed, please verify") can be MORE accurate than a shill — evaluate each tweet's claim on-chain, not by account size or verification badge.
- **"Fees" does not mean transfer tax.** For launcher-protocol tokens it means the launch strategy had fees enabled (`FEES_ON` variant in the repo). Probing token `fee()`/`tax()`/`owner()` selectors returns nothing on these uERC20 tokens — don't report "no fees" as suspicious.
- **Official-platform attribution needs 3 signals together.** NS match with the org's main domain + backend gateway under the org's domain + CSP connect-src listing the org's RPCs. A privacy registrar (GoDaddy + Domains By Proxy) is common for stealth launches and alone proves nothing either way.
- **"First" must be scoped to the launcher generation.** The repo pins BOTH an old `LiquidityLauncher` and a new `LIQUIDITY_LAUNCHER_ROBINHOOD` (deployed later). A token launched a week earlier via the OLD launcher (e.g. POOLS, 30 Jul) predates the "first via new launcher" token (UNIFROG, 5 Aug) — both "first" claims can be true simultaneously. Check which launcher address is in the token's creation tx trace (`internal-transactions` shows `delegatecall` from the launcher + `create2` from the factory).
- **Deployer-dumped signal.** When the deployer EOA is absent from the token's top-50 holders list, they already sold/moved their position. For an "official/insider" narrative that is a strong risk flag — report it alongside the bullish provenance facts.
- **Oldest + platform-named ≠ confirmed official.** The token named exactly like the platform (POOLS/"pools.trade") that launched pre-public-launch is the strongest candidate, but still no explicit team confirmation exists. Frame it as "highest-probability candidate", never "confirmed by the team".

## Verification

The verdict rests on ONE command proving the discriminator:

```bash
grep -i "<token-address>" /tmp/addresses.ts && echo "TOKEN IN REPO" || echo "TOKEN NOT IN REPO — infra-only claim"
```

Plus the on-chain chain: token `creator_address_hash` == the factory address listed in the repo (verified infra), while the token address itself is absent from the repo (not endorsed). That combination — real infra, permissionless launch, random deployer — is the standard finding for these shills.

## References

- `references/unifrog-case-2026-08.md` — full worked example: $UNIFROG "deployed with addy in Uniswap GitHub" claim, exact addresses, timelines, verdict.
- `references/pools-trade-followup-2026-08.md` — follow-up same day: multi-tweet cross-check ($FORK, $FRONG), "fees strategy" decode, pools.trade site attribution (NS match, backend gateway, CSP chains, frong.mp4 teaser leak).
- `references/pools-token-analysis-2026-08.md` — the $POOLS (pools.trade-named) token: oldest launcher token, funding-cluster trace (same funder as UNIFROG), launcher-generation scoping, deployer-dumped signal.
