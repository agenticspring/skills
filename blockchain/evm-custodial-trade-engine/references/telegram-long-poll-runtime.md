# Telegram long-poll runtime diagnosis

Use this when a Telegram bot process is alive but commands such as `/start` receive no response.

## Safe evidence order

1. Confirm the intended process, cwd, and executable.
2. Fingerprint (do not print) dev and production bot tokens to rule out shared identity.
3. Call `getMe` and `getWebhookInfo`; record bot username, empty/nonempty webhook URL, and pending count.
4. Inspect logs for HTTP 409: `terminated by other getUpdates request`.
5. Inspect local processes and established TLS sockets to Telegram.
6. Use `sendMessage` as a non-polling API health check.

## Critical pitfall

Do not call `getUpdates` while the bot is running merely to test whether polling is active. Telegram permits one active long poll; the diagnostic call can terminate the production poll, manufacture a 409, or make the result race-dependent. If direct polling is necessary, stop the worker first, let the prior long request expire, then probe once.

## Common startup deadlock pattern

A bot may perform `SetMyCommands`, cleanup, or another Telegram API call synchronously before `Bot.Start(ctx)`. If that call hangs, the process remains alive but no updates are consumed.

Preferred sequence:

```text
initialize state
→ start polling immediately
→ run optional command registration asynchronously with ~10s timeout
```

## Clean restart verification

```text
stop old process
→ wait at least the configured long-poll timeout
→ start exactly one instance
→ monitor logs for more than one poll cycle
→ ensure no new 409 conflicts
→ send a harmless health message
→ ask user to send a fresh /start
```

`pending_update_count` alone is ambiguous. Combine it with post-start logs and network/socket evidence. Avoid deleting or advancing pending updates unless the user explicitly accepts dropping them.
