# SeaDrop v1 on Robinhood Chain — Deployed Reference

## Key Addresses

- Canonical SeaDrop v1: `0x00005EA00Ac477B1030CE78506496e8C2dE24bf5` (21081 bytes code)
- RH Chain ID: 4663 (0x1237)
- Public RPC: `https://rpc.mainnet.chain.robinhood.com`
- OpenSea auto-indexed collection: slug auto-generated from contract address (e.g. `spring-test-317800923`)

## Deploy Flow That Works

1. Build deploy tx via `POST /api/v2/drops/deploy` — but the builder's seadrop immutable
   points to `0x0ac477b1...cd0b` which is EMPTY on RH. MUST redeploy with forge.
2. Clone seadrop repo, build with forge, deploy ERC721SeaDrop with canonical SeaDrop as constructor arg.
3. Post-deploy setup (in order):
   - `setMaxSupply(100)` — defaults to 0!
   - `updateAllowedSeaDrop([canonical])`
   - `updateCreatorPayoutAddress(canonical_seadrop, payout_wallet)` — two-arg version on NFT
   - `updateAllowedFeeRecipient(canonical_seadrop, canonical_seadrop, true)` — required for signed mints
   - `updatePublicDrop(canonical_seadrop, (price,start,end,maxWallet,maxSupply,false))`

## Allowlist via Signed Vouchers (v1.0 has no merkle stage)

- Merkle `mintAllowList` always reverts `NotActive` because v1.0 NFT lacks `updateAllowListStage`.
- Workaround: register creator via `updateSignedMintValidationParams(seadropAddr, signerAddr, params)`,
  sign EIP712 voucher, wallet calls `mintSigned()`.
- Voucher params must EXACTLY match stored validation window or reverts `InvalidSignedStartTime`.
- `restrictFeeRecipients` must be `true` or reverts `SignedMintsMustRestrictFeeRecipients`.

## EIP712 Domain for Signing Vouchers

```
domain: { name: "SeaDrop", version: "1.0", chainId: 4663, verifyingContract: SEADROP }
types:
  MintParams(mintPrice, maxTotalMintableByWallet, startTime, endTime,
             dropStageIndex, maxTokenSupplyForStage, feeBps, restrictFeeRecipients)
  SignedMint(nftContract, minter, feeRecipient, mintParams, salt)
```

## Gas on RH Chain

Base fee ~0.02 gwei (very cheap). Mint gas ~104k-124k. Deploy ~4.5M gas (~$0.30).

## OpenSea Drops API Endpoints (RH Chain)

- `POST /api/v2/drops/deploy` — returns ready-to-sign creation code for SeaDrop NFT
- `GET /api/v2/drops/{slug}` — fetch drop info + stages (returns 404 if drop not published via studio)
- `POST /api/v2/drops/{slug}` — save drop edits (stages, payout, timing) — requires OAuth bearer with `write:drops` scope
- `POST /api/v2/drops/{slug}/allowlist/upload` — presigned S3 upload for allowlist file
- `POST /api/v2/drops/{slug}/items/media` — presigned S3 uploads for item media (max 50 per call)
- `POST /api/v2/drops/{slug}/prereveal-item` — save prereveal metadata `{name, description, media_token}`
- `opensea login --private-key --scopes 'read:eligibility,write:drops,write:collections'` — CLI auth
- Bearer tokens expire ~1 hour; store in `/root/.opensea/auth.json`

## Drop Publishing Flow

1. Deploy contract → auto-indexed by OpenSea with slug from address
2. Upload media via presigned S3 POST (Python requests, NOT curl subprocess)
3. Persist media tokens via `save-item-media`
4. Save prereveal items via `prereveal-item` endpoint
5. Configure on-chain stages (public drop, signed validation params, fee recipients)
6. Drop becomes visible after ALL steps complete; verify via `getPublicDrop()` on-chain

## Common Revert Selectors

| Selector | Error | Cause |
|----------|-------|-------|
| `0x13da22f2` | NotActive(uint256,uint256,uint256) | Merkle allowlist stage not configured |
| `0x3f009769` | CreatorPayoutAddressCannotBeZeroAddress | Call updateCreatorPayoutAddress first |
| `0x0d35e921` | IncorrectPayment(uint256,uint256) | msg.value != price × quantity |
| `0x15e26ff3` | OnlyAllowedSeaDrop() | Seadrop not in allowed list |
| `0xd855c4f4` | InvalidSignature(address) | Signer not registered or wrong EIP712 domain |
| `0x333d33d0` | InvalidSignedStartTime(uint256,uint256) | Voucher start ≠ stored validation start |
| `0xdb8b2fad` | SignedMintsMustRestrictFeeRecipients() | Set restrictFeeRecipients=true |
| `0xf477d26f` | FeeRecipientNotAllowed() | Allow seadrop as fee recipient |

Decode unknown selectors: `curl -s 'https://api.openchain.xyz/signature-database/v1/lookup?function=0x<sel>'`
