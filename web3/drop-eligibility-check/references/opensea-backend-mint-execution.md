# OpenSea Backend-Signed Mint + Batch Execution (2026-08-30)

Follow-on to eligibility: how to actually MINT an eligible signed-presale
(GTD/WL) drop. Key discovery that contradicts earlier assumptions — you do
NOT self-sign vouchers for drops whose signer key lives at OpenSea. You
SIWE the wallet into OpenSea, POST their mint builder, and OpenSea's backend
returns ready-to-broadcast calldata (they hold the signer).

## Flow that works (proven on Onchain Sketches)

1. SIWE login the wallet (per-wallet, each wallet is its own OpenSea account).
2. Set the `connected-account-server-hint` cookie (same fix as eligibility).
3. `POST https://api.opensea.io/api/v2/drops/{slug}/mint`
   headers: `X-API-KEY: <key>` + SIWE session cookies
   body: `{"minter": "<wallet>", "quantity": N}`
4. 200 → response `{"to", "data", "value", "chain"}` = signed calldata.
   Broadcast it yourself via `cast send <to> --data <data> --value <value>`.
   OpenSea's backend did the EIP-712 voucher signing server-side.
5. Do NOT use `opensea.io/__api/drops/...` — that path returns SPA HTML.
   The real endpoint is `api.opensea.io/api/v2/drops/{slug}/mint`.

## Response semantics (learned live)

| Status | Meaning |
|---|---|
| 200 | mint tx built; broadcast it |
| 401 | `Missing an API Key` — need `X-API-KEY` header, not just SIWE |
| 409 | `Drop is not currently active for minting` — endpoint valid, stage not open yet |
| 422 | `Drop is fully minted out` — supply gone (3333/3333 happened <8 s after WL open) |
| HTML body | wrong base path (`/__api/` instead of `/api/v2/`) |

## Auto-mint scheduler pattern

- Cheap probe: `GET /api/v2/drops/{slug}` and read `active_stage` /
  `is_minting`. NO SIWE needed for probing — do NOT SIWE-login per poll or
  you'll be rate limited within minutes (probe 5-30 s apart is fine).
- Probe must be **stage-aware**: check the target window by epoch
  (`WL_START <= now <= WL_END`) AND/OR `active_stage.label` contains the
  expected stage (e.g. "WL"). Naive "is any stage active?" fires on the
  wrong stage (e.g. GTD when you want WL) and every wallet fails.
- Only SIWE-login once the drop reports active, then run all wallets in
  parallel (ThreadPoolExecutor 4-5) — sequential per-wallet SIWE ≈15 s each,
  parallel ≈ 3× faster.
- One retry (sleep 2 s) on transient broadcast failure.
- Oversubscribed drops (WL count >> supply) sell out in the first seconds of
  the stage — polling at 10 s + per-wallet SIWE will be too slow to win.
  Treat "fully minted out" as the likely outcome and set expectations.

## Gas funding math (used for the $1/wallet distribution)

- ETH spot from CoinGecko `simple/price?ids=ethereum`.
- $1 = total_hub_balance/10 for a 10-wallet spread; send exact wei per wallet.
- RH gas is ~0.16-0.17 gwei; a plain value transfer costs ~21000 gas ≈
  0.0000035 ETH ≈ $0.000009 — negligible vs the $1 amounts.

## Scripts

- `/tmp/batch_ocs_elig.py` — eligibility batch (mnemonics → SIWE → GraphQL).
- `/tmp/ocs_os_mint.py` — OpenSea-backend mint: SIWE → POST mint → broadcast,
  `--watch` mode polls cheaply until the stage opens, `--parallel N`.
- Both read `/root/.hermes/.credintial/.springwallet` ("Set N" header +
  mnemonic) and `/tmp/ocs_wallets.json` (100 addresses, index 0 = Set 1).
- Per-wallet PK derivation needs
  `Account.enable_unaudited_hdwallet_features()` before `from_mnemonic`.
