# Telegram Bot API — Dynamic Custom Emoji Reference

## Verified API surface

Telegram Bot API exposes:

- `uploadStickerFile`
- `createNewStickerSet`
- `addStickerToSet`
- `getCustomEmojiStickers`

A text/caption entity uses:

```text
type: custom_emoji
custom_emoji_id: <Telegram-issued ID>
```

## Creating a custom-emoji set

`createNewStickerSet` requires:

```text
user_id     owner of the sticker set
name        1–64 chars; English letters/digits/underscore; ends _by_<bot_username>
title       1–64 chars
stickers    1–50 InputSticker objects
sticker_type = custom_emoji
```

`needs_repainting` is optional and applies to custom-emoji sets. Do not enable it for token-logo art unless recoloring is intentional.

## Adding assets

`addStickerToSet` requires `user_id`, set `name`, and an `InputSticker`.

- Only sticker sets created by the bot are editable through this API.
- Custom emoji sticker sets support up to 200 stickers.
- Use rotating set names, e.g. `dezbot_tokens_01_by_<bot_username>`.

`InputSticker` accepts a preexisting Telegram `file_id`, an HTTP URL for static sticker media, or multipart upload (`attach://...`). Static custom assets should be normalized locally before upload rather than delegating arbitrary URL fetches to Telegram.

## Operational implication

Custom emoji are not dynamically derived by Telegram from token metadata. A bot must upload/create/add the token image as a custom emoji sticker and cache the returned `custom_emoji_id`. A system that appears instant is usually using a cache, a pre-indexer, or a fallback before the background creation job finishes.

## Required proof test

Before production automation:

1. Use a disposable dev bot and isolated database/key.
2. Create a dedicated test custom-emoji sticker set with one static image.
3. Obtain the emoji ID.
4. Send it as a `custom_emoji` entity to the owner's private chat.
5. Verify visual rendering, not only HTTP/API success.

API availability does not substitute for validating entitlement/rendering in the actual target chat type.
