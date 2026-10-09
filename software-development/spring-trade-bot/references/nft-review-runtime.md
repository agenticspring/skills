# NFT Review Runtime

Use this for a user-facing Telegram review of the compact NFT card UX. It is a review harness, not a production trading deployment.

## Required startup contract

1. Build and run the latest artifact; never launch stale `dist/` output after a source change.
2. Use a dedicated test bot identity, never an existing production bot token.
3. Load the token from the process environment only; do not write it to the repository, `.env` in the project, logs, notes, or chat output.
4. Restrict Telegram access to the explicit reviewer user ID. An empty allowlist must fail closed.
5. Start with `read_only`, `signer=false`, `broadcaster=false`, and FCFS disabled.
6. Use a public wallet manifest containing addresses/labels only. Never import private keys or seed phrases for a UI review.
7. If the reviewer needs BUY buttons visible before real eligibility is wired, use an explicit test-only eligibility override. Label the card `TEST REVIEW override`; never present it as on-chain eligibility or balance proof.
8. Verify startup output includes bot identity, review mode, wallet count, test-override state, and signer/broadcaster false. Do not print secrets.
9. After the review, stop the process and rotate any token that was pasted into chat or otherwise exposed. Then restart only with the replacement token.

## Review scenarios

- Paste a direct contract with an explicit chain.
- Paste an OpenSea asset URL and verify contract/token/chain normalization.
- Confirm the compact card shows NFT name, token ID, chain, contract, floor/best listing, wallet count, and read-only state.
- Confirm BUY is absent when no wallet is eligible.
- Confirm BUY shows only eligible wallet labels (`Phrase N`), never seed phrase material or full signer secrets.
- Confirm wallet selection produces a preview and does not call signer, broadcaster, or execution adapter.

## Evidence vocabulary

`started` means the dedicated review process emitted a successful startup identity. `read_only` means no write surface is wired. `TEST REVIEW override` means UI-only synthetic eligibility. Do not report a real buy or real eligibility without chain/API evidence and a transaction/receipt boundary.

## Pitfalls

- Do not reuse a production bot token or the same Telegram polling identity as another bot process.
- Do not treat a successful `/getMe` or polling startup as proof that NFT lookup works; exercise the `/nft` path.
- Do not leave a test eligibility override enabled when moving to a real resolver.
- Do not claim that a UI BUY button means an execution route is active.
