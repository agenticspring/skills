# NFT marketplace fulfillment reference

Use this reference for the OpenSea/Seaport buy, sweep, and accept-offer boundary.

## Normalized order identity

Before preparation, compare the current order to the persisted snapshot:

```text
order_hash
chain
protocol_address
seller / fulfiller
NFT contract
 token ID or identifierOrCriteria
quantity
payment currency
consideration: gross, marketplace fee, royalty
expiry
```

A mismatch is stale data and must fail closed. Do not rebuild a new order silently.

## OpenSea acquisition routes

```text
POST /api/v2/listings/fulfillment_data
body: { fulfiller: { address }, listing: { chain, hash, protocol_address } }

POST /api/v2/offers/fulfillment_data
body: { fulfiller: { address }, offer: { chain, hash, protocol_address } }
```

Treat these as transaction-data acquisition only. Validate the response shape before passing it to the canonical simulator:

```text
fulfillment_data.transaction.to
fulfillment_data.transaction.data
fulfillment_data.transaction.value
```

Do not expose `data`, signatures, JWTs, or raw signed bytes in Telegram or ordinary logs.

## Criteria offers

`identifierOrCriteria == 0` is not proof that any token qualifies. Require a supported criteria-validation callback/endpoint for the exact order hash, NFT contract, and selected token ID. Missing validator or a false result is `criteria_validation_unavailable` / `criteria_mismatch`.

## Cost and confirmation

Buy total:

```text
gross price + gas reserve
```

Offer net preview:

```text
gross offer - marketplace fee - royalty - gas
```

Confirmation requires all of:

```text
receipt.status == success
receipt.transactionHash == persisted TxHash
exact Transfer from seller to expected recipient
post-state owner == expected recipient
payment delta == expected delta
```

A successful API response, a returned fulfillment payload, an indexer update, or a TxHash alone is not confirmation.

## Sweep policy

Default: all-or-nothing. If the caller explicitly enables partial execution:

- persist each item as `selected` or `rejected`;
- include a reason (`stale_or_invalid`, `expired`, `budget`);
- enforce the aggregate budget while selecting;
- stop on invalid or uncertain post-broadcast state;
- never auto-retry an uncertain item.

## Minimum tests

- stale/expired/wrong contract/token/currency/criteria/consideration rejected;
- exact listing/offer fulfillment request binding;
- malformed fulfillment transaction rejected before simulation;
- criteria validator missing/false/true paths;
- total cost and net proceeds use atomic integer arithmetic;
- partial sweep disabled by default;
- explicit partial sweep records item-level statuses;
- receipt/hash/transfer/ownership/payment delta all required;
- sanitized preview excludes calldata and signatures;
- signing and broadcast remain false in preparation tests.
