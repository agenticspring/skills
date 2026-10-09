# CCTP V2 Bridge Claim — Iris status reference

Debugging a "claim does nothing" report revealed the bot was working; the burn
was simply not claimable yet. Capture the real upstream semantics so future
sessions don't misdiagnose.

## Endpoint
`GET https://iris-api.circle.com/v2/messages/{sourceDomain}?transactionHash={burnTx}`
- mainnet → `https://iris-api.circle.com`
- testnet → `https://iris-api-sandbox.circle.com`
- CCTP source domains: Ethereum=0, Avalanche=1, Optimism=2, Arbitrum=3, Base=6, Polygon=7 (Arc is the DESTINATION, domain 26).
- The `fetchMessage` helper returns `nil, nil` on HTTP non-200 (treats 404 as "not indexed yet").

## `status` field values (from `irisMessage.Status`)
- `pending_confirmations` — burn tx mined but Circle relayer has NOT finalized it yet. Attestation not generated. **Claim is impossible.** Normal for fresh burns (1–2 min); if it PERSISTS for months, the forwarding route for that source→Arc pair is stuck/unsupported and Iris is holding. NOT a bot bug.
- `complete` / ready — attestation available; `message` + `attestation` fields populated; manual claim (`receiveMessage` on Arc) can proceed.
- `forwarded` / has `forwardTxHash` — Circle already minted on Arc automatically (forwarding succeeded); burn should be marked completed, manual claim unnecessary.

## `GetAttestationOnce` return shape
`cctp.AttestationResult{ Ready bool, AlreadyMinted bool, Status string, Message string, Attestation string, ForwardTxHash string }`.
- `Ready=false` → bot sends "Attestation belum siap (Status: X)". That message IS the feedback — user may think "nothing happened" but it's correct.
- `AlreadyMinted=true` → mark completed, tell user forwarding already landed.

## Debug recipe for a burn
1. `curl` the endpoint above with the real burnTx + correct sourceDomain from `burns.source_domain`.
2. Cross-check the burn tx on the source-chain explorer (e.g. AVAX `https://api.avax.network/ext/bc/C/rpc`, `eth_getTransactionByHash`) to confirm it actually mined (not reverted). A valid mined burn that stays `pending_confirmations` for months = route stuck, not fixable from the bot.
3. Compute burn age: `now - burns.created_at` (unix sec). If >10 min and still pending, message should hint "rute forwarding gangguan, cek menu 📡 Rute".

## DB
- `data/spring-trade.db` (bot data dir). Table `burns`: `burn_tx, source_key, source_domain, status, transfer_amount, created_at`.
- `FindBurnByTx(tx)` returns `(nil, nil)` if not found — handle `b == nil` distinctly from a real DB error.
