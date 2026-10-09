# Blockscout v2 API Quirks (verified 2026-08, eth.blockscout.com)

## Endpoints
- `GET /api/v2/addresses/{addr}` — balance (`coin_balance`, wei), `is_contract`, `has_tokens`, `has_token_transfers`
- `GET /api/v2/addresses/{addr}/counters` — `transactions_count`, `token_transfers_count`
- `GET /api/v2/addresses/{addr}/transactions` — native txs (do NOT use `?filter=to|from`; enum rejects pipe syntax)
- `GET /api/v2/addresses/{addr}/token-transfers?type=ERC-20,ERC-721`

## Gotchas

1. **type filter is comma-separated, NOT URL-encoded pipe.** `?type=ERC-20%7CERC-721` fails with a regex-cast error. Correct: `?type=ERC-20,ERC-721` (comma needs no encoding).
2. **Responses can contain raw control characters** inside string fields (token metadata etc.), which breaks Python `json.loads`. Fix: strip before parsing — `re.sub(r'[\x00-\x1f]+', ' ', raw)`. If parsing still fails on large pages, fall back to regex extraction per item (`"symbol":"..."`, `"timestamp":"..."`, `"method":"..."`, `"from"/"to"` hash).
3. **Etherscan V1 api.etherscan.io endpoints are deprecated** (return NOTOK "switch to V2"). Etherscan V2 multi-chain requires chainid param but does NOT support all chains (RH 4663 not supported). Blockscout needs no API key — prefer it for quick recon.
4. **Empty wallet ≠ no history**: check both `coin_balance == "0"` AND `has_tokens`/counters; some wallets hold dust but zero txs.
5. Method field in token-transfers shows raw selector (`0xa9059cbb` = transfer, `0x87201b41` = safeBatchTransferFrom-style, `0x161ac21f` = mint-from-zero-address claim); `via=mint` or counterparty `0x000...000` means the wallet minted natively.

## Arkham specifics
- arkm.com visualizer pages are fully login-gated (Turnstile). web_extract returns only the login page.
- The link's `positions` query param still names labeled entity nodes (binance, stake-com, opensea, relay-link, zero-address) — free context without access.
