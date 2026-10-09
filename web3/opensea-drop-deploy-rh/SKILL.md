---
name: opensea-drop-deploy-rh
description: Deploy and mint SeaDrop NFT drops on Robinhood Chain.
version: 0.1.0
author: Hermes
platforms: [linux]
metadata:
  hermes:
    tags: [NFT, OpenSea, SeaDrop, Robinhood, Deploy, Mint]
---

# OpenSea Drop Deployment on Robinhood Chain

Deploys ERC721-SeaDrop NFT contracts on Robinhood Chain (chain ID 4663), configures
free-mint drop stages (allowlist + public), and tests minting. Uses the OpenSea
`/drops/deploy` API for tx data or `forge create` for custom deployments. Requires
`cast`/`forge` (Foundry), an OpenSea API key, and a funded wallet on RH chain.

## When to Use

- "Deploy an NFT drop on Robinhood Chain"
- "Create a free mint collection on OpenSea for RH"
- "Set up allowlist + public mint stages on RH chain"
- "Test batch mint from multiple wallets on Robinhood"

## Prerequisites

- Foundry: `cast`, `forge` (`curl -L https://foundry.paradigm.xyz | bash`)
- OpenSea API key with developer account approved
- Funded wallet on RH chain (gas ~0.0002 ETH per deploy)
- Alchemy RPC: `https://robinhood-mainnet.g.alchemy.com/v2/$ALCHEMY_API_KEY`
- Public RPC: `https://rpc.mainnet.chain.robinhood.com`
- Canonical SeaDrop v1: `0x00005EA00Ac477B1030CE78506496e8C2dE24bf5`

## Quick Reference

```text
RH Chain ID:        4663 (0x1237)
SeaDrop v1:         0x00005EA00Ac477B1030CE78506496e8C2dE24bf5
Deploy builder:     POST https://api.opensea.io/api/v2/drops/deploy
Drop stages save:   POST https://api.opensea.io/api/v2/drops/{slug}
Allowlist upload:   POST https://api.opensea.io/api/v2/drops/{slug}/allowlist/upload
Media upload:       POST https://api.opensea.io/api/v2/drops/{slug}/items/media
Save item:          POST https://api.opensea.io/api/v2/drops/{slug}/items
Mint builder:       POST https://api.opensea.io/api/v2/drops/{slug}/mint
OAuth login:        opensea login --private-key --scopes 'read:eligibility,write:drops'
```

## Procedure

1. **Build deploy tx via OpenSea API** (returns ready-to-sign creation code).

```bash
curl -s -X POST 'https://api.opensea.io/api/v2/drops/deploy' \
  -H "x-api-key: $OPENSEA_API_KEY" \
  -H 'content-type: application/json' \
  --data '{"chain":"robinhood","contract_name":"MyCollection","contract_symbol":"SYMB","drop_type":"seadrop_v1_erc721","sender":"<WALLET>","token_type":"erc721_standard"}'
```

2. **Sign and broadcast** (`to=0x0...0` means contract creation).

```bash
DATA=$(python3 -c "import json; print(json.load(open('deploy_tx.json'))['data'])")
cast send --private-key $PK --rpc-url $RPC --json --create "$DATA"
```

3. **Set max supply** — defaults to 0; mints revert without this.

```bash
cast send <CONTRACT> 'setMaxSupply(uint256)' 100 --private-key $PK --rpc-url $RPC
```

4. **Add canonical SeaDrop to allowed list.**

```bash
cast send <CONTRACT> 'updateAllowedSeaDrop(address[])' '[0x00005EA00Ac477B1030CE78506496e8C2dE24bf5]' --private-key $PK --rpc-url $RPC
```

5. **Set creator payout** — two-arg version on NFT contract.

```bash
cast send <CONTRACT> 'updateCreatorPayoutAddress(address,address)' \
  0x00005EA00Ac477B1030CE78506496e8C2dE24bf5 <PAYOUT_WALLET> \
  --private-key $PK --rpc-url $RPC
```

6. **Configure public drop stage on-chain.**

```bash
NOW=$(date +%s); END=$((NOW + 37*86400))
cast send <CONTRACT> 'updatePublicDrop(address,(uint80,uint48,uint48,uint16,uint16,bool))' \
  0x00005EA00Ac477B1030CE78506496e8C2dE24bf5 "(0,$NOW,$END,2,100,false)" \
  --private-key $PK --rpc-url $RPC
```

7. **Upload allowlist**: `opensea drops create-allowlist-upload <slug>` → S3 presigned POST → validate with `{"allowlist_file_token": "<key>"}`.

8. **Upload item media** in batches of ≤50 filenames via `create-item-media-upload`, persist via `save-item-media`.

9. **Save prereveal items**: `POST /drops/{slug}/prereveal-item` with `{name, description, media_token}` only (no traits).

10. **Set up allowlist via signed vouchers** (SeaDrop v1.0 has no `updateAllowListStage`; merkle `mintAllowList` will always revert with `NotActive`).

    a. Register the creator as an allowed signer — arg order is `(seadropAddr, signerAddr)`, NOT `(nft, seadrop)`:

```bash
cast send <CONTRACT> 'updateSignedMintValidationParams(address,address,(uint80,uint24,uint40,uint40,uint40,uint16,uint16))' \
  0x00005EA00Ac477B1030CE78506496e8C2dE24bf5 <CREATOR_WALLET> \
  "(1,2,$NOW,$END,100,0,0)" --private-key $PK --rpc-url $RPC
```

    b. Allow the SeaDrop as fee recipient (signed mints require `restrictFeeRecipients=true`):

```bash
cast send <CONTRACT> 'updateAllowedFeeRecipient(address,address,bool)' \
  0x00005EA00Ac477B1030CE78506496e8C2dE24bf5 0x00005EA00Ac477B1030CE78506496e8C2dE24bf5 true \
  --private-key $PK --rpc-url $RPC
```

    c. Sign an EIP712 voucher from the creator key, then the WL wallet mints:

```bash
cast send 0x00005EA00Ac477B1030CE78506496e8C2dE24bf5 \
  'mintSigned(address,address,address,uint256,(uint256,uint256,uint256,uint256,uint256,uint256,uint256,bool),uint256,bytes)' \
  <CONTRACT> 0x00005EA00Ac477B1030CE78506496e8C2dE24bf5 <MINTER> 1 \
  "(<price>,<maxWallet>,<start>,<end>,1,<maxSupply>,0,true)" <salt> <signature> \
  --value 1 --private-key $PK_MINTER --rpc-url $RPC
```

    Sign vouchers in bulk with `scripts/sign_voucher.py` (invoke through the `terminal` tool):

```bash
python3 <skill_dir>/scripts/sign_voucher.py \
  --creator-pk $PK_CREATOR --nft $CONTRACT --minter $WL_WALLET \
  --salt <unique-per-mint>
```

11. **Test public mint** via SeaDrop directly:

```bash
cast send 0x00005EA00Ac477B1030CE78506496e8C2dE24bf5 \
  'mintPublic(address,address,address,uint256)' \
  <CONTRACT> <RECIPIENT> <PAYER> 1 \
  --value 1 --private-key $PK --rpc-url $RPC
```

## Pitfalls

- `/drops/deploy` sets seadrop immutable to `0x0ac477b1...cd0b` which is EMPTY on RH chain; always redeploy with forge using canonical `0x00005EA00Ac477B1030CE78506496e8C2dE24bf5`.
- `maxSupply()` defaults to 0 — MUST call `setMaxSupply(100)` before any mint.
- `updateCreatorPayoutAddress(address)` on NFT forwards to immutable seadrop (possibly empty). Use two-arg version on NFT: `(address seadropAddr, address payoutAddr)`.
- OAuth bearer tokens expire after ~1 hour; re-run `opensea login` on 401.
- `create-item-media-upload` accepts max 50 filenames per call.
- Prereveal items endpoint does NOT accept a `traits` field.
- `cast send --create`: all flags BEFORE `--create`; anything after is constructor args.
- forge create splits bracket-wrapped arrays into separate args; compute calldata via `cast calldata` instead.
- S3 multipart uploads fail via curl subprocess (arg length); use Python `requests` for presigned POST uploads.
- Merkle `mintAllowList` on RH SeaDrop always reverts `NotActive(uint256,uint256,uint256)` — v1.0 NFT contracts lack `updateAllowListStage`. Use signed vouchers (step 10) instead.
- Signed voucher params must EXACTLY match the stored validation window: `InvalidSignedStartTime` if start differs, and `restrictFeeRecipients` MUST be true or mint reverts `SignedMintsMustRestrictFeeRecipients`.
- `updateSignedMintValidationParams` arg order: first arg = allowed seadrop address, second = signer wallet. Swapping them triggers `OnlyAllowedSeaDrop` or silently registers the wrong signer.
- `cast call` cannot simulate `--value`; payment checks (`IncorrectPayment`) only appear on `cast send`. Dry-run everything else via `cast call --from`.
- Derive per-set wallets from the mnemonic file with `cast wallet derive <mnemonic> --accounts N --insecure`; the file has a "Set N" header line before each 12-word mnemonic.
- Decode unknown revert selectors instantly via openchain: `curl -s 'https://api.openchain.xyz/signature-database/v1/lookup?function=0x<selector>'`.

## Verification

```bash
cast call <CONTRACT> 'totalSupply()(uint256)' --rpc-url $RPC
# expect ≥ 1 after test mint
```
