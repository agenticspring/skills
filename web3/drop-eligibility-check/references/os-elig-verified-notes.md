# os-elig CLI — verified session details (2026-08-17)

## Origin

Wrapper around the open-source Telegram eligibility bot
(`Juuju1/Check-Opensea-Eligible-With-Telegram-Bot`) stripped of its Telegram
polling loop, adapted to derive wallet keys in memory from the Hermes mnemonic
file. Project: `/root/projects/os-elig-bot/`. Global command: `/usr/local/bin/os-elig`.

## Audit summary of the bot module

- Endpoints: `opensea.io/__api/auth/siwe/nonce` + `/verify`, `gql.opensea.io/graphql`,
  `api.opensea.io/api/v2/drops` + `/collections`, `scatter.art/api/trpc`,
  `rpc.mainnet.chain.robinhood.com`, Telegram API (unused in CLI), Coinbase/CoinGecko
  (ETH/USD price display).
- No private-key exfiltration: PKs are only used locally for SIWE signing.
- Original expects `~/wallets.csv` (`name,address,private_key`); CLI runner
  bypasses that by deriving from `/root/.hermes/.credintial/.springwallet`
  (Set 1..100) with ephemeral `/dev/shm` temp files.

## Verified case: Mythborn (2026-08-17)

- Target: `mythborn-735638242`, contract `0x92ed183381e7ac64ad5e34222658fb788f369425`
  (minimal proxy 45-byte; implementation `0x09a26fc8fcef18192e267d7a6da9dfb4be81dd`).
- Drop stages from `/api/v2/drops/mythborn-735638242`:
  - Team signed_presale: price 0, max 100, 15:00-15:10Z
  - OG Mythborn signed_presale: price 0.0001 ETH, max 2, 15:10-15:40Z
  - FCFS Mythborn signed_presale: price 0.00015 ETH, max 3, 15:40-16:10Z
  - Public Mythborn: price 0.0002 ETH, max 7, 16:10Z+
- Result: Set 1 (and Sets 1-15 sampled) `PUB elig=[] pub=['Public Mythborn']` —
  only the public stage is eligible, no signed/whitelist stage.
- `os-elig mythborn-735638242 1` reproduces in ~5s.

## Scatter path verification

- `os-elig https://www.scatter.art/c/<slug> 1` reaches the Scatter trpc and RH
  RPC; a non-existent slug returns `HTTP Error 404`, an existing collection
  with no on-chain list returns `no stages`. No SIWE needed.

## Module function map (for manual fallback)

- `bot.parse_link(text)` → `{"source": "opensea"|"scatter", "slug": ...}`
- `bot.fetch_drop_stages(slug)` / `bot.fetch_collection_meta(slug)` — OpenSea API
- `bot.siwe_login(address, pk)` → httpx client with OpenSea access_token cookie
- `bot.check_eligibility_graphql(client, wallet, slug)` — DropEligibilityQuery
- `bot.check_one_wallet(w, slug, api_stages)` — full per-wallet check
- `bot.scatter_fetch_collection(slug)` / `bot.check_one_wallet_scatter(w, info)`

## Rate-limit notes

- Without proxies the bot reduces SIWE concurrency to 2 (serial-ish); the CLI
  runner sleeps 0.35s between wallets.
- OpenSea API key rate limits are shared per account bucket; don't create many
  keys to multiply capacity.
