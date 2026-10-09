# Telegram Bot API — Custom Emoji Reference

## Official lifecycle

Telegram Bot API documents this path for custom emoji sticker assets:

```text
uploadStickerFile
createNewStickerSet
addStickerToSet
MessageEntity(type="custom_emoji", custom_emoji_id=...)
```

### `createNewStickerSet`

Required inputs include:

```text
user_id
name
title
stickers (1–50 initial InputSticker items)
```

Set:

```text
sticker_type = "custom_emoji"
```

The sticker-set name is 1–64 characters, uses letters/digits/underscores, starts with a letter, and ends in:

```text
_by_<bot_username>
```

`needs_repainting` is available only for custom emoji sets and is appropriate for monochrome/context-color artwork—not arbitrary full-color token logos.

### `addStickerToSet`

The bot can add to a set it created. A custom-emoji set has a 200-sticker limit. Rotate deterministic set names at capacity.

### `InputSticker`

Static artwork may be `.PNG` or `.WEBP`; animated/video assets have separate formats. An input can be uploaded multipart or refer to a Telegram file ID. For dynamic untrusted token artwork, normalize locally first and upload the generated static PNG.

### `MessageEntity`

Custom emoji is rendered by a text/caption entity:

```text
type: custom_emoji
custom_emoji_id: Telegram-issued ID
```

The entity offset and length use UTF-16 code units.

## Staged capability test

Do this only with explicit approval because it creates a Telegram asset:

1. Use a dev bot and a developer-owned test user ID.
2. Generate one harmless static PNG locally.
3. Create one custom-emoji sticker set, or append to a known dev-only set.
4. Obtain the returned sticker custom emoji ID.
5. Send one direct message containing the entity.
6. Confirm that the recipient sees the inline emoji, not just a successful endpoint response.
7. Store no bot token or developer ID in repository code/tests/logs.

## Integration warning

Success creating a sticker set does not by itself prove the bot can render custom emoji in target chats. Verify the exact dev bot + intended chat class before enabling the feature.
