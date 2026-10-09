# TG bot isolation + long-running jobs (session 2026-07-20)

User-confirmed architecture after "pisah aja" → option **2**.

## Full pool isolation
Bot `/root/webnovel-tg-bot` owns:
- `accounts.txt`, `proxy.txt`, `device_profiles.json`, `avatars/`

Autoreg `/root/webnovel-autoreg` is only `signup.py` code source for `/create`.
Force env on create subprocess:
`WEBNOVEL_ACCOUNTS_FILE`, `WEBNOVEL_PROXY_FILE`, `DEVICE_PROFILES_FILE`,
`WEBNOVEL_AVATAR_DIR`, `WEBNOVEL_AVATAR_USED_FILE`.

Seed/copy accounts once when splitting; do not auto-delete autoreg copy unless asked.

## Unlimited create + stream + Stop
- `/create N` has **no max 5** cap.
- Stream signup stdout with `python -u` / `PYTHONUNBUFFERED=1`.
- Soft timeout `min(6h, max(15m, N*4m))`.
- Inline **🛑 Stop** → cooperative cancel; keep partial successes.

## Powerstone / bookmark jobs
- Inter-account delay only (not start-delay).
- Stream progress on same message.
- Same **🛑 Stop** mid-run (including during delay sleep).
- Partial report always.

## Device profiles on bot
- Bot-local `wn/device_profiles.py` + bot JSON.
- When opening mobile from bot, pass explicit UA/impersonate; avoid autoreg profile file.
- chrome120/124 only for mobile impersonate.

## Related stale notes
Older text in `references/telegram-powerstone-bot.md` may still mention shared autoreg pool / max-5 create — prefer this file + SKILL.md pitfalls 14–18 until that reference is refreshed.
