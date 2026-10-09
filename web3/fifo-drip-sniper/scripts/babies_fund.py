#!/usr/bin/env python3
"""Spread gas from the hub wallet to the 100 BABIES mint wallets. Dry-run unless --go."""
import json, os, re, sys, time, urllib.request
from eth_account import Account

HOME = os.path.expanduser("~")
WALLETS = json.load(open(os.path.join(HOME, "babies", "wallets.json")))
HUB_FILE = os.environ.get("BABIES_HUB", os.path.join(HOME, "babies", "hub.json"))
PER = int(float(os.environ.get("BABIES_PER", "0.0003")) * 1e18)
CHAIN_ID = 4663
RPC = os.environ.get("BABIES_RPC", "https://rpc.mainnet.chain.robinhood.com")
H = {"content-type": "application/json", "user-agent": "Mozilla/5.0"}

def rpc_batch(b, timeout=30):
    r = urllib.request.Request(RPC, data=json.dumps(b).encode(), headers=H)
    with urllib.request.urlopen(r, timeout=timeout) as f:
        return json.load(f)

def rpc(m, p):
    return rpc_batch([{"jsonrpc": "2.0", "id": 1, "method": m, "params": p}])[0]

hub = json.load(open(HUB_FILE))
hub = hub[0] if isinstance(hub, list) else hub
pk = hub["private_key"]
addr = Account.from_key(pk).address

bal = int(rpc("eth_getBalance", [addr, "latest"])["result"], 16)
gp = int(rpc("eth_gasPrice", [])["result"], 16)
print("hub      : %s" % addr)
print("balance  : %.6f ETH" % (bal / 1e18))

# skip anything already funded, and anything that already spent its one free mint
b = []
for i, w in enumerate(WALLETS):
    b.append({"jsonrpc": "2.0", "id": i * 2, "method": "eth_getBalance", "params": [w["address"], "latest"]})
    b.append({"jsonrpc": "2.0", "id": i * 2 + 1, "method": "eth_call", "params": [
        {"to": "0xfCe5F08D3167863ad8D85735bbE8Ec973dc32bCC",
         "data": "0x389fcf06" + "0" * 24 + w["address"][2:].lower()}, "latest"]})
cur = {}
for k in range(0, len(b), 150):
    for x in rpc_batch(b[k:k + 150]): cur[x["id"]] = x.get("result") or "0x0"
spent = sum(1 for i in range(len(WALLETS)) if int(cur.get(i * 2 + 1, "0x0"), 16) >= 1)
todo = [w for i, w in enumerate(WALLETS)
        if int(cur.get(i * 2, "0x0"), 16) < PER // 2 and int(cur.get(i * 2 + 1, "0x0"), 16) == 0]
print("funding %d wallets (%d already funded, %d already minted -> skipped)"
      % (len(todo), len(WALLETS) - len(todo) - spent, spent))
need = PER * len(todo) + 21_000 * gp * 3 * len(todo)
print("per wal  : %.6f ETH x %d" % (PER / 1e18, len(todo)))
print("need     : %.6f ETH  (gasPrice %.4f gwei)" % (need / 1e18, gp / 1e9))
if bal < need:
    print("SHORT by %.6f ETH — fund the hub first" % ((need - bal) / 1e18)); sys.exit(1)
if not todo:
    print("nothing to fund"); sys.exit(0)
if "--go" not in sys.argv:
    print("dry run only. re-run with --go to send."); sys.exit(0)

nonce = int(rpc("eth_getTransactionCount", [addr, "latest"])["result"], 16)
maxfee = max(gp * 3, 60_000_000)
sent = []
for j, w in enumerate(todo):
    sg = Account.sign_transaction(
        {"to": w["address"], "value": PER, "gas": 21_000, "maxFeePerGas": maxfee,
         "maxPriorityFeePerGas": 0, "nonce": nonce + j, "chainId": CHAIN_ID, "type": 2}, pk)
    raw = sg.raw_transaction.hex(); raw = raw if raw.startswith("0x") else "0x" + raw
    r = rpc("eth_sendRawTransaction", [raw])
    if "error" in r:
        print("  %s FAILED %s" % (w["address"], str(r["error"])[:90])); break
    sent.append(r["result"])
    if j % 20 == 0: print("  sent %d/%d" % (j + 1, len(todo)))
print("broadcast %d txs, waiting for inclusion..." % len(sent))
time.sleep(6)
b = [{"jsonrpc": "2.0", "id": i, "method": "eth_getBalance", "params": [w["address"], "latest"]}
     for i, w in enumerate(WALLETS)]
ok = 0
for k in range(0, len(b), 150):
    for x in rpc_batch(b[k:k + 150]):
        if int(x.get("result") or "0x0", 16) >= PER // 2: ok += 1
print("funded and confirmed: %d/%d" % (ok, len(WALLETS)))
