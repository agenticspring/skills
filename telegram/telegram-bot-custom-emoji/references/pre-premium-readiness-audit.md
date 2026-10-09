# Pre-Premium Readiness Audit

Use this when the @BotFather owner's Premium is inactive, so real custom-emoji rendering cannot yet be proven.

## Official gate

Rendering requires either an active Telegram Premium subscription on the bot's actual @BotFather owner or an additional username purchased for the bot on Fragment. Sticker-pack ownership, app admin IDs, successful pack creation, and a valid `custom_emoji_id` do not grant rendering permission.

## Read-only checks

1. Persistent cache row is `ready` and keyed by normalized `chain + token`.
2. `getCustomEmojiStickers(custom_emoji_id)` returns exactly one sticker with:
   - `type = custom_emoji`;
   - matching `custom_emoji_id` and sticker set;
   - bounded dimensions;
   - `Sticker.emoji` equal to the placeholder glyph used in message text.
3. Initial send and edit both use explicit `MessageEntity{type: custom_emoji}`.
4. Entity offset targets visible plain text and length is measured in UTF-16 units.
5. `ParseMode` is absent when explicit entities are provided.
6. Link previews are disabled on send and edit.
7. Initial render passes the detected chain into the global cache key.
8. Same-token work is single-flight; same-pack appends are serialized.
9. Async completion edits the current card only and never sends a DM/new card.
10. Trusted image provider, MIME/size/decode limits, re-encoding, and normalized-image hashing are active.

## Verification gate

Run race tests, vet, and build. Report two separate statuses:

```text
code/API readiness: ready or blocked
actual visual rendering: waiting for entitlement or visually verified
```

Never claim visual readiness from a successful API response alone. After Premium is restored, restart the bot and perform one real-client card refresh. Artwork replacing the fallback glyph is the final proof.
