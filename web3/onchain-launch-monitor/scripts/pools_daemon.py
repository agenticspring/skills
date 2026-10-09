#!/usr/bin/env python3
"""Real-time launchpad monitor daemon (sub-minute tier).

Adapt the CONFIG block per launchpad, then run via:
  terminal(background=true, command="cd ~/.hermes/scripts && python3 pools_daemon.py")

Checks every LOOP_SECONDS: website teaser->live, GitHub addresses-file commit,
and factory-contract tx cursor. On change, pushes a Telegram alert directly
using TELEGRAM_BOT_TOKEN + TELEGRAM_HOME_CHANNEL from ~/.hermes/.env.

State shared with the cron-tier script at ~/.hermes/scripts/pools_monitor_state.json.
First run initializes baseline only (no alert). Stdlib only.
"""
import hashlib, json, os, re, time, urllib.request, urllib.parse

STATE = os.path.expanduser("~/.hermes/scripts/pools_monitor_state.json")
ENV_PATH = os.path.expanduser("~/.hermes/.env")
UA = {"User-Agent": "Mozilla/5.0"}

# ---- CONFIG: adapt per launchpad ----
SITE_URL = "https://pools.trade"
TEASER_MARKER = "Coming soon"
GH_COMMITS_URL = "https://api.github.com/repos/Uniswap/sdks/commits?path=sdks/liquidity-launcher-sdk/src/addresses.ts&per_page=1"
GH_RAW_URL = "https://raw.githubusercontent.com/Uniswap/sdks/main/sdks/liquidity-launcher-sdk/src/addresses.ts"
FACTORY = "0x000000e200088D55C39a11F609E5F667729ad49b"
EXPLORER = "https://robinhoodchain.blockscout.com"
RPC = "https://rpc.mainnet.chain.robinhood.com"
LOOP_SECONDS = 30
# ---- end CONFIG ----

ADDR_RE = re.compile(r"0x[a-fA-F0-9]{40}")
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


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


def get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def get_json(url, timeout=20):
    return json.loads(get(url, timeout))


def rpc_call(method, params):
    data = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(RPC, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode()).get("result")


def tg_send(token, chat_id, text):
    try:
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}


def find_ca_from_receipt(tx_hash):
    """Blockscout 500s on fresh txs; the receipt's mint log IS the CA."""
    try:
        receipt = rpc_call("eth_getTransactionReceipt", [tx_hash])
        if not receipt:
            return ""
        for log in receipt.get("logs", []):
            topics = log.get("topics", [])
            if topics and topics[0] == TRANSFER_TOPIC and topics[1] and int(topics[1], 16) == 0:
                return log.get("address", "")
    except Exception:
        pass
    # fallback: blockscout internal creates
    try:
        itx = get_json(f"{EXPLORER}/api/v2/transactions/{tx_hash}/internal-transactions")
        for t in itx.get("items", []):
            c = t.get("created_contract") or {}
            if c.get("hash"):
                return c["hash"]
    except Exception:
        pass
    return ""


def check_once(state):
    changes = []
    new_state = {}

    # 1. Website
    try:
        html = get(SITE_URL)
        title = "Pools"
        m = re.search(r"<title>([^<]*)</title>", html)
        if m:
            title = m.group(1)
        m = re.search(r'name="description" content="([^"]*)"', html)
        desc = m.group(1) if m else ""
        teaser = TEASER_MARKER in html
        html_for_hash = re.sub(r'nonce="[^"]+"', "NONCE", html)  # CSP nonce is random per request
        h = hashlib.sha256(html_for_hash.encode()).hexdigest()[:16]
        old = state.get("site_hash")
        if old is not None and old != h:
            changes.append(f"{SITE_URL} CHANGED: title={title!r} desc={desc!r} teaser={'YES' if teaser else 'NO (LIVE?)'}")
        if not teaser:
            cas = set(ADDR_RE.findall(html))
            if cas:
                changes.append("CA FOUND ON SITE: " + ", ".join(sorted(cas)))
        new_state["site_hash"] = h
        new_state["site_title"] = title
        new_state["site_desc"] = desc
        new_state["site_teaser"] = teaser
    except Exception:
        pass

    # 2. GitHub commit cursor
    try:
        commits = get_json(GH_COMMITS_URL)
        if isinstance(commits, list) and commits:
            sha = commits[0]["sha"]
            date = commits[0]["commit"]["author"]["date"]
            msg = commits[0]["commit"]["message"].split("\n")[0]
            old = state.get("gh_sha")
            if old is not None and old != sha:
                changes.append(f"GitHub addresses UPDATED: {sha[:10]} @ {date} — {msg}")
            new_state["gh_sha"] = sha
            new_state["gh_msg"] = msg
            new_state["gh_date"] = date
    except Exception:
        pass

    # 3. Raw addresses file content
    try:
        raw = get(GH_RAW_URL)
        rh = hashlib.sha256(raw.encode()).hexdigest()[:16]
        old = state.get("raw_hash")
        if old is not None and old != rh:
            changes.append(f"addresses content changed (hash {old} → {rh})")
            cas = sorted(set(ADDR_RE.findall(raw)))
            if cas:
                changes.append("CAs in addresses: " + ", ".join(cas[:20]))
        new_state["raw_hash"] = rh
    except Exception:
        pass

    # 4. Factory tx cursor -> new CA
    try:
        txs = get_json(f"{EXPLORER}/api/v2/addresses/{FACTORY}/transactions?filter=to")
        items = txs.get("items", [])
        if items:
            newest = items[0]
            tx_hash = newest.get("hash", "")
            ts = newest.get("timestamp", "")
            method = newest.get("method", "")
            frm = (newest.get("from") or {}).get("hash", "")
            old_tx = state.get("factory_tx")
            if old_tx is not None and old_tx != tx_hash:
                ca = find_ca_from_receipt(tx_hash)
                changes.append(
                    f"NEW FACTORY TX {ts}: {method} from {frm[:18]}… tx={tx_hash[:18]}…"
                    + (f"\n   🪙 NEW CA: {ca}" if ca else "")
                )
            new_state["factory_tx"] = tx_hash
            new_state["factory_ts"] = ts
    except Exception:
        pass

    return changes, new_state


def main():
    env = load_env()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    chat = env.get("TELEGRAM_HOME_CHANNEL", "")

    state = {}
    if os.path.exists(STATE):
        try:
            state = json.load(open(STATE))
        except Exception:
            state = {}

    changes, new_state = check_once(state)
    try:
        json.dump(new_state, open(STATE, "w"))
    except Exception:
        pass
    if changes:
        print("Baseline initialized (skipped):", changes)

    while True:
        time.sleep(LOOP_SECONDS)
        changes, new_state = check_once(state)
        if changes:
            msg = "🔔 LAUNCH MONITOR:\n" + "\n".join("• " + c for c in changes)
            msg += f"\n\nDetail: {SITE_URL}"
            print("ALERT:", msg)
            if token and chat:
                res = tg_send(token, chat, msg)
                print("TG send:", "ok" if not res.get("error") else res.get("error"))
        state = new_state
        try:
            json.dump(state, open(STATE, "w"))
        except Exception:
            pass


if __name__ == "__main__":
    main()
