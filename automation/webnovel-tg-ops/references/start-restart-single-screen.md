# Start / Restart Webnovel TG (Single Screen)

## When

User: “nyalakan bot webnovel tg” / bot dead after reboot / `Dead ???` screen socket.

## Sequence (mandatory)

```bash
screen -wipe || true
# kill orphan poller if any (avoid Telegram 409)
pkill -f '/root/webnovel-tg-bot/.venv/bin/python -m bot.main' 2>/dev/null || true
screen -dmS webnovel-tg bash -lc 'cd /root/webnovel-tg-bot && unset TELEGRAM_BOT_TOKEN TELEGRAM_TOKEN && exec ./run.sh'
sleep 3
screen -ls | grep webnovel-tg
screen -S webnovel-tg -X hardcopy /tmp/webnovel-tg-hardcopy.txt
```

## Expected hardcopy

```text
Starting bot. admins={<TELEGRAM_ALLOWED_USERS_REDACTED>} accounts=...
getMe 200
setMyCommands 200
deleteWebhook 200
Application started
getUpdates 200
```

## Hard rules

- Screen name: **`webnovel-tg` only** — never dual `webnovel-tg-bot`.
- Always `unset TELEGRAM_BOT_TOKEN TELEGRAM_TOKEN` so bot-local `.env` wins.
- Dead sockets must be wiped before recreate.
- Health = hardcopy/process proof, not merely “screen listed”.

## Verified example

2026-08-01: wiped dead `webnovel-tg`, started single instance, `@webnovelpowerbot` Application started, 350 accounts, getUpdates 200.