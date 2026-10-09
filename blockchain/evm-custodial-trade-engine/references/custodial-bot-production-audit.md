# Custodial Bot Production Audit — Durable Lessons

## Immutable accounting evidence

Do not use mutable aggregate position fields (`open_tx`, `close_tx`) as the only crash-recovery proof. DCA overwrites `open_tx`; partial sells may delete and recreate rows. Use an immutable `(chain, tx_hash)` accounting-proof ledger written in the **same database transaction** as the position mutation.

Required regression cases:

- first DCA hash remains proven after a second buy overwrites the aggregate row;
- sell proof survives partial-sell row reconstruction;
- crash after position commit but before journal `accounted` does not replay;
- overlapping reconcilers invoke accounting once.

## Automation intent snapshots

Never evaluate current automation settings against historical completed operations. For bridge-triggered buys, snapshot target CA and amount at burn creation. A legacy/completed burn without a snapshot must not gain targets when Auto Buy is enabled later.

Persist burn and target snapshot atomically. If target loading fails before broadcast, fail closed. If burn broadcast succeeds but tracking persistence fails, report the TxHash as unresolved and explicitly warn against retrying.

## Runtime isolation

A process PID and screen name are not sufficient health evidence. A launcher can inherit the wrong Telegram token or DB path from its parent environment.

For isolated dev workers:

- start with a clean environment and source only the workspace `.env`;
- use an exclusive process lock to prevent duplicate pollers/transaction workers;
- keep output visible in screen and durable via `tee`;
- verify exact cwd, executable, Telegram identity, update dispatch, and pending count;
- never run manual `getUpdates` while the bot poller is alive.

## Telegram trust boundary

Custodial wallet routes should default to private chats only. Require private chat type and `chat_id == sender_id`; reject callback messages whose private-chat owner differs from callback sender. Generated/revealed private keys should be sent separately and enrolled in durable auto-delete handling.

## SQLite secret handling

Protect the DB, WAL, and SHM files, not just the main DB. Use owner-only umask and fail startup if permissions cannot be restricted. WAL/SHM can contain wallet ciphertext, settings, user identifiers, and journal state.

## Gas-mode propagation

A gas mode is part of transaction policy. Propagate it through manual trade, automation, TP/SL, approvals, and relays. An Auto mode must fail closed if the live fee RPC fails; silently falling back to zero tip is unsafe and misleading.
