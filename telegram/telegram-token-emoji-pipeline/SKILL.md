---
name: telegram-token-emoji-pipeline
description: Build and verify dynamic Telegram custom-emoji pipelines from trusted token artwork, with cache, sticker-set rotation, and safe fallback UI.
version: 1.0.0
author: spring
license: Private
platforms: [linux]
metadata:
  hermes:
    tags: [telegram, custom-emoji, stickers, token-metadata, golang]
---

# Telegram Dynamic Token Custom Emoji Pipeline

Use this skill when a Telegram bot should turn dynamic token artwork into inline custom emoji, especially for token scanners, trading cards, watchlists, and alerts.

## Core model

Telegram does not convert a logo URL into a custom emoji automatically. The service must:

```text
token address
→ trusted metadata provider returns image URL
→ validate + download artwork
→ decode / normalize static PNG
→ upload sticker file
→ create or append custom-emoji sticker set
→ get sticker set
→ read Sticker.custom_emoji_id
→ cache chain + address → custom emoji ID
→ render MessageEntity custom_emoji in text/caption
```

Use photo cards as the normal token-detail surface when they provide important UX such as wide inline keyboards. Custom emoji improves the title/header; it should not automatically replace a photo-card UI.

## Verified Telegram Bot API facts

- `createNewStickerSet` supports `sticker_type="custom_emoji"`; a set is owned by a Telegram `user_id`.
- Bot-created sets can be edited by that bot.
- `addStickerToSet` caps custom-emoji sets at **200 stickers**.
- `uploadStickerFile` returns a temporary `File`, **not** a `custom_emoji_id`.
- `createNewStickerSet` and `addStickerToSet` return a boolean.
- After writing, call `getStickerSet`; read `Sticker.custom_emoji_id` from the resulting sticker.
- The `file_id` returned from upload may differ from the materialized set sticker's `file_id`. For a single serialized append, the final sticker in the returned set is the newly appended asset.
- Send custom emoji using a `MessageEntity` with `type="custom_emoji"` and its `custom_emoji_id`. For Go Telegram bot libraries, use the entity field appropriate to the transport: `Entities` for text, `CaptionEntities` for photos/captions.
- Entity offsets use **UTF-16 code units** per Telegram API. Do not compute them with raw bytes or rune counts when text can contain non-BMP characters.

## Architecture

### 1. Persistent cache

Create a cache table keyed by normalized:

```text
chain + token address
```

Suggested fields:

```text
image_hash
custom_emoji_id
sticker_set
state: pending | ready | failed
failure
created_at
updated_at
```

Cache behavior:

```text
ready cache hit → return custom emoji immediately
same normalized image hash → reuse asset; never upload duplicate
missing logo / provider miss → fallback UI, do not block token card
upload failure → persist failure state with bounded retry policy
```

### 2. Trusted logo lookup

Do not fetch arbitrary token-supplied URLs in a bot that handles public CAs.

Recommended order:

```text
on-chain token logo metadata, if available
→ trusted indexer/provider image URL
→ fallback chain/default branding
```

For a DexScreener provider integration:

- Query `GET /token-pairs/v1/{chain}/{token}`.
- Select only a pair where the requested token is the **base token** on the requested chain; do not accidentally use a quote-token image.
- Use `info.imageUrl` only after host validation.
- Restrict logo downloads to HTTPS and an allowlist such as `cdn.dexscreener.com`.
- Treat provider data as untrusted despite trusted origin: enforce response byte limits, `image/*` content type, actual decoder validation, redirect policy, and timeouts.

### 3. Image normalization

Before Telegram upload:

```text
limit compressed input size
→ decode actual bytes (do not trust extension/content type alone)
→ center crop square
→ resize to a fixed static emoji size
→ encode clean PNG/WebP
→ SHA-256 normalized output
```

This strips source metadata and makes dedupe deterministic. Include JPEG decoding because public token artwork commonly arrives as JPEG.

### 4. Sticker-set lifecycle

Name packs predictably:

```text
<prefix>_<sequence>_by_<bot_username>
```

Use one active pack until 200 assets, then create the next pack.

**Concurrency requirement:** pack selection, capacity verification, append, and post-write lookup must be one coordinated operation. A mutex around only the Telegram append is insufficient: two different tokens can both select a pack at 199 entries before either acquires that lock. Re-check authoritative Telegram pack size under the lock and replan to the next pack when full. Process-local locks also do not protect multiple bot processes; use a DB lease/advisory lock or guarantee a single writer.

Serialize writes per pack so “last sticker after append” remains safe to identify the newly added item. Do not derive capacity solely from local ready-cache rows; Telegram pack contents are authoritative because manual changes or a failed DB write can desynchronize them.

For first production rollout, use a local/dev bot and a single harmless artwork capability test before enabling background generation.

### 5. UI behavior

Do not make a user wait for an external upload while viewing a token:

```text
paste CA
→ show the existing token card immediately
→ queue/cache custom emoji work
→ once ready, edit that same card in place
```

Never send a separate “emoji ready” DM/message as part of normal flow. Capability-test messages are exceptional, require approval, and must be clearly identified as external proof actions.

For text cards that need custom emoji **and** rich formatting/links, do not mix `parse_mode` with explicit entities or strip anchors with a regex. Render trusted markup into visible text plus explicit `MessageEntity` records (`custom_emoji`, `bold`, `italic`, `code`, `text_link`) with UTF-16 offsets. Set `LinkPreviewOptions.IsDisabled=true` on both send and edit so links stay clickable without spawning explorer previews.

Keep normal fallback if entitlement, provider, image normalization, or Telegram upload fails. Confirm rendered behavior in a real client before declaring success; creation of a pack and receipt of a `custom_emoji_id` prove storage, not visual entitlement/rendering.

## TDD workflow

Write tests before each unit:

1. Cache normalization and upsert/read behavior.
2. Image normalization, malformed-image rejection, and size limits.
3. Pack planner behavior below/at the 200-item limit.
4. Trusted provider selection: chain/base-token match and host rejection.
5. Image fetch URL-validation-before-request and non-image rejection.
6. Resolver: cache hit bypasses gateway, missing logo returns fallback, valid image persists ready state.

Gateway tests must use an in-memory fake. Only the explicit capability test may call Telegram.

## Capability test protocol

An externally visible test creates a public sticker asset. Require clear user approval before it.

1. Use isolated dev bot credentials and a dev-only data directory.
2. Create/upload one benign static image.
3. Read `custom_emoji_id` from `getStickerSet`.
4. Send one direct message with the `custom_emoji` entity.
5. Confirm the emoji renders in the target DM.
6. Remove temporary test commands afterwards; preserve only reusable adapter code and tests.

## Entitlement gate

Before debugging entity offsets repeatedly, verify Telegram's eligibility rule for bot-authored custom emoji. Pack creation/upload capability and valid `custom_emoji_id` retrieval do **not** prove that the bot may render custom emoji in messages. Verify the current official Bot API requirement (for example, Premium on the actual @BotFather owner account or an eligible paid additional username) and record which account owns the bot. Admin IDs and sticker-set owner IDs are different identities.

When eligibility is absent, stop visual patch loops. Keep the Unicode fallback and defer one real-client send/edit verification until entitlement is restored.

**Evidence rule:** never report the rendering issue as fixed merely because code compiles, entities are returned, the sticker exists, or an API call succeeds. A fix is complete only after a real Telegram client visibly shows the artwork on both initial send and in-place edit. After one failed visual retest, stop stacking speculative patches: re-read the official eligibility/entity contract, inspect the server-returned message entities, and isolate entitlement versus serialization before editing again.

## Failure control

Persist failed generation state with a bounded retry policy. Reopening a card must not repeatedly call metadata/image/Telegram APIs during a persistent provider or entitlement failure. Use a cooldown/backoff such as 1m → 5m → 30m → 6h, with an explicit retry/reset path. Sanitize persisted/logged upstream errors so request URLs or credentials cannot leak.

For trusted image fetching, validate **every redirect target** or disable redirects. Validating only the initial allowlisted CDN URL is not an SSRF boundary because default HTTP clients follow redirects.

## Pitfalls

1. **Do not assume on-chain `logo()` is present.** Direct-to-V3 tokens can have valid pools and no launcher metadata; use a trusted indexer fallback.
2. **Do not treat `uploadStickerFile` output as a custom emoji ID.** Query the sticker set after create/add.
3. **Do not match uploaded `file_id` blindly.** Telegram can materialize a different file ID in the set.
4. **Do not synchronously generate an emoji in the critical token-card path.** It increases latency and risks rate-limit failures.
5. **Do not use arbitrary token/project logo URLs.** This creates SSRF and oversized/decompression-risk paths.
6. **Do not generate an unlimited asset set per pasted CA.** Cache, dedupe by normalized image hash, rate limit, queue, and rotate packs.
7. **Do not use custom emoji directly in inline keyboard labels as a required feature.** Use Unicode for buttons; custom entities belong in text/captions.
8. **Do not conflate token custom emoji with token photo rendering.** Photo cards remain better for dynamic visual identity and full-width Telegram keyboard UX.

## References

- See `references/telegram-custom-emoji-api.md` for the verified API sequence, Go library mapping, and a real direct-to-V3 token fallback example.
- See `references/production-readiness.md` for the entitlement gate, explicit rich-text entity contract, global deduplication, no-spam UX, pack concurrency, redirect security, failure cooldown, and final live-render verification checklist.
