#!/usr/bin/env python3
"""Sweep leftover gas from the mint wallets back to the hub. Dry-run unless --go."""
import json, os, re, sys, urllib.request
from eth_account import Account

RPC = os.environ.get("BABIES_RPC", "https://rpc.mainnet.chain.robinhood.com")
H = {"content-type": "application/json", "user-agent": "Mozilla/5.0"}
def rb(b, t=30):
    r = urllib.request.Request(RPC, data=json.dumps(b).encode(), headers=H)
    with urllib.request.urlopen(r, timeout=t) as f: return json.load(f)
def rpc(m, p): return rb([{"jsonrpc": "2.0", "id": 1, "method": m, "params": p}])[0]

_h = json.load(open(os.environ.get("BABIES_HUB", os.path.expanduser("~/babies/hub.json"))))
HUB = Account.from_key((_h[0] if isinstance(_h, list) else _h)["private_key"]).address
ws = json.load(open(os.path.expanduser("~/babies/wallets.json")))
gp = int(rpc("eth_gasPrice", [])["result"], 16); maxfee = max(gp * 3, 60_000_000)
cost = 21_000 * maxfee
bals = {}
b = [{"jsonrpc": "2.0", "id": i, "method": "eth_getBalance", "params": [w["address"], "latest"]} for i, w in enumerate(ws)]
for k in range(0, len(b), 150):
    for x in rb(b[k:k + 150]): bals[x["id"]] = int(x.get("result") or "0x0", 16)
tot = sum(bals.values()); movable = [(i, v) for i, v in bals.items() if v > cost * 2]
print("hub %s | %d wallets hold %.6f ETH | sweepable %d wallets" % (HUB, len(ws), tot / 1e18, len(movable)))
if "--go" not in sys.argv:
    print("dry run. re-run with --go"); sys.exit(0)
n = 0
for i, v in movable:
    sg = Account.sign_transaction(
        {"to": HUB, "value": v - cost, "gas": 21_000, "maxFeePerGas": maxfee,
         "maxPriorityFeePerGas": 0, "nonce": int(rpc("eth_getTransactionCount", [ws[i]["address"], "latest"])["result"], 16),
         "chainId": 4663, "type": 2}, ws[i]["private_key"])
    raw = sg.raw_transaction.hex(); raw = raw if raw.startswith("0x") else "0x" + raw
    r = rpc("eth_sendRawTransaction", [raw])
    if "error" not in r: n += 1
print("swept %d wallets back to hub" % n)
