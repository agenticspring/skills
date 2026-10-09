# Debugging "button does nothing" / "no message appeared" in spring-trade

The user reports a button click produced no feedback. Do NOT take that at face value — verify
the code path actually runs and actually sends. In this session a "no message" report turned out
to be a valid message saying "not ready" (status `pending_confirmations`) that the user dismissed
as "nothing happened" — the bot WAS sending, the burn was just stuck at the Circle relayer.

## Reproduction recipe (proved `doClaim` ran + `a.send` fired)
1. Write a throwaway `cmd/<name>/main.go` that builds the REAL `App` and calls the handler
   method directly — no Telegram needed:
   ```go
   cfg, _ := config.Load()
   st, _  := store.Open(cfg.DataDir + "/spring-trade.db")
   cl     := evm.NewClients(cfg)
   box, _ := crypto.NewBox(cfg.MasterKeyB64)
   wsvc   := wallets.New(st, box)
   app, _ := tg.New(cfg, st, cl, wsvc, evm.NewNonceLock())
   app.DoClaimForTest(context.Background(), userID, chatID, burnTx) // exported thin wrapper
   ```
   - `config.Load()` returns `(cfg, err)`; `store.Open(path)` (NOT `store.New`); `wallets.New(st, box)`.
   - Export a `DoClaimForTest` wrapper on `App` (or whichever method) just for this; DELETE it before commit.
2. Add `log.Printf` at: handler entry, find-by-tx result, upstream query result, and EVERY
   `a.send` call (e.g. `log.Printf("[send] chat=%d text=%q", chatID, text[:min(80,len(text))])`).
3. Run with the bot's env: `set -a; source ~/.hermes/.env; set +a; go run ./cmd/<name>`.
   The log shows exactly which branch executed and whether `a.send` was reached.
4. REMOVE the throwaway cmd + the exported wrapper before committing.

## Confirm the upstream state independently
When the handler depends on an external API, curl it directly to see the real status:
- CCTP attestation: `GET https://iris-api.circle.com/v2/messages/{sourceDomain}?transactionHash={burnTx}`
  (domain for AVAX = 1). A `status: "pending_confirmations"` with a months-old burn means the
  Circle relayer never finalized — not a bot bug. The bot message "Attestation belum siap" is
  correct; the user just read it as "nothing happened".
- Confirm the source-chain tx is real: `eth_getTransactionByHash` on the chain RPC.

## Takeaway
"Silent button" is almost never silent code — it's either a blocking handler, a message-type
mismatch (text-edit on photo / photo-edit on text → silent fallback spawn), or a status message
the user didn't register. Reproduce + log + curl before concluding.
