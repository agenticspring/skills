## Dev bot launch verification (2026-07-18)

For `/root/dezbot-dev`, a `screen` session name is not proof of bot liveness. The verified launch checklist is:

1. Run from exact workspace: `/root/dezbot-dev`.
2. Confirm process executable resolves to `/root/dezbot-dev/dezbot`.
3. Confirm `/proc/<pid>/cwd` resolves to `/root/dezbot-dev`.
4. Confirm launcher logs `DEV_BOT_LAUNCH` followed by `bot mulai`.
5. Confirm Telegram `getWebhookInfo.pending_update_count` decreases after a user command, and logs show an update dispatch marker.
6. A screen pane may be visually quiet when output is redirected; use a visible `tee` launcher/status banner and verify process + Telegram behavior rather than screen appearance alone.

Never claim Telegram responsiveness from PID/startup log alone.