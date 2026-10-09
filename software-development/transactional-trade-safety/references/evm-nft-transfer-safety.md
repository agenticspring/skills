# EVM NFT Transfer Safety Reference

## Preparation evidence

Bind one immutable plan to:

```text
chain + chainId
wallet/source
allowlisted checksum destination
contract + code hash
token standard + tokenId + quantity
pre-state ownership/balances
exact calldata + zero/native value
gas limit + fee evidence + native reserve
observed block
```

Required reads before simulation:

- `eth_chainId` and `eth_getCode`;
- ERC-165 `supportsInterface` when the workflow depends on ERC-721 vs ERC-1155 semantics;
- ERC-721 `ownerOf(tokenId)` or ERC-1155 source `balanceOf(owner,id)`;
- for ERC-1155, destination pre-balance for later delta proof;
- exact `eth_call`, `eth_estimateGas`, fee evidence, native balance, and current block.

Fail before nonce/signing when destination, chain, code, standard, owner, quantity, simulation, gas ceiling, or reserve is invalid.

## Signed envelope and journal order

Validate the signed transaction against the immutable plan:

```text
from
to
chainId
value
calldata
gas limit
fee fields
nonce
locally derived TxHash
```

Then enforce:

```text
sign
→ derive TxHash locally
→ persist TxHash + plan hash + nonce + raw-tx checksum
→ broadcast once
```

Do not store raw signed transaction bytes. A journal conflict where one intent is already bound to another hash fails closed.

## Unknown outcomes

Any timeout/error after a send may have reached the network. Mark the intent unknown and block its wallet+chain lane. Do not retry signing or broadcast. Restart workers with a persisted TxHash must perform reconciliation only; tests should assert signer and broadcaster calls remain zero.

## Confirmation proof

A transfer is confirmed only with:

1. transaction hash/from/to/input match;
2. successful final receipt and no removed logs;
3. exactly matching NFT event:
   - ERC-721 `Transfer(from,to,tokenId)`;
   - ERC-1155 `TransferSingle(operator,from,to,id,value)` for exact safe-transfer plans;
4. post-state:
   - ERC-721 `ownerOf(tokenId) == destination`;
   - ERC-1155 source decreased and destination increased by the planned quantity relative to retained baselines.

Receipt success without exact log and post-state is `UNKNOWN_NEEDS_RECONCILIATION`.

## Minimum behavioral tests

- destination outside allowlist;
- wrong chain/code/standard/owner;
- ERC-721 quantity not one;
- ERC-1155 insufficient source balance and partial quantity success;
- simulation revert, gas ceiling, and reserve failure before nonce change;
- TxHash persisted before broadcaster invocation;
- timeout after send produces unknown and no retry;
- restart with persisted TxHash never signs/broadcasts;
- reverted receipt;
- successful receipt with wrong/missing/removed log;
- destination post-state mismatch;
- real read-only burner smoke verifying nonce/balance unchanged and zero `eth_sendRawTransaction` calls.
