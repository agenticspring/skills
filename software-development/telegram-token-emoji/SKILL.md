---
name: telegram-token-emoji
description: "Build dynamic Telegram custom-emoji pipelines for token cards: global cache, safe logos, pack rotation, and in-place UI updates."
version: 1.0.0
---

# Telegram Dynamic Token Emoji Pipeline

Use this for Telegram bots that turn dynamic token/logo artwork into inline custom emoji. Especially relevant to token scanners, trading cards, alerts, and watchlists.

## Product contract

A user scanning a token must never receive an extra DM or a second card just because an asynchronous emoji job completed.

```text
scan token
→ render the normal existing card immediately
→ cache hit: show custom emoji immediately
→ cache miss: use normal fallback icon
→ generate/upload in background once
→ edit that same card in place when ready
```

Never block initial token rendering on emoji generation. Never use a per-user asset cache.

## Required architecture

```text
Global persistent cache: chain + normalized token address
                    ↓
In-process single-flight: chain:token key
                    ↓
Trusted metadata/logo provider
                    ↓
Bounded image fetch + normalize + hash
                    ↓
Telegram custom emoji sticker set
                    ↓
Store custom_emoji_id globally
                    ↓
All later users reuse the same asset
```

### Cache record

Store at least:

```text
chain
normalized token address
image hash
custom emoji ID
sticker set name
state: pending | ready | failed
failure diagnostic
created/updated timestamps
```

The cache must be global across users. A repeated scan by any user is a read-only cache hit: no provider fetch, no image download, no sticker upload, and no new sticker slot.

### Concurrency

Use a keyed single-flight mechanism around `chain:token` before any network/upload path. Concurrent scanners of the same novel token wait for one job result. Different tokens may proceed independently. Ensure the worker has a bounded context and cannot overwrite a card after the user moved to another token/menu.

## Telegram Bot API flow

A custom emoji is a sticker in a set whose `sticker_type` is `custom_emoji`.

```text
uploadStickerFile
→ temporary File/file_id

createNewStickerSet OR addStickerToSet
→ boolean success

getStickerSet
→ final Sticker.custom_emoji_id
```

Do **not** assume `uploadStickerFile` returns `custom_emoji_id`; it returns a File. Read the sticker set after write and obtain `Sticker.custom_emoji_id` there. Telegram may materialize a different final `file_id` than the temporary upload file ID. After an append, the final sticker entry is the newly added asset.

Custom emoji sets hold at most 200 stickers. Persist/count the active global set and rotate only at capacity. Naming must end with `_by_<bot_username>` and remain within Telegram's limit.

## Logo acquisition safety

Treat token logo URLs as untrusted input.

1. Prefer on-chain logo metadata only when present and valid.
2. For tokens without launcher metadata, use a trusted indexer/provider fallback.
3. Allowlist both scheme and image host. Do not fetch arbitrary project/website URLs.
4. Apply HTTP timeout, response-size cap, `image/*` content-type check, decode-first validation, and a second decoded-image size bound.
5. Re-encode clean static PNG after center crop/fit and resize; hash output with SHA-256 for dedupe.
6. Keep provider response size bounded too.

For a DexScreener provider implementation, only accept a result when the requested CA matches the pair's **base token** on the requested chain. Do not attach a quote-token image by mistake. See `references/dexscreener-custom-emoji.md`.

## UI integration

- Existing photo token cards may remain the primary card transport for full-width keyboards.
- Custom emoji enriches the title/header rather than replacing dynamic token imagery.
- For HTML mode, render `<tg-emoji emoji-id="...">🔹</tg-emoji>` only if a ready ID exists; otherwise render no entity/fallback Unicode.
- Before editing asynchronously, confirm the active message still represents the same normalized token address.
- Do not log bot tokens, owner IDs, custom emoji IDs, or raw token imagery metadata unnecessarily.

## Test sequence

1. RED: global cache normalizes chain/address and reuses a ready ID.
2. RED: image normalizer produces deterministic bounded square output and rejects invalid/oversize content.
3. RED: pack planner appends below 200 and rotates at 200.
4. RED: single-flight runs only one job for concurrent same-token scans.
5. RED: trusted provider rejects a quote-token match and unknown logo host.
6. GREEN each behavior, then run race tests.
7. Only after local tests pass and explicit user approval, create one benign public test emoji asset and verify one in-place render.

## Pitfalls

- Do not generate a new asset for every user scan.
- Do not send a DM just to confirm emoji generation.
- Do not use `uploadStickerFile` file ID as the custom emoji ID.
- Do not make the first token card wait for provider/upload latency.
- Do not fetch token project URLs directly; token metadata is attacker controlled.
- Do not blindly use `logo()` on-chain as the only source; direct-to-DEX tokens may not implement it.
- Do not copy production bot state, credentials, database, or sticker cache into a development sandbox.
