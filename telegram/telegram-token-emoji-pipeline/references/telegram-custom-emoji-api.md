# Telegram Custom Emoji API — Verified Field Notes

## Official Bot API sequence

```text
uploadStickerFile(user_id, sticker, sticker_format="static")
→ File { file_id }

createNewStickerSet(user_id, name, title, stickers, sticker_type="custom_emoji")
or addStickerToSet(user_id, name, sticker)
→ bool

getStickerSet(name)
→ StickerSet.stickers[].custom_emoji_id

sendMessage(text, entities=[{type:"custom_emoji", custom_emoji_id: ...}])
or sendPhoto(caption, caption_entities=[...])
```

## Go library mapping (`github.com/go-telegram/bot`)

```go
client.UploadStickerFile(ctx, &bot.UploadStickerFileParams{...})
client.CreateNewStickerSet(ctx, &bot.CreateNewStickerSetParams{StickerType: "custom_emoji", ...})
client.AddStickerToSet(ctx, &bot.AddStickerToSetParams{...})
set, err := client.GetStickerSet(ctx, &bot.GetStickerSetParams{Name: pack})

models.MessageEntity{
    Type: models.MessageEntityTypeCustomEmoji,
    Offset: utf16Offset,
    Length: utf16Length,
    CustomEmojiID: emojiID,
}
```

`SendMessageParams` uses `Entities`; `SendPhotoParams` and `EditMessageCaptionParams` use `CaptionEntities`.

## Sticker set limits and naming

- A custom-emoji sticker set is limited to 200 assets.
- Name format ends with `_by_<bot_username>`.
- A set is owned by the supplied Telegram user ID.
- Maintain predictable pack sequence and serialize append operations.

## Real fallback validation: Ponshood on Robinhood

Token:

```text
chain: robinhood / 4663
address: 0x432C99bBD9dc1d9040087598d7Cf40502d7cC20b
name: Ponshood
symbol: PONSHOOD
```

Read-only RPC returned `name` and `symbol`, but launcher methods `logo()` and `liquidityPool()` reverted. DexScreener nevertheless returned a valid base-token pair with:

```text
GET /token-pairs/v1/robinhood/{token}
→ matching baseToken.address
→ info.imageUrl at cdn.dexscreener.com
```

This proves direct-to-V3 tokens need indexer artwork fallback even if core token metadata does not expose a logo.

## Capability test result

A dev bot successfully:

```text
created a custom emoji sticker set
→ uploaded a normalized static PNG
→ read custom_emoji_id using getStickerSet
→ sent the entity to a developer DM
```

The initial implementation incorrectly matched `uploadStickerFile.file_id` to the `StickerSet` entry. The materialized sticker's file ID differed. For a single serialized append, use the final sticker returned by `getStickerSet` and require a non-empty `custom_emoji_id`.
