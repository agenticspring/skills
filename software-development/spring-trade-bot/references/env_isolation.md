# Environment & Token Isolation for spring-trade

**Problem observed:** The bot responded as the Hermes bot (`8660...RxMY`) instead of @Eloncolibot (`8967...BJEU`). The screen session inherited the agent's environment variable.

**Root cause:** `TELEGRAM_BOT_TOKEN` was already set in the parent shell. The project's `.env` was not overriding it because `loadDotEnv` skips existing vars, and `source .env` in subshell didn't propagate to the binary. User repeatedly said "Lo salah pake bot tele besti" and "Gua run sendiri aja".

**Correct start commands (tested in this session):**

1. **Explicit export (most reliable):**
   ```bash
   cd /root/spring-trade
   TOK=$(grep '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2-)
   KEY=$(grep '^MASTER_ENCRYPTION_KEY=' .env | cut -d= -f2-)
   screen -dmS spring-trade bash -c "
     export TELEGRAM_BOT_TOKEN='$TOK'
     export MASTER_ENCRYPTION_KEY='$KEY'
     cd /root/spring-trade
     exec ./spring-trade 2>&1 | tee bot.log
   "
   sleep 3
   pgrep -fa './spring-trade' | grep -v bash   # must show exactly 1 binary
   grep -c Conflict bot.log                    # must be 0
   ```

2. **Using env -i (clean environment):**
   ```bash
   env -i PATH="/usr/local/go/bin:/usr/bin:/bin" \
     TELEGRAM_BOT_TOKEN="$(grep '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2-)" \
     MASTER_ENCRYPTION_KEY="$(grep '^MASTER_ENCRYPTION_KEY=' .env | cut -d= -f2-)" \
     screen -dmS spring-trade bash -c 'cd /root/spring-trade; exec ./spring-trade 2>&1 | tee bot.log'
   ```

**Verification:**
- `tr '\0' '\n' < /proc/$(pgrep -f './spring-trade' | head -1)/environ | grep TELEGRAM_BOT_TOKEN`
- Should show the project's token (starts with 8967...).

**Pitfall:** `unset` in the same shell is not enough if the screen is launched from a parent that re-sets it. Always export explicitly in the command string. Never rely on `source .env` alone in a screen -dmS bash -c.

This reference was added after the session where repeated token leakage caused the agent to start the wrong bot and the user had to run it himself.
