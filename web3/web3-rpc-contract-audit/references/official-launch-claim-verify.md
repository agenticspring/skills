# Verifying "Official Launch / GitHub-Listed" Token Claims (real case: $UNIFROG, 2026-08-05)

When a tweet claims "token X is official — deployed with the address in project Y's GitHub", do NOT trust the screenshot. The claim is often a half-truth: the token was created *through* an official factory whose address IS in the repo, but the token address itself is NOT there, and the factory is permissionless (anyone can call it). This is the end-to-end recipe that produced a verified verdict.

## 1. Read the tweet without a browser

X is bot-walled and the local browser (Camofox) is often down. fxtwitter returns full JSON keylessly:

```bash
curl -s "https://api.fxtwitter.com/i/status/<id>"
# -> {"tweet": {"text": "...", "author": {"screen_name","followers","verification"}, "media": {...}, "created_at": ...}}
```

Also resolves the `t.co` links embedded in the text. Author metadata matters: follower count + verified flag calibrate how much weight the claim carries.

## 2. OCR the tweet screenshots (vision-model fallback)

When the active model has no image support, download media and OCR with tesseract:

```bash
curl -s -o shot.jpg "https://pbs.twimg.com/media/<media-id>.jpg?name=orig"
tesseract shot.jpg stdout
```

Recovered the exact GitHub snippet (`POSITION_MANAGER_ROBINHOOD = getAddress('0x58daec...')`) and the on-chain transfer trace (launcher → PositionManager → PoolManager) from the two screenshots. OCR text is dirty — treat as hints to verify against the real file/chain, never as proof.

## 3. Fetch the referenced GitHub file and grep BOTH the token AND infrastructure

```bash
curl -s "https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>" > /tmp/addr.ts
grep -i "<claimed-token-address>" /tmp/addr.ts          # usually NOT found
grep -E "0x[a-fA-F0-9]{40}" /tmp/addr.ts | head          # infrastructure addresses
```

Key insight: the tweet's screenshot usually shows an *infrastructure* address (Position Manager, factory) that IS in the file — while the *token* address is absent. That's the trick the claim relies on.

## 4. Check git history — did the address EVER exist?

```bash
curl -s "https://api.github.com/repos/<owner>/<repo>/commits?path=<file>&per_page=10"
# for each sha:
curl -s "https://raw.githubusercontent.com/<owner>/<repo>/<sha>/<path>" | grep -ci "<address>"
```

Zero hits across all recent commits = the address never lived in the repo. It was not "removed later".

## 5. Verify the on-chain creator (Blockscout v2)

```bash
curl -s "https://<chain>.blockscout.com/api/v2/addresses/<token>"
# -> creator_address_hash, creation_transaction_hash, is_verified, name
```

- Token name/symbol/decimals/supply via RPC `eth_call` (0x06fdde03 / 0x95d89b41 / 0x313ce567 / 0x18160ddd).
- If `creator_address_hash` == the factory listed in GitHub AND the factory is `is_verified: true` with the expected name → the launch genuinely went through official infrastructure.
- Same probe on the launcher/position-manager contracts: verified + correct name = official deploy.

## 6. Timeline triangulation ("launched earliest, this is first")

From Blockscout `/api/v2/transactions/<creation-tx>` get `timestamp` for:
- launcher/factory deploy time
- token creation time
- platform/frontend go-live (from news/teaser page)

UNIFROG case: launcher deployed 04 Aug 23:40 UTC → token created 05 Aug 01:16 UTC (1.5h later) → pools.trade frontend live 16:00 UTC same day. Token launched BEFORE the frontend went live = "first" claim holds (with caveats).

## 7. Decode the launch flow (internal txs)

```bash
curl -s "https://<chain>.blockscout.com/api/v2/transactions/<creation-tx>/internal-transactions"
```

Shows EOA → launcher (delegatecall) → factory (create2) → token. The strategy address called (e.g. `0x3f556B...`) maps to a name in the GitHub addresses file (`INSTANT_LAUNCH_STRATEGY_FEES_ON_ROBINHOOD_V311`). "Fees coin" claims = FEES_ON launch strategy, NOT token transfer tax — probing fee selectors on the token returns nothing, which is expected.

## Verdict logic

- **Infra legit ≠ token endorsed.** Official factory = permissionless; anyone can `createToken`. "Deployed with addy in GitHub" = "created through the factory whose address is in GitHub", NOT "the team deployed this token".
- **Deployer identity:** team deploys via CREATE2 deterministic factory (`0x4e59b448...` — the standard deployer) from a recurring deployer wallet; a fresh EOA funded hours before launch by a trader wallet = third-party permissionless launch.
- **Report both halves:** verified facts (repo real, factory verified on-chain, token created through it, first-launch timeline) AND the caveat (token address itself NOT in the repo; factory permissionless; any token can be created tomorrow).
- Dexscreener pair data (`/latest/dex/tokens/<addr>`) adds the market picture: age, liquidity, volume, price change — a +2600%/24h token is still in the pump window regardless of infra legitimacy.
