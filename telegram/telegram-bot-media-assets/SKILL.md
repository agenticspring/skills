---
name: telegram-bot-media-assets
description: Build Telegram bot flows that render dynamic token/media assets, including photo cards, sticker/custom-emoji packs, caching, and safe test isolation.
version: 1.0.0
platforms: [linux]
metadata:
  hermes:
    tags: [telegram, bot-api, custom-emoji, stickers, media, token-cards]
---

# Telegram Bot Media Assets

Use this skill when a Telegram bot must display dynamic visual assets such as token logos, generated banners, stickers, or inline custom emoji.

## Decide the rendering model first

Do not assume custom emoji are automatically generated from an image URL.

| Need | Use |
|---|---|
| Exact arbitrary token logo, immediately | Photo message or generated image card |
| Compact inline brand/status/token icon | Custom emoji entity |
| Full-width inline keyboard and rich visual card | Photo message |
| Action icon in an inline keyboard | Unicode emoji only |

Telegram custom emoji are pre-existing custom-emoji stickers referenced by `custom_emoji_id`. A token image can become one only after an upload/create/add sticker workflow.

## Official custom-emoji pipeline

1. Resolve token metadata and a candidate logo URL.
2. Fetch only through a hardened media fetcher: HTTPS, allowlisted public address resolution, response-size cap, timeout, MIME sniffing, image decode, and metadata stripping.
3. Normalize to a square static PNG/WEBP that meets Telegram sticker requirements.
4. Deduplicate by normalized image hash and `(chain, token address)`.
5. Upload or reuse a sticker through `uploadStickerFile`.
6. Create the first set using `createNewStickerSet` with `sticker_type=custom_emoji`, or add to a bot-created set using `addStickerToSet`.
7. Persist the resulting `custom_emoji_id` and use a `custom_emoji` MessageEntity in text/captions.
8. If upload is pending/fails, render a chain/default Unicode indicator or preserve the existing photo-card fallback; do not block a token lookup.

## Sticker-set lifecycle

- A custom emoji sticker set is owned by a Telegram user (`user_id`), not the bot identity alone.
- Set names must end in `_by_<bot_username>` and meet Telegram short-name rules.
- `createNewStickerSet` accepts 1–50 initial stickers.
- `addStickerToSet` can manage only sets created by the bot and custom-emoji sets are limited to 200 stickers.
- Rotate sets before full and store which set owns each asset.
- Creating a set does not by itself prove the bot may render custom emoji in every target chat. Validate the actual bot entitlement and rendering behavior with a single private-chat proof test before building production automation.

## Token emoji cache model

Persist at least:

```text
chain
contract_address
logo_url
image_hash
sticker_set_name
custom_emoji_id
status: pending | ready | failed
created_at
updated_at
```

Resolution priority:

```text
exact chain+contract cache
→ image-hash cache
→ in-flight job marker
→ fallback visual
```

Never use token ticker alone as the primary key; symbols collide across chains and can be spoofed.

## UX model

Recommended default is hybrid:

```text
text/caption header: cached custom emoji when ready
photo card: token logo or generated placeholder
inline keyboard: Unicode labels/icons
```

A compact text-only mode can use custom emoji, but it loses the wide button bubble and rich visual identity of a photo card.

## Background work and rate limits

Do not create sticker assets synchronously in the CA-paste request path.

```text
paste CA
→ show current card/fallback immediately
→ enqueue deduplicated asset job
→ create/cache custom emoji
→ edit the existing card/header only if still current
```

Bound concurrency, retry transient Telegram failures, and rate-limit new asset creation. Treat arbitrary CA/logo inputs as untrusted; a public user must not be able to exhaust sticker-set capacity or make the bot fetch internal network addresses.

## Test isolation

When trialing media/sticker behavior against a production bot, create a source-only development copy:

```text
copy code
exclude .env, runtime data, databases, binary artifacts, and VCS metadata
use a separate bot token
use a fresh master encryption key
use a fresh database path/data directory
```

Run build and tests before starting the test bot. Do not start polling or create public sticker assets until the user explicitly asks.

## Verification sequence

1. Build and unit-test the isolated copy.
2. Create one static test asset in a dedicated dev set.
3. Confirm API success.
4. Send one `custom_emoji` entity to the owner’s private chat.
5. Confirm it renders visually.
6. Only then add logo fetching, cache persistence, background jobs, and pack rotation.

## References

- `references/custom-emoji-bot-api.md` — condensed Telegram Bot API facts and implementation checklist.
