---
name: cast-broadcast-safety
description: Broadcast EVM txs safely with cast wrappers.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Cast, Broadcast, EVM, Gas, Robinhood, Wrapper]
    related_skills: [wallet-fund-sweep, evm-wallet-set-management, fifo-drip-sniper]
---

# Cast Broadcast Safety

Patterns for writing `cast send` wrapper scripts that broadcast EVM
transactions (funding, sweeping, NFT transfers) reliably on low-fee chains
such as Robinhood (4663). Learned from the BABIES cascade where every sweep
failed in-script while the identical manual `cast send` succeeded — the
failures were wrapper bugs, not chain or fund problems.

## When to Use

- Writing a Python wrapper around `cast send` for funding/sweeping/transfers
- A scripted broadcast fails `insufficient funds` but the same manual command works
- After a sniper/mint run, sweeping leftover balance to another wallet

## Pitfalls (verified on-chain 2026-08-21)

1. **ONE wei convention end-to-end.** A helper formatting
   `--value` as `format(int(value*1e18), '#x')` expects an ETH float argument.
   Passing `int(amount*1e18)` into it multiplies AGAIN → sends
   `amount*1e36` wei → every broadcast reverts `insufficient funds for
   transfer` while manual `cast send` with identical params succeeds.
   Fix: name the parameter `value_wei`, pass wei directly, format as-is.
2. **Fresh nonce per retry attempt.** Rebuilding the cmd once and reusing it
   in the retry loop sends the same stale nonce. Build the nonce flag inside
   the loop (`cmd = base + ['--nonce', str(nonce(addr))]`).
3. **Pending-tx gap after mint runs.** `eth_getBalance` reads latest, but the
   gas estimate reserves for pending pool txs, so the first sweep after a
   sniper win reverts `insufficient funds` even with a healthy balance.
   Retry with backoff 4s + attempt*3 until pending clears; verify
   `eth_getTransactionCount(addr, 'pending') == 'latest'` and zero pending
   txs before concluding funds are actually gone.
4. **Explicit `--gas-price` is required on thin balances.** cast's default
   max-fee estimate reverts `gas required exceeds allowance (N)` / 
   `insufficient funds for transfer` on balances under ~0.00001 ETH. Pass
   `--gas-price 0x1406f40` (~0.021 gwei) where base is ~0.02 gwei.
5. **Keep = real fee only, never a fat buffer.** For "send everything until
   it can't tx": keep = `21000 * gas_price * 1.15` (min 0.0000012-0.000003),
   send balance minus keep. Residual below fee is the intended endpoint.
6. **`--json <to>` must stay in the base cmd.** Dropping the recipient when
   refactoring the base list yields `Must specify a recipient address`.
7. **`maxPriorityFeePerGas` MUST be <= `maxFeePerGas`.** Verified 2026-09-27
   broadcasting an OP Stack bridge deposit: setting `prio = 1 gwei` while
   `maxFee = baseFee*2` (~0.12 gwei at baseFee 0.06) made the node reject the
   tx 4x with `max priority fee per gas higher than max fee per gas`.
   Fix: `prio = 0.01 gwei`, `maxFee = baseFee*2 + prio`. Nothing was spent —
   nonce stayed 0 — but the retry loop burned 4 attempts. Compute the fee pair
   from ONE expression so they can never invert.
8. **Node-side `eth_estimateGas` fails while a wallet is unfunded**
   (`EVM error: OutOfFunds`). Don't read that as "calldata is wrong". To dry-run
   before funding, use `eth_call` with **state overrides**:
   `params=[{from,to,data,value},"latest",{addr:{balance:"0x…"}}]`.
   Alchemy accepts the override on `eth_call` but still fails `eth_estimateGas`
   with the same params — so preflight with `eth_call`, not `estimateGas`.
9. **Alchemy free tier caps `eth_getLogs` at a 10-block range.** For wide log
   scans use Blockscout's Etherscan-compatible endpoint
   (`https://eth.blockscout.com/api?module=logs&action=getLogs&address=…&topic0=…`)
   or scan blocks individually. Also: Blockscout's log/tx **index lags on new
   contracts** — never conclude "no event" from an indexer alone when a receipt
   can be fetched directly.

## OP Stack L1 -> L2 bridge deposits (verified 2026-09-27, GIWA chain 9134)

Two entry points, same trust domain, same `TransactionDeposited` event:

| | `L1StandardBridge.bridgeETHTo(address,uint32,bytes)` = **`0xe11013dd`** | `OptimismPortal2.depositTransaction(address,uint256,uint64,bool,bytes)` = **`0xe9e05c42`** |
|---|---|---|
| gas (measured) | **620,976** — identical on repeat runs | ~150k-250k |
| L2 delivery | automatic via messenger | manual / you own the `_data` call |
| L2 deposit tx `to` | `0x4200…0007` (L2CrossDomainMessenger), NOT your address | your address |

- Fund for **700,000 gas**, not 200k. Gas is deterministic (620,976 twice).
- Deposit `_minGasLimit` of 200,000 is fine for a plain ETH transfer.
- **Finding the L2 side:** the deposit tx `to` is the L2CrossDomainMessenger, so
  searching L2 txs by `to == yourAddress` finds nothing. Instead scan for
  **anomaly blocks** (`eth_getBlockTransactionCountByNumber > 1`, since a quiet
  OP Stack block has exactly 1 system tx) and match on `value` + `type == 0x7e`.
- **Address aliasing trap:** a contract L1 sender appears in
  `TransactionDeposited` topic1 as `sender + 0x1111000000000000000000000000000000001111`.
  A user wallet balance list built from those topics will silently include the
  aliased `L1CrossDomainMessenger` (`0xe4c52377…` -> alias `0xf5d62377…`).
  Subtract the alias constant to recover the real sender; if the original L1 tx
  `from` is an EOA calling the portal directly, topic1 is NOT aliased.
- Same rule for the L2 escrow check: `L1StandardBridge` balance stays **0** —
  all bridged ETH sits in the `OptimismPortal2`. Reconcile a deposit by diffing
  the **portal** balance, not the bridge's.

## More broadcast pitfalls (continuation of the numbered list above)

7. **Never trust a remembered function selector.** Hand-built calldata recalled from memory
   (`bridgeETHTo(address,uint32,bytes)` "= `0x540abf73`"; the real selector is `0xe11013dd`)
   either reverts or, worse, hits a different same-shape function. Verify before broadcast:
   `cast sig "<fn>(<types>)"` to compute the selector, `cast 4byte <selector>` to confirm what
   it actually is, and `cast 4byte-decode <full-calldata>` to prove your encoding round-trips
   back to the arguments you intended.
8. **`eth_estimateGas` answering `OutOfFunds` on an unfunded wallet is not a broken call.**
   Gas estimation checks balance, so a dry-run against a zero-balance address always fails —
   which reads like "this transaction is invalid" when nothing is wrong. Validate with
   `eth_call` + `stateOverrides` (`{<acct>: {"balance": "0x..."}}`) instead. Alchemy's
   `eth_estimateGas` rejects/ignores `stateOverrides` (`unknown field` / `Invalid params`), so
   simulate with `eth_call` and size gas from a MEASURED envelope, not a guessed one.
   **Measured on Ethereum mainnet 2026-09-27: an OP Stack L1 bridge deposit
   (`L1StandardBridge.bridgeETHTo`) consumed 620,976 gas** — ~3× a 21 000 transfer and far
   above the ~150-200k this note previously guessed. Budget a ~700 k ceiling for a bridge
   deposit; under-reserving reverts `insufficient funds` on a balance that looked healthy.
9. **Refuse to broadcast below `value + gas`.** A wrapper that sends anyway half-executes and
   burns gas on a revert. Compute `need = value + gas_cap * maxFeePerGas`, abort with the
   shortfall, and set `maxFeePerGas = base_fee * 2`. Keep the wallet's *entire* balance equal to
   the maximum acceptable loss: fund a fresh throwaway address per test (key to a `chmod 600`
   file, print only the address) instead of reusing one that holds anything else.
10. **`maxPriorityFeePerGas` must be `<=` `maxFeePerGas` — verify this before the retry loop.**
    Verified on Ethereum mainnet 2026-09-27: `tip = 1 gwei` combined with `maxFee = baseFee * 2`
    (≈0.12 gwei at a quiet base fee) is rejected on EVERY attempt with
    `-32003  max priority fee per gas higher than max fee per gas`. Nothing is spent — the nonce
    never moves — so a generic retry loop just burns four attempts and buries the real cause
    under "broadcast failed". Two consequences:
    - Prescribe the pair, don't set them independently: `tip = 0.01 gwei`,
      `maxFee = base_fee * 2 + tip` (the ceiling must **include** the tip). The
      `maxFeePerGas = base_fee * 2` formula in the pitfall above is only safe when the tip is
      known to fit underneath it.
    - Classify that error string as **fatal, not transient** — grep for it and abort loudly
      instead of retrying, and keep it out of the `insufficient funds` / `nonce too low` transient
      bucket in the retry list below. Same rule for `cast send`: an explicit
      `--priority-gas-price` must sit below `--gas-price`.
11. **Never set `gas = eth_estimateGas * 2`.** The estimate is already conservative, and doubling
    it inflates the amount the node reserves at submit time
    (`gasLimit * maxFeePerGas + value`). The tx is then rejected with
    `insufficient funds for gas * price + value: have X want Y` **even though the wallet plainly
    holds enough** — and because the message says "insufficient funds", you go hunting the balance
    instead of the gas limit. Verified 2026-09-27: an OP Stack bridge deposit estimated ~660 k gas,
    the `*2` set the limit to 1.32 M, and a working 0.0037 ETH bridge failed 4× identically.
    Fix: use a **fixed ceiling from measurement**, never a multiplier — that deposit always
    consumed 620,976 gas, so a flat 700,000 is both safe and honest.
    The `want` figure tells you what was actually reserved:
    `want - value == gasLimit * maxFeePerGas` — back it out to confirm the diagnosis before
    touching the balance check.

## Procedure

1. Define `broadcast(pk, addr, to, data='0x', value_wei=0, gas_p=None, retries=4)`
   with base list `['cast','send','--rpc-url',RPC,'--private-key',pk,'--json',to]`.
2. Append `--data` only when non-zero, `--value` (wei, as-is) only when non-zero,
   always `--gas-price`.
3. In the retry loop, build the full cmd with a FRESH nonce each attempt.
4. On transient errors (`insufficient funds`, `nonce too low`, `replacement`,
   `already known`, `gas required exceeds`), log, sleep `4 + attempt*3`, retry.
5. After broadcast, poll `eth_getTransactionReceipt` until status 1.
6. For sweeps: compute keep from live base fee, send `balance - keep`.

## Session Reference

- `references/babies-cascade-2026-08.md` — full transcript of the BABIES
  cascade that surfaced these bugs: the 6-bug fix table, dev-controlled drip
  interval swings (3s→600s→2s), verified fee numbers, and win-verification
  rules. Load when running a multi-wallet free-mint cascade or debugging a
  sweep that keeps reverting.
- For a worked end-to-end broadcast outside the cast-wrapper mould — a real
  OP Stack L1→L2 bridge deposit (raw `eth_account` signing, fee pair, 620,976-gas
  receipt, L2 verification, fund-gated watcher) — see
  `web3-rpc-contract-audit`'s `references/l1-to-l2-bridge-deposit-execution.md`.

## Verification

```bash
# A sweep that previously failed in-script should succeed with identical params
cast send --rpc-url <RPC> --private-key <pk> --json <to> \
  --value <value_wei_hex> --gas-price 0x1406f40 --nonce <fresh>
```
