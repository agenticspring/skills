---
name: telegram-bot-custom-emoji
description: Build, cache, and render dynamic Telegram custom emoji for bot content without duplicate uploads or chat spam.
version: 1.0.0
---

# Telegram Bot Dynamic Custom Emoji

Use this for a Telegram bot that turns trusted dynamic artwork (for example, a token logo) into a reusable Telegram custom emoji and displays it inline in an existing bot card.

## Operating principle

Treat a custom emoji as a globally reusable asset, **not a per-user UI artifact**.

```text
canonical identity = chain + normalized token address
cache hit          = reuse stored custom_emoji_id
cache miss         = one generation job globally
```

Never create/upload a new emoji merely because another user scanned the same asset.

## Required architecture

```text
Token card request
  ├─ cache lookup (chain + address)
  │   └─ ready → render stored custom_emoji_id immediately
  └─ miss → render normal card immediately
             └─ background, single-flight generation
                  ├─ trusted metadata/logo provider
                  ├─ bounded image fetch + decode
                  ├─ normalize static asset
                  ├─ upload/add sticker
                  ├─ read custom_emoji_id from sticker set
                  ├─ persist global cache
                  └─ edit the SAME card in place
```

Use a persistent cache with at least:

```text
chain, token, image_hash, custom_emoji_id, sticker_set,
state (pending|ready|failed), failure, created_at, updated_at
```

## Telegram API flow

The reliable create path is:

```text
uploadStickerFile
→ createNewStickerSet OR addStickerToSet
→ getStickerSet
→ read Sticker.custom_emoji_id
```

Do **not** assume `uploadStickerFile`, `createNewStickerSet`, or `addStickerToSet` returns a custom emoji ID. The first returns a temporary File object; create/add returns a boolean.

Sticker sets are user-owned. Keep the owner user ID in secret configuration, never source code. Rotate packs at Telegram’s custom-emoji capacity (currently 200 items per set) using durable database state, not a fresh in-memory counter.

## Hard entitlement gate: creation is not rendering permission

A bot can create a custom-emoji pack, receive a nonempty `custom_emoji_id`, and retrieve it through `getCustomEmojiStickers` while Telegram still ignores the entity and displays the Unicode fallback glyph.

Per Telegram's current Bot API rules, custom emoji entities can be used only when either:

- the bot purchased an additional username on Fragment; or
- the account that is the bot's actual owner in **@BotFather** has an active Telegram Premium subscription, for messages directly sent by the bot to private, group, or supergroup chats.

Do not confuse these identities:

```text
application admin ID
sticker-set owner user_id
actual bot owner in @BotFather
```

Only the Bot API entitlement decides rendering permission. Verify entitlement **before** building or debugging the full dynamic pipeline. If the real client displays the placeholder despite a valid entity and asset, stop patching offsets, HTML, cache, and image generation until ownership/Premium/Fragment eligibility is confirmed.

```text
create/add succeeded + valid custom_emoji_id
≠ bot is entitled to render custom emoji entities
```

The capability gate passes only when a real Telegram client visibly renders the artwork.

## Rendering: explicit entity, not HTML tag

For dynamic custom emoji in bot text, prefer explicit `MessageEntity`:

```go
models.MessageEntity{
    Type:          models.MessageEntityTypeCustomEmoji,
    Offset:        0,
    Length:        2, // UTF-16 code units for one astral placeholder emoji
    CustomEmojiID: cachedID,
}
```

Use a stable placeholder glyph at the beginning of **visible plain text**, then replace that exact UTF-16 span via the entity. The glyph must match the materialized sticker's regular `Sticker.emoji` alt. Pass `Entities` on **both** `SendMessage` and `EditMessageText`.

Do not combine `ParseMode` with explicit `Entities`; entities replace parse mode. Offset `0` against raw HTML such as `<b>🔹 ...` points at `<`, not the visible emoji. Either generate all formatting as explicit entities or use plain text while validating custom-emoji rendering.

When the card also needs bold, italic, code, and clickable footer links, convert trusted internal markup into **visible text plus explicit entities**:

```text
custom_emoji
bold / italic / code
text_link
```

Calculate every offset and length in UTF-16 code units. Never strip `<a href>` tags into labels merely to stabilize custom-emoji offsets—that creates a UI regression where `Scan`, explorer, social, and project links look interactive but are not clickable.

Disable explorer/link previews explicitly on both send and edit paths:

```go
LinkPreviewOptions: &models.LinkPreviewOptions{IsDisabled: true}
```

A `text_link` entity remains clickable while previews stay disabled. Test both properties together: links work, preview cards do not spawn.

Do not rely only on `<tg-emoji>` HTML markup in a card/update path; verify the real client renders the asset rather than the fallback glyph.

## No-spam UI rule

Never send a separate DM, notification, or token-card message solely because an emoji is ready. Capability tests also need explicit user approval and should be limited to one message; once capability is known, normal debugging must inspect returned entities/logs rather than repeatedly messaging the user.

Correct behavior:

```text
new token scan → send one normal card
emoji becomes ready → edit that same card
cached token scan → send/edit one card with its emoji immediately
```

Before asynchronously editing, verify the user still has that token as the active card. Otherwise an old worker can overwrite a newer card.

## Concurrency and deduplication

Use three layers:

1. Durable cache for all users and restarts.
2. Per-process single-flight keyed by normalized `chain:token` so simultaneous scans of one token cause one fetch/upload.
3. A mutex/queue per sticker-pack name. If the gateway identifies the new asset as the final sticker returned after append, concurrent appends to the same pack can map token A to token B's emoji unless writes are serialized.

**Pack selection and append must be one coordinated operation.** Locking only inside the Telegram gateway is too late if two callers can both select a 199-item pack before either appends. Under the same serialization boundary, re-read the authoritative Telegram sticker count, append if `<200`, or replan to the next pack. If multiple bot processes may share packs, use a cross-process DB/advisory lock or enforce one writer process; an in-memory mutex is insufficient.

Also hash normalized image bytes to avoid redundant sticker assets when artwork is reused. Pass the detected chain into the **initial** send/edit cache lookup; an empty chain key makes a ready global cache look like a miss until a later async refresh.

Apply negative caching/backoff to persistent failures. A `failed` row that is retried on every card open wastes provider/Telegram traffic—especially while Premium entitlement is inactive. Store bounded failure categories plus `attempt_count`/`next_retry_at` (for example 1m → 5m → 30m → 6h), and reset only after the cooldown or an explicit entitlement/config change.

## Trust boundary for artwork

Do not fetch arbitrary `logo()` / IPFS / website URLs into a Telegram upload worker.

Use an allowlisted metadata provider first. Enforce:

- HTTPS only;
- fixed hostname allowlist;
- provider confirms requested token is the base token on the requested chain;
- response size cap;
- `image/*` content type;
- bounded image decode;
- re-encode normalized artwork, stripping source metadata;
- validate **every redirect target** against the same HTTPS/hostname/IP policy, cap redirect depth, or disable redirects entirely. Validating only the initial CDN URL leaves an SSRF/open-redirect gap because standard HTTP clients follow redirects automatically.

If no trusted provider logo exists, retain the normal fallback card and do not create an emoji.

## Verification checklist

1. Unit test cache hit: no gateway call.
2. Unit test concurrent same token: one generation invocation.
3. Unit test untrusted logo URL rejection.
4. Integration proof: upload one benign asset, then `getStickerSet` yields a nonempty `custom_emoji_id`.
5. Real-client proof: the card displays artwork, not placeholder glyph.
6. Confirm cache hit from a second user/token-card render does not fetch or upload again.
7. Verify no additional message/DM is sent during async completion.

## Pitfalls

- `custom_emoji_id` must come from the materialized `Sticker` in `getStickerSet`, not from the upload File ID.
- Use UTF-16 offsets for `MessageEntity`, not Go byte indexes or rune indexes.
- If an old photo-card design is replaced with text, Telegram cannot edit photo → text; plan one controlled replacement or keep the message type consistent.
- Do not swallow async worker errors. Log chain, token, and wrapped error; persist failure state if retry policy needs it.
- A cache row marked ready proves asset generation, **not** client rendering. Validate entity serialization and actual Telegram display separately.

## References

- See [references/token-emoji-pipeline.md](references/token-emoji-pipeline.md) for concrete Go/Bot API notes and verified failure modes.
- See [references/pre-premium-readiness-audit.md](references/pre-premium-readiness-audit.md) for the audit checklist when entitlement is inactive and visual rendering cannot yet be proven.
