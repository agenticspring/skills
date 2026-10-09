# DexScreener Token Logo Fallback

## Verified endpoint

```text
GET https://api.dexscreener.com/token-pairs/v1/{chain}/{tokenAddress}
```

The response is an array of pairs. For a token-logo lookup:

1. normalize requested chain and address;
2. select a pair where both `chainId` and `baseToken.address` match;
3. read `info.imageUrl`;
4. accept only `https://cdn.dexscreener.com/...` URLs;
5. fetch under a strict timeout and a small size limit;
6. require `Content-Type: image/*`, decode image, normalize and hash it.

Do not use a pair where the target is only `quoteToken`: that would associate the wrong visual asset with the token.

## Why a fallback is required

Direct-to-DEX tokens may be valid tokens with live pools but lack launcher-specific views such as `logo()` and `liquidityPool()`. A Robinhood Ponshood example had valid name/symbol and DexScreener `info.imageUrl`, while those launcher calls reverted.

## Telegram API result handling

```text
uploadStickerFile → File (temporary file id)
createNewStickerSet/addStickerToSet → boolean
getStickerSet → Sticker.custom_emoji_id (final inline entity ID)
```

Do not treat the upload file ID as the custom emoji ID. Telegram can materialize a different sticker file ID inside a set.

## Product behavior

Use the provider only for a cache miss. After global `(chain, token)` cache is ready, every user reuses the cached `custom_emoji_id`; no further provider request, logo download, image transform, or sticker upload occurs.
