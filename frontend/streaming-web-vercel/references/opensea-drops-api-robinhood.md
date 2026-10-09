# OpenSea Drops API — Programmatic Drop Creation on Robinhood Chain

Validated 2026-08-24. Full working flow: deploy ERC721-SeaDrop → configure stages → upload items → mint.

## Architecture

- RH chain ID: **4663** (`0x1237`)
- Public RPC: `https://rpc.mainnet.chain.robinhood.com`
- Alchemy: `https://robinhood-mainnet.g.alchemy.com/v2/$ALCHEMY_API_KEY`
- Canonical SeaDrop v1: `0x00005EA00Ac477B1030CE78506496e8C2dE24bf5` (21081 bytes code)
- OpenSea auto-indexes any deployed ERC721 on supported chains (slug = lowercase name)

## Auth (two layers required)

1. **API Key** — for read endpoints + mint building
2. **OAuth Bearer token** — for write endpoints (`write:drops`, `write:collections` scopes)

```bash
npm install -g @opensea/cli
export OPENSEA_PRIVATE_KEY=<deployer_pk>
opensea login --private-key --scopes 'read:eligibility,write:drops,write:collections'
# Token stored in ~/.opensea/auth.json → tokens.<address>.accessToken
```

Bearer token expires ~1h. Re-login before long batch operations.

## Deploy Contract

```bash
POST https://api.opensea.io/api/v2/drops/deploy
{
  "chain": "robinhood",
  "contract_name": "...",
  "contract_symbol": "...",
  "drop_type": "seadrop_v1_erc721",
  "sender": "0x...",
  "token_type": "erc721_standard"
}
```

Returns `{to, data, value}` — sign+broadcast via cast. Supported drop_types: `standard_external_erc721`, `standard_external_erc1155`, `seadrop_v1_erc721`, `seadrop_v2_erc721` (not yet on RH).

### CRITICAL PITFALL: Builder deploys with maxSupply=0

The `/drops/deploy` builder does NOT include a `maxSupply` parameter. The resulting contract has `maxSupply()=0` which makes ALL mints revert with `MintQuantityExceedsMaxSupply`.

**Fix:** After deployment, call `setMaxSupply(uint256)` on the new contract (owner-only).

### CRITICAL PITFALL: Constructor seadrop arg may be empty on RH

The builder's constructor args include a SeaDrop address that may have NO CODE on RH chain (`0x0ac4...cd0b` was observed). This means:
- `updateCreatorPayoutAddress` reverts (forwards to empty seadrop)
- `mintPublicSale` fails with `CreatorPayoutAddressCannotBeZeroAddress`

**Fix:** Call `updateAllowedSeaDrop(address[])` to ADD the canonical SeaDrop `0x00005EA00Ac477B1030CE78506496e8C2dE24bf5`, then use it for all stage config.

## Post-Deployment Setup (owner calls on NFT contract)

```
1. setMaxSupply(uint256)                    // REQUIRED — default is 0
2. updateAllowedSeaDrop(address[])          // if constructor arg was wrong
3. updateCreatorPayoutAddress(address)      // forwards to FIRST allowed seadrop only!
4. updatePublicDrop(address,(uint80,uint48,uint48,uint16,uint16,bool))
   // (price_wei, startTime, endTime, maxPerWallet, maxTokenSupplyForStage, feeBps)
5. updateAllowedFeeRecipient(address,address,bool)  // optional
```

**PITFALL:** `updateCreatorPayoutAddress(address)` on the NFT forwards to the FIRST seadrop in its immutable array. If that seadrop is empty, use the two-arg version on the canonical SeaDrop directly: `updateCreatorPayoutAddress(address nft, address payout)` called by the NFT owner.

## Verify On-Chain State

```bash
# Read public drop from SeaDrop
cast call 0x00005EA00Ac477B1030CE78506496e8C2dE24bf5 \
  'getPublicDrop(address)(uint80,uint48,uint48,uint16,uint16,bool)' $NFT_ADDR --rpc-url $RPC

# Check supply
cast call $NFT 'maxSupply()(uint256)' --rpc-url $RPC
cast call $NFT 'totalSupply()(uint256)' --rpc-url $RPC
cast call $NFT 'owner()(address)' --rpc-url $RPC
```

## Upload Item Media (100 items in <60s)

Three-step flow:
1. `POST /api/v2/drops/{slug}/items/media` with `{"filenames": ["1.jpg", ...]}` — max 50 per request
2. Upload each file to presigned S3 URL (Python requests handles multipart correctly; curl subprocess with long field values returns status=000)
3. `POST /api/v2/drops/{slug}/items/media/save` with `{"media_tokens": [...]}`

Each context includes a `token` field — this IS the media_token needed later.

## Save Items (metadata)

Use `POST /api/v2/drops/{slug}/prereveal-item` for prereveal items:
```json
{"name": "...", "description": "...", "media_token": "studio/drop/..."}
```
Does NOT accept `traits` (unknown field). Does NOT accept `supply`. Requires auth bearer.

The SelfMint endpoint (`save-item`) returns tx data but gives 500 on SeaDrop v1 drops.

## Save Drop Stages

```bash
POST /api/v2/drops/{slug}
Authorization: Bearer <oauth_token>
{
  "creator_payout_address": "0x...",
  "max_supply": "100",
  "stages": [
    {
      "uuid": "unique-uuid",
      "label": "PUBLIC",
      "stage_type": "public_sale",
      "price": {"contract_address": "0x0000000000000000000000000000000000000000", "unit": "0"},
      "start_time": "2026-08-24T11:17:38Z",
      "end_time": "2026-09-30T11:17:38Z",
      "max_total_mintable_by_wallet": "2"
    }
  ]
}
```

Stage ordering rules:
- Public sale must be FIRST in array
- Presale must end EXACTLY when public starts
- `signed_presale` stage accepts `allowlist_file_token`

## Allowlist Upload

```bash
# 1. Request presigned upload
POST /api/v2/drops/{slug}/allowlist/upload
# 2. Upload file to S3 (multipart POST, file part LAST)
# 3. Validate
POST /api/v2/drops/{slug}/allowlist/validate
{"allowlist_file_token": "primary-drops/<contract>/<uuid>"}
```

Allowlist file format: plain text, one address per line.
Validation error uses `allowlist_file_token` (not `file_token`).

## Mint

Once public drop is live on-chain, mint directly via SeaDrop:
```bash
cast send 0x00005EA00Ac477B1030CE78506496e8C2dE24bf5 \
  'mintPublic(address,address,address,uint256)' \
  $NFT $MINTER $PAYER 1 \
  --value <price_wei> --private-key $PK --rpc-url $RPC
```

Or build via API: `POST /api/v2/drops/{slug}/mint` with `{"minter": "0x...", "quantity": 1}`

## Pitfalls Summary

| Issue | Cause | Fix |
|---|---|---|
| MintQuantityExceedsMaxSupply | Builder deploys maxSupply=0 | Call setMaxSupply(100) after deploy |
| CreatorPayoutAddressCannotBeZeroAddress | Seadrop immutable empty on RH | Add canonical seadrop via updateAllowedSeaDrop, then set payout |
| OnlyAllowedSeaDrop() revert | Seadrop not in allowed list | Call updateAllowedSeaDrop([canonical_addr]) |
| Bearer 401 mid-batch | Token expires ~1h | Re-login before batches >30min |
| Media upload status=000 via curl subprocess | Long S3 field values break shell quoting | Use Python requests library |
| Drop GET 404 after save_edits success | Drop not published (needs items + publish step) | Upload items first, drop appears when published |

## OpenSea CLI Commands

```bash
opensea drops get <slug>
opensea drops list --chain robinhood
opensea drops save-edits <slug> --body <json>
opensea drops create-item-media-upload <slug> --body <json>
opensea drops save-item-media <slug> --body <json>
opensea drops create-allowlist-upload <slug>
opensea drops validate-allowlist <slug> --body <json>
opensea drops eligibility <slug>
opensea drops mint <slug> --minter 0x...
opensea whoami
```
