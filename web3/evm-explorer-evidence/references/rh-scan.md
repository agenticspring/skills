# RH-scan Adapter Notes

## Verified identity

- Base URL: `https://rh-scan.xyz/`
- Chain ID: `4663`
- Network: Robinhood Chain
- Clean links:
  - `https://rh-scan.xyz/tx/<full-hash>`
  - `https://rh-scan.xyz/address/<checksum-address>`
  - `https://rh-scan.xyz/token/<contract>`

## Confirmed routes

```text
GET /api/home
GET /api/gas
GET /api/search?q=<query>
GET /api/internal/export/status
```

`/api/home` returns head/finalized/safe blocks, price/gas metadata, recent blocks, and recent transactions. `/api/search` returns typed resolution for an address, transaction, block, or token. `/api/gas` returns gas/price metadata.

## Unsupported assumptions

The following standard-looking routes returned not-found responses during the reference inspection and must not be assumed to work:

```text
/api/v2/*
/api?module=...
/openapi.json
/api-json
```

If the site changes, inspect its current Next.js chunks or API docs to rediscover routes.

## Reporting rule

The `rh-scan.xyz` host was later observed failing DNS. Do not report its links without rechecking the exact URL at report time. Current fallback tested for the Bozo Hood transaction: `https://robinhoodchain.blockscout.com/tx/<full-hash>` returned HTTP 200. Use direct RPC for receipt status, logs, ownership, balances, nonce, and gas. If an explorer page shows `—` while RPC has a confirmed receipt, report `indexer_lag` and include the RPC proof plus only a live-verified explorer URL.
