#!/usr/bin/env python3
"""Grow the BABIES wallet pool to N total. Appends only; existing keys untouched."""
import json, os, secrets, sys
from eth_account import Account

N = int(sys.argv[1])
D = os.path.expanduser("~/babies"); os.makedirs(D, exist_ok=True)
F = os.path.join(D, "wallets.json")
w = json.load(open(F)) if os.path.exists(F) else []
have = len(w)
for i in range(have, N):
    a = Account.from_key("0x" + secrets.token_hex(32))
    w.append({"i": i, "address": a.address, "private_key": a.key.hex()})
old = os.umask(0o077); json.dump(w, open(F, "w"), indent=1); os.umask(old)
os.chmod(F, 0o600)
open(os.path.join(D, "addresses.txt"), "w").write("\n".join(x["address"] for x in w) + "\n")
print("pool: %d -> %d wallets (added %d)" % (have, len(w), len(w) - have))
