# NFT Card UX Reference

Use when adding an NFT card to Telegram that should feel like the existing Spring Trade token card.

## Target interaction

```text
paste contract or OpenSea asset URL
  -> compact NFT card
  -> one BUY fast-action button only when eligible wallets exist
  -> edit the same message into wallet-label buttons
  -> edit the same message into a concise preparation preview
```

Do not start with the full transaction lifecycle or a long safety explanation. Preserve the execution boundary in code, but keep the first UI slice quick to review.

## Compact card hierarchy

Recommended order:

```text
NFT name · symbol
collection or token ID
chain
contract
separator
floor
best listing
eligible-wallet count
BUY unavailable when count is zero
optional TEST REVIEW override marker
small read-only footer
```

Use the same message for transitions. Avoid one new Telegram message per button click.

## Keyboard contract

Initial card:

```text
[🟢 BUY · N]
```

No eligible wallet:

```text
no BUY keyboard
card text contains BUY unavailable
```

Wallet picker:

```text
[🟢 Phrase 1] [🟢 Phrase 2] [🟢 Phrase 3]
```

Use at most three wallet buttons per row. “Phrase N” is a display label only; never expose seed phrases, private keys, signer references, or session tokens.

Selection preview must include price and explicit:

```text
signed=false
broadcast=false
```

## Callback rules

- Bind callback tokens to actor, chat, intent, version, and expiry.
- Permit bounded wallet-label IDs containing `-` or `_`; test the parser with those separators.
- On `nft_buy`, load the current stored NFT view and recalculate the eligible wallet set.
- On wallet selection, reject a wallet that is no longer eligible.
- Answer callback queries immediately and edit the current message.
- Do not invoke signer, broadcaster, buy executor, or any financial adapter from the eligibility UI.

## Review runtime

For a user review, start a separate bot identity with:

```text
explicit reviewer allowlist
public wallet manifest only
app mode read_only
signer=false
broadcaster=false
```

A test-only eligibility override is allowed solely to make the buttons visible, but it must be labeled in the card as `TEST REVIEW override` and must never claim on-chain eligibility or wallet balance. Startup logs should show bot identity, wallet count, review flag, override flag, signer=false, and broadcaster=false without printing secrets.

If a bot token was posted in chat, stop the review process after review and rotate it through BotFather. Never persist the token in the repository or notes.

## Audit checklist

- [ ] Card is compact and information-first.
- [ ] BUY is one fast-action button, not repeated per wallet.
- [ ] BUY is absent when no wallet is eligible.
- [ ] Wallet buttons are compact (three per row).
- [ ] Existing message is edited rather than spawning a message per transition.
- [ ] `Phrase N` is only a label.
- [ ] Test override is visibly labeled.
- [ ] Callback IDs with hyphens parse correctly.
- [ ] Stale/ineligible wallet selection is rejected.
- [ ] No signer/broadcast/executor call is reachable.
- [ ] Focused UI tests, typecheck, secret scan, build, and existing bot tests pass.

## Related skills

`telegram-bot-media-assets` covers photo/card media and message recycling. `transactional-trade-safety` covers the later execution boundary. `spring-trade-pitfalls` covers the existing bot's callback and message-spam pitfalls.
