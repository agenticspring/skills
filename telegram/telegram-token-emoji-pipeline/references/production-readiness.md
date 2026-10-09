# Telegram token custom-emoji production readiness

Use this checklist for dynamic token-logo emojis in Telegram bots.

## Official entitlement gate

Creating a custom-emoji sticker set and obtaining `custom_emoji_id` does **not** prove that a bot may render it in messages. Before debugging offsets repeatedly, verify one official entitlement path:

- the actual bot owner recorded by @BotFather has active Telegram Premium; or
- the bot has an eligible additional username acquired through Fragment.

The application admin, sticker-set owner, and @BotFather bot owner are distinct identities. Premium on the wrong account does not satisfy the gate.

When entitlement is absent, Telegram may display the regular placeholder glyph instead of the artwork. Treat this as an entitlement hypothesis before changing rendering code.

## Correct entity contract

- Upload/add the static custom emoji, then call `getStickerSet` (or `getCustomEmojiStickers`) to obtain/verify `Sticker.CustomEmojiID`; upload/create/add responses do not directly yield the final custom emoji ID.
- The message text must contain exactly one regular emoji placeholder matching `Sticker.emoji`.
- Entity offsets and lengths use UTF-16 code units. A placeholder such as `🔹` has `Offset=0`, `Length=2` when it starts the visible text.
- Prefer explicit `MessageEntity{type=custom_emoji}` for deterministic composition.
- Do not combine explicit `entities` with `parse_mode` and assume both will apply.
- If rich formatting and links are needed, convert trusted markup to visible text plus explicit `bold`, `italic`, `code`, `text_link`, and `custom_emoji` entities. Calculate all offsets over the final visible text in UTF-16 units.
- Disable link previews independently on both send and edit paths; `text_link` remains clickable while previews stay off.

## UX rule: no notification spam

Custom-emoji generation is enrichment, not a user-visible event stream:

1. Show the existing token card immediately with a regular fallback glyph.
2. Resolve/generate in the background.
3. Edit that same card in place when ready.
4. Never send a separate DM, completion message, or second card merely to announce emoji readiness.
5. Before editing, verify the user is still viewing the same chain/token card so stale workers cannot overwrite newer navigation.

Capability tests that send a message are external side effects. Request explicit approval and clearly label them as temporary proof tests.

## Global deduplication architecture

Cache globally by normalized `chain + token address`, not by user. Store at least:

- normalized image hash;
- `custom_emoji_id`;
- sticker-set name;
- state (`pending`, `ready`, `failed`);
- timestamps and bounded failure metadata.

For cache hits, all users reuse the same ID without downloading or uploading again.

Add two synchronization layers:

- per-token single-flight to prevent duplicate generation for the same chain/token;
- serialized sticker-pack mutation to prevent concurrent appends from associating a token with the wrong last sticker.

Pack selection and capacity checks must be synchronized with the append. At 199 items, two different-token jobs must not both select the same pack and leave the second failing instead of rotating. Database counts are advisory; Telegram's sticker-set contents are authoritative. Multi-process deployments require a distributed/database lock or a single dedicated pack writer, not only process-local mutexes.

Add failed-state cooldown/backoff so persistent provider, Telegram, or entitlement failures do not retry on every scan.

## Secure logo retrieval

- Resolve logos only through trusted providers and verify the requested CA is the matching base token on the expected chain.
- Require HTTPS and an explicit hostname allowlist.
- Enforce metadata and image byte limits, MIME validation, decode validation, deterministic crop/resize, metadata stripping, and content hashing.
- Validate every redirect target against the same URL policy or disable redirects. Validating only the initial URL leaves an SSRF gap.
- Never fetch arbitrary on-chain/IPFS/project URLs directly into this pipeline without a separate hardened retrieval policy.

## Verification sequence

Do not declare readiness from unit tests alone.

1. Unit-test UTF-16 offsets, markup-to-entity conversion, global cache, same-token single-flight, pack rotation boundaries, concurrent appends, redirects, size/MIME limits, and failure cooldown.
2. Run race tests, vet, and build.
3. Query Telegram read-only to verify asset type, dimensions, sticker-set membership, placeholder alt, and ID.
4. Verify entitlement on the actual @BotFather owner.
5. Perform one approved live send and edit test.
6. Inspect the returned Telegram message entities and the rendered client artwork.

If repeated fixes do not change the rendered result, stop patching. Re-read official documentation, separate asset validity from entitlement and serialization, and gather server-returned entities before attempting another code change.
