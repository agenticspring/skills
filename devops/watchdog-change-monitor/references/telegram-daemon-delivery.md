# Telegram Delivery for Sub-Minute Watchdogs

Tested pattern from the pools.trade 30-second monitor (Aug 2026). Use when
cron can't go below 1 minute and the user wants near-real-time alerts.

## Env loading (no hardcoded secrets)

```python
ENV_PATH = os.path.expanduser("~/.hermes/.env")

def load_env():
    env = {}
    try:
        with open(ENV_PATH) as fh:
            for line in fh:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env
```

## Direct send

```python
import urllib.parse, urllib.request, json

def tg_send(token, chat_id, text):
    try:
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}
```

## Daemon loop skeleton

```python
def main():
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat = env.get("TELEGRAM_HOME_CHANNEL", "")

    state = {}  # load from STATE file if exists
    changes, new_state = check_once(state)   # baseline: DO NOT alert
    json.dump(new_state, open(STATE, "w"))

    while True:
        time.sleep(30)
        changes, new_state = check_once(state)
        if changes:
            msg = "🔔 MONITOR:\n" + "\n".join("• " + c for c in changes)
            res = tg_send(token, chat, msg)
            state = new_state
            json.dump(state, open(STATE, "w"))
        else:
            state = new_state
            json.dump(state, open(STATE, "w"))

if __name__ == "__main__":
    main()
```

Launch with `terminal(background=true)`:
```
cd /root/.hermes/scripts && python3 <name>_daemon.py
```
Use `watch_patterns=["ALERT:", "filtered bot tx", "Baseline initialized"]` to
surface activity without polling. Kill with `process(action='kill', session_id=...)`.

## Bot-spam filter (launchpad factory watch)

```python
# decode calldata BEFORE matching markers
txt = bytes.fromhex(raw_in[2:]).decode("latin1")
low = txt.lower()
if any(m in low for m in ["cli", "automated", "auto ", "bot ", "fast_", "deploy"]):
    skip = True
# deployer tx count
cnt = get_json(f"{EXPLORER}/api/v2/addresses/{frm}/counters")
if int(cnt.get("transactions_count", "0") or 0) > 2000:
    skip = True
```

## Finding a newly created token CA when Blockscout 500s

Blockscout tx detail / internal-transactions can return 500 on fresh txs. Fall
back to RPC receipt logs: an ERC20 mint log (`Transfer` with `from=0x0`) at a
non-factory `address` IS the new token CA.

```python
# eth_getTransactionReceipt via RPC
for log in receipt.get("logs", []):
    if log["address"].lower() != FACTORY.lower():
        ca = log["address"]  # the minted token
```

For factory creation, the tx calldata itself also carries the token name as an
ASCII run (e.g. `FAST_CLI`, `Fast Rocket`) — decode `input[2:]` as latin1 and
scan printable runs to identify what the bot deployed.
