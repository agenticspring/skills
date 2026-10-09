---
name: telegram-custom-emoji-pipeline
description: Build and validate Telegram Bot API custom-emoji pipelines for dynamic application assets, with safe caching, sticker-set rotation, and staged external capability tests.
version: 1.0.0
platforms: [linux]
metadata:
  hermes:
    tags: [telegram, bot-api, custom-emoji, stickers, media, caching]
---

# Telegram Custom Emoji Pipeline

Use this skill when a Telegram bot needs to create, manage, or render custom emoji—especially when turning dynamic application assets such as token logos into inline custom emoji.

## Core facts

Telegram Bot API supports the required sticker-set lifecycle:

```text
uploadStickerFile
→ createNewStickerSet(sticker_type="custom_emoji")
→ addStickerToSet
→ obtain/use Sticker.custom_emoji_id
→ send as MessageEntity(type="custom_emoji")
```

A custom emoji is an existing Telegram sticker asset identified by `custom_emoji_id`; it is **not** a remote image URL. To render a new token logo inline, the logo must first become a custom-emoji sticker.

## Architecture

Keep the UI transport separate from emoji generation:

```text
Token metadata / trusted logo provider
        ↓
remote fetch boundary (validated)
        ↓
decode + normalize static image
        ↓
content hash / cache lookup
        ↓
sticker-set gateway
        ↓
custom_emoji_id cache
        ↓
caption/text entity rendering
```

Default to a hybrid UI:

- Existing photo/token card remains the primary detailed trade UI.
- Custom emoji enhances compact headers, alerts, scan lists, and notifications.
- Inline keyboard buttons use Unicode emoji only; do not depend on custom-emoji rendering there.

## Required data model

Persist an idempotent cache keyed by normalized chain and token address:

```text
chain
 token
 image_hash
 custom_emoji_id
 sticker_set
 state: pending | ready | failed
 failure
 created_at
 updated_at
```

Priority on lookup:

```text
ready cache by chain+CA
→ content hash dedupe
→ create/upload path
→ generic chain/default fallback
```

Never key a dynamic token asset only by ticker or name: symbols collide across chains and can be spoofed.

## Sticker-set management

- `createNewStickerSet` creates a set owned by a Telegram user; `user_id` is required.
- Pack name must end in `_by_<bot_username>` and comply with Telegram naming rules.
- Custom-emoji sticker sets hold at most **200** stickers.
- Use deterministic pack rotation, e.g. `app_tokens_01_by_botname`, then `02` once capacity is reached.
- The bot may modify sets that it created. Do not assume it can edit arbitrary third-party sets.

## Image processing and abuse controls

Treat logo URLs and token metadata as untrusted input.

1. Cache hit before fetch.
2. Fetch only through a hardened HTTP boundary: HTTPS allowlist/policy, redirect limits, DNS/IP validation, no localhost/private/link-local targets, timeout, response-size cap.
3. Decode image bytes; never trust extension or declared MIME type.
4. Enforce byte and pixel limits.
5. Center crop/fit into a bounded square PNG or WEBP; strip source metadata by re-encoding.
6. SHA-256 the normalized output for deduplication.
7. Queue work and rate-limit per user/token/chain. Never make Telegram sticker upload part of a synchronous CA paste path.
8. On any failure, render the normal card/default icon and record a bounded failure state.

## Capability-first rollout

Before production integration, prove the actual bot entitlement and rendering behavior:

1. Implement all cache, image, planner, and entity code with local fakes and tests.
2. Keep the feature flag disabled by default.
3. Ask the user for explicit approval before creating a public sticker set or uploading any asset.
4. Perform exactly one benign static test asset upload on the dev bot.
5. Send a DM to the developer and verify actual inline rendering, not merely HTTP success.
6. Capture the non-secret result; only then enable automated creation.

Do not claim a bot may use custom emoji solely because pack creation endpoints exist. Render permission/entitlement is a separate live capability check.

## Entity rendering

Bot API supports `MessageEntity` with:

```text
type = "custom_emoji"
custom_emoji_id = <Telegram-issued ID>
```

For Go Telegram libraries, verify support for both:

- `SendMessageParams.Entities`
- `SendPhotoParams.CaptionEntities` and `EditMessageCaptionParams.CaptionEntities`

Offsets are UTF-16 code units. Test entity offset construction with non-ASCII text and HTML/Markdown formatting interactions. Prefer a small dedicated renderer instead of manually calculating offsets throughout handlers.

## Token-logo provenance pitfall

A token can be tradable through a direct Uniswap V3 pool yet not implement launchpad-specific methods like `logo()` or `liquidityPool()`. Do not infer absence of a token image from those reverts.

For tokens outside the launcher ABI, use a trusted indexer/logo-provider fallback. Keep that provider behind an interface and preserve a no-logo fallback.

## Verification checklist

```bash
gofmt -w <changed-go-files>
go vet ./...
go test -race -shuffle=on -count=1 ./...
go build ./cmd/bot
```

Additionally verify:

- cache hit causes no gateway call;
- repeated normalized image hash causes no duplicate sticker creation;
- the 200-item boundary rotates to a new pack;
- missing/malformed artwork never blocks the normal token card;
- no secrets, bot token, owner ID, or generated custom emoji IDs are committed.

## References

- See `references/bot-api-custom-emoji.md` for the condensed official Bot API contract and a staged test recipe.
