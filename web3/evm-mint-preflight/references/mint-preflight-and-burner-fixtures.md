# Mint preflight and burner fixtures

Use this reference for EVM primary-mint/allowlist preparation before any signing or broadcast.

## Fixture rules

- Create an ephemeral EVM burner with `Wallet.createRandom()` in the test process.
- Assert its native balance is zero through RPC before preflight.
- Do not print or persist its private key. Do not import it into the production signer vault.
- Do not fund it, sign with it, or broadcast from it.
- A zero-balance result should fail at the balance-reserve gate after the read-only `eth_call`/gas path.

## Gate order

1. Collection slug/chain/contract identity.
2. `eth_chainId` equality.
3. `eth_getCode` non-empty and optional code hash.
4. Actual Merkle leaf/proof or EIP-712 voucher validation.
5. Exact `eth_call` with exact `from`, `to`, calldata, and value.
6. `eth_estimateGas` and configured max-gas check.
7. `value + gasLimit * gasPrice` against spendable balance/reserve.
8. Deterministic plan hash with `signed=false` and `broadcast=false`.

## RPC quirk

For Geth-compatible endpoints, encode zero transaction value as `0x0`, not `0x00`; the latter can produce `cannot unmarshal hex number with leading zero digits`.

## Reporting

`verified` means chain/address/bytecode evidence passed. `simulated` means exact call and gas estimate passed, not that a transaction exists. `failed_preflight` is the correct result for an unfunded burner. Never report `minted`, `broadcast`, or `successful` without an actual receipt and post-state evidence.
