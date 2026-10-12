# Telegram Bot Pattern for Automation Scripts

## Pattern

Telegram bot that wraps a Python script, with:
- Auth check (only specific user ID)
- Direct execution via subprocess
- Donor/config management via file
- Batch processing

## Key Components

### Auth Check
```python
AUTHORIZED_USER_ID = 6832598147

def is_authorized(update: Update) -> bool:
    return update.effective_user.id == AUTHORIZED_USER_ID
```

### Script Execution
```python
result = subprocess.run(
    ["python3", SCRIPT_PATH, auth_token, ct0, target],
    capture_output=True, text=True, timeout=120
)
```

### Config File (donor.txt)
```
# Format: name|auth_token|ct0
donor1|token1|ct0_1
donor2|token2|ct0_2
```

### Bot Commands
```python
app.add_handler(CommandHandler("gift", gift))
app.add_handler(CommandHandler("batch", batch))
app.add_handler(CommandHandler("list_donors", list_donors))
app.add_handler(CommandHandler("reload", reload_donors))
```

## Deployment

```bash
# Start in screen
screen -dmS tgbot bash -c 'python3 bot.py'

# Restart
screen -S tgbot -X quit
screen -dmS tgbot bash -c 'python3 bot.py'

# Check logs
tail -f /path/to/bot.log
```

## Pitfalls

1. **Markdown parsing** — Remove `parse_mode='Markdown'` if messages contain special chars
2. **Token exposure** — Never expose bot token in responses
3. **Screen sessions** — Use `notify_on_complete=true` for long tasks
4. **Subprocess timeout** — Always set timeout for script execution
