---
name: relay-weth-wrap
description: Wrap or unwrap WETH safely through Relay quotes.
version: 0.1.0
author: Hermes
license: MIT
metadata:
  hermes:
    tags: [Relay, WETH, Robinhood, Wrap, EVM]
---

# Relay WETH Wrap and Unwrap

Wrap native ETH into WETH or unwrap WETH back to native ETH using a Relay quote, then independently preflight the exact transaction before any broadcast. This skill covers Robinhood Chain (4663) evidence gathered live; it does not approve ERC-20s, bridge assets, or broadcast until the user explicitly requests it.

## When to Use

- User asks to "swap ETH to WETH" or "swap WETH back to ETH" through Relay.
- Need to validate Relay's quoted WETH contract before sending native ETH.
- Need a small-value wrap/unwrap test with receipt and balance proof.

## Prerequisites

- Native ETH for amount plus gas.
- `ALCHEMY_API_KEY` in `~/.hermes/.env` for Robinhood Chain RPC.
- `cast` available through the `terminal` tool for final broadcast.
- Explicit wallet address, chain, amount, and user confirmation before broadcast.

## How to Run

Use `terminal` to invoke `scripts/relay-wrap-preflight.py`. It queries Relay's live quote API, checks the requested Relay currency record, and runs exact `eth_call` plus `eth_estimateGas`. It is read-only: `signed=false`, `broadcast=false`.

```bash
python3 scripts/relay-wrap-preflight.py \
  --mode wrap --chain-id 4663 --user <wallet> --amount-wei <wei>
```

For an unwrap, omit the amount to use the wallet's full WETH balance:

```bash
python3 scripts/relay-wrap-preflight.py \
  --mode unwrap --chain-id 4663 --user <wallet>
```

## Quick Reference

```text
Relay quote API:      POST https://api.relay.link/quote/v2
Relay currency API:   POST https://api.relay.link/currencies/v2
Robinhood chain ID:   4663
Native ETH address:   0x0000000000000000000000000000000000000000
Robinhood WETH:       0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73
deposit() selector:   0xd0e30db0
withdraw(uint256):    0x2e1a7d4d
```

## Procedure

1. **Identify operation.** `wrap` must use ETH as input and WETH as output; `unwrap` reverses that. User and recipient must be the same wallet for Relay's ETH/WETH wrap route.
2. **Query Relay.** Send `user`, `recipient`, `originChainId`, `destinationChainId`, `originCurrency`, `destinationCurrency`, `amount`, and `tradeType: EXACT_INPUT` to `/quote/v2`.
3. **Validate quote identity.** Require `details.operation` to equal `wrap` or `unwrap`, `chainId == 4663`, `to == Robinhood WETH`, and `from == user`.
4. **Validate calldata.** Wrap must be `deposit()` (`0xd0e30db0`) with ETH value. Unwrap must begin `withdraw(uint256)` (`0x2e1a7d4d`) with zero value and the requested WETH amount encoded.
5. **Validate currency metadata.** Query `/currencies/v2` with `{chainIds:[4663], address:<WETH>}`. Relay currently returns `symbol: WETH`, `decimals: 18`, but metadata `verified: false`; do not present the badge as a security proof.
6. **Independently verify contract.** Resolve its EIP-1967 implementation via RPC, then inspect verified source/ABI on Blockscout. The observed implementation is `aeWETH`: `deposit()` mints to `msg.sender`; `withdraw(amount)` burns caller WETH and transfers native ETH to the caller.
7. **Simulate exact payload.** Call `eth_call` and `eth_estimateGas` with exact `from`, `to`, `data`, and `value`. Stop on any revert or response failure.
8. **Broadcast only after confirmation.** Use `terminal` with explicit `--nonce` and `--gas-price`; never use a different payload from the preflighted quote.
9. **Verify.** Require receipt `status=1`, re-read WETH `balanceOf(user)` and native ETH balance, and report the real TxHash.

## Pitfalls

- `metadata.verified: false` in Relay's catalog is not a contract audit. Require independent proxy/source and exact-call evidence.
- The WETH contract is a transparent proxy; prove the active implementation before every first-use or contract-change event.
- Same-chain ETH→ETH quotes are classified as `send`; use identical user/recipient for native wrap/unwrap, as Relay requires.
- Relay site can return 429/WAF. Use the documented API endpoints, not page scraping.
- RPC can transiently return 403 or malformed response. Retry read-only calls; never broadcast until exact call and gas estimate succeed.
- A quote with an approval, a recipient other than the user, a nonzero unwrap value, or unexpected calldata is fail-closed.
- WETH is not a bridge transfer. Use a real bridge route only when origin and destination chain IDs differ.

## Verification

```text
Receipt status == 1
AND wrap: WETH balance increases by quoted amount
OR unwrap: WETH balance is reduced by requested amount and native ETH increases minus gas
```
