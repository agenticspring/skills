# Isolated Dev Bot + SniperX Safety Notes

## Verified dev runtime invariant

For this bot class, a named `screen` session is not evidence that the process is alive. After every start, prove all of:

```text
screen window name signals RUNNING
PID exists
/proc/<pid>/cwd is the intended dev root
/proc/<pid>/exe is the intended dev binary
startup log has a fresh `bot mulai`
no fatal/panic/getUpdates conflict after that startup marker
```

Use an isolated launcher that `cd`s to the project and `exec`s the exact binary. `exec` matters: the screen child must become the Go bot, not leave an idle shell that looks alive.

```bash
screen -dmS dezbot-dev -t DEVBOT-RUNNING \
  bash -lc 'exec /root/dezbot-dev/scripts/run-dev-bot.sh'
```

Keep production process/session untouched. Never infer a running dev process from an old screen ID or old log line.

## SniperX CCTP completion gate

An automated post-bridge buy is eligible only after all of:

```text
Iris returns forwardTxHash
Arc transaction receipt is successful and canonical with configured confirmations
recipient Arc USDC balance is greater than the durable pre-burn balance baseline
explicit target has a durable idempotency claim keyed by burnTx + recipient wallet + token
```

Do not trigger on route liveness, Iris indexing, `pending_confirmations`, attestation-ready, or `forwardTxHash` alone.

## One-shot auto bridge intent

Persist source chain, amount, chat ID, and status. State transition is:

```text
armed --(forwarding route live)--> fired --> burn attempts
armed --(user OFF)--> cancelled
```

Mark `fired` atomically before the external burn attempt. Do not implement a boolean loop that repeatedly bridges a balance.

## Per-target auto-buy amount

Store the amount with each target, not as a global automation amount:

```text
target: user_id, chain, token, symbol, amount_usdc
buy claim: burn_tx, recipient wallet, token
```

UI should let the user add `CA SYMBOL AMOUNT_USDC` and edit each target's amount independently. Parse and validate a positive finite amount before persistence.

## Wrapped-native execution pitfall

A quote asset may be WETH while execution should be native ETH. Keep this distinction explicit in the selected route:

```text
quote: WETH -> token (QuoterV2)
buy execution: native ETH msg.value -> router payable path
sell execution: token -> router -> WETH unwrap -> native ETH
```

Do not take the generic ERC-20 execution path for wrapped-native buy routes; it can produce unnecessary WETH approvals and `SafeTransferFrom` failures.

## Revert classification

Do not collapse all revert selectors into slippage:

```text
Too little received / INSUFFICIENT_OUTPUT_AMOUNT -> price/slippage
STF / SafeTransferFrom -> input transfer, allowance, balance, or router issue
IDS / invalid signature -> Permit2/router authorization issue
```

Always retain the raw safe-truncated revert in logs/journal for diagnosis; user-facing text should report the correct action category.
