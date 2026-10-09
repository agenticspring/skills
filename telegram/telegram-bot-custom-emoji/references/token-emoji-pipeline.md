# Dynamic Token Emoji Pipeline — Field Notes

## Bot API fact pattern

```text
uploadStickerFile       → File (temporary upload identity)
createNewStickerSet     → bool
addStickerToSet         → bool
getStickerSet           → Sticker[] containing custom_emoji_id
```

Use the `custom_emoji_id` from the sticker-set response. Do not compare it to the upload File ID; Telegram may materialize a different file identity in the set.

## Observed failure classes

### 1. Token logo exists but is unsafe to fetch
A token’s `logo()`/IPFS metadata URL can be present yet outside the image allowlist. If the worker tries it first and immediately fails, it may never reach the trusted metadata fallback.

**Correct order:** query the trusted provider first for dynamic Telegram artwork. Only fetch URLs that pass an explicit allowlist validator.

### 2. Cache ready but screen displays fallback glyph
This proves generation/upload worked but rendering did not. Investigate in this order:

1. **Entitlement:** confirm the actual @BotFather owner has active Telegram Premium, or the bot purchased an additional username on Fragment. Sticker-set ownership and application admin IDs do not grant render permission.
2. **Asset:** verify `getCustomEmojiStickers(custom_emoji_id)` returns a `custom_emoji` sticker.
3. **Serialization:** send `Entities: []MessageEntity{custom_emoji}` on both initial send and edit; use UTF-16 offsets and do not mix raw HTML offsets with visible-text offsets.
4. **Real client:** visually confirm artwork replaces the fallback glyph.

Do not iterate through repeated code patches when entitlement is unverified. A valid cached asset is not evidence of render permission.

### 3. Silent async failure
A background generator that returns errors into an ignored goroutine gives the user a permanent fallback icon with no diagnosis.

**Fix:** log and/or persist the wrapped error with the normalized chain/token key. Do not use a separate DM to report success; update the existing card only.

## Compact Go sketch

```go
text := "🔹 Token Name | TKN / USDC"
entities := []models.MessageEntity{{
    Type:          models.MessageEntityTypeCustomEmoji,
    Offset:        0,
    Length:        2, // UTF-16 units for 🔹
    CustomEmojiID: cachedID,
}}

_, err := bot.EditMessageText(ctx, &bot.EditMessageTextParams{
    ChatID: chatID, MessageID: messageID,
    Text: text,
    Entities: entities, ReplyMarkup: keyboard,
})
```

The placeholder is normal text when no cache ID exists. When an ID exists, the entity replaces its display.

## Preserving card links while using explicit entities

A custom-emoji entity often forces a card away from `ParseMode=HTML` toward explicit entities. Do not solve this by regex-stripping all markup: it silently destroys explorer/social links and formatting.

For trusted internally generated card markup, render:

```text
<b>…</b>       → MessageEntity bold
<i>…</i>       → MessageEntity italic
<code>…</code> → MessageEntity code
<a href=…>…</a>→ MessageEntity text_link
placeholder    → MessageEntity custom_emoji
```

Offsets are UTF-16 units in the final visible text. Test nested/non-BMP cases. Send/edit with `LinkPreviewOptions.IsDisabled=true`: `text_link` stays clickable while explorer previews remain suppressed.

## Product behavior

- First scan: show one card immediately, then edit it after generation.
- Repeat scan from any user: use the global cache immediately.
- No extra DM or “emoji ready” card.
- If the user navigated away, skip the late edit.
