#!/usr/bin/env python3
"""Analyze a minified JS bundle for scam/drainer execution patterns.

Usage: python3 analyze_execution.py /path/to/bundle.js

Prints:
  - all contract addresses (with classification hints)
  - execution call sites: .transfer(, eth_sendTransaction, depositForBurn
  - recipientAddress assignments (hardcoded sink candidates)
  - fake-activity arrays + setInterval(Math.random) timers
  - user input fields
  - chain config zero-address flags
"""

import re
import sys


def ctx(body, start, before=200, after=250):
    s = max(0, start - before)
    return body[s : start + after].replace("\n", " ")


def main(path):
    body = open(path, "r", errors="ignore").read()
    print(f"bundle size: {len(body)} chars\n")

    # 1. addresses
    addrs = sorted(set(re.findall(r"0x[a-fA-F0-9]{40}", body)))
    print(f"=== {len(addrs)} unique 0x-addresses ===")
    for a in addrs:
        low = a.lower()
        hint = ""
        if low == "0x" + "0" * 40:
            hint = "  <-- ZERO (fake config / burn)"
        elif low in (
            "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",  # Base USDC
            "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # ETH USDC
            "0xaf88d065e77c8cc2239327c5edb3a432268e5831",  # Arb USDC
        ):
            hint = "  (Circle USDC - known good)"
        print(f"  {a}{hint}")

    # 2. execution call sites
    print("\n=== EXECUTION CALL SITES ===")
    for pat in [r"\.transfer\(", r"eth_sendTransaction", r"depositForBurn", r"\.approve\("]:
        hits = [m.start() for m in re.finditer(pat, body)]
        print(f"\n{pat}: {len(hits)} hits")
        for h in hits[:5]:
            print("  ...", ctx(body, h, 180, 200))

    # 3. recipient assignments (sink candidates)
    print("\n=== recipientAddress / beneficiary / owner ===")
    for pat in ["recipientAddress", "beneficiary", "feeRecipient", "refundTo"]:
        for m in re.finditer(pat, body):
            s = max(0, m.start() - 120)
            print(f"  [{pat}]", ctx(body, m.start(), 120, 160)[-260:])
            break  # first occurrence per pattern

    # 4. fake activity arrays
    print("\n=== FAKE ACTIVITY (hardcoded stream records) ===")
    for m in re.finditer(r"type:`?(?:OUT|IN)`?[^]]{0,120}", body):
        s = max(0, m.start() - 60)
        seg = ctx(body, m.start(), 60, 200)
        if "$" in seg or "timeAgo" in seg:
            print("  ...", seg[:260])
    for m in re.finditer(r"setInterval\([^)]{0,200}Math\.random", body):
        print("  TIMER:", ctx(body, m.start(), 80, 120)[-220:])
    for m in re.finditer(r"status:`?COMPLETED`?", body):
        print("  FAKE-COMPLETE:", ctx(body, m.start(), 100, 80)[-200:])

    # 5. user inputs
    print("\n=== USER INPUT FIELDS ===")
    inputs = set(re.findall(r"type:`(text|number|tel|email|address)`", body))
    print("  input types:", inputs if inputs else "NONE")

    # 6. chain config zero flags
    print("\n=== CHAIN CONFIG ZERO FLAGS ===")
    for m in re.finditer(r"(usdcAddress|tokenAddress|messenger|router)`?:`?(0x0{40})", body):
        print("  ZERO:", ctx(body, m.start(), 120, 40)[-180:])

    # 7. verdict hint
    n_transfer = len(re.findall(r"\.transfer\(", body))
    n_deposit = len(re.findall(r"depositForBurn", body))
    n_sendtx = len(re.findall(r"eth_sendTransaction", body))
    print("\n=== INVARIANT ===")
    print(f"  .transfer( calls:          {n_transfer}")
    print(f"  eth_sendTransaction:       {n_sendtx}")
    print(f"  depositForBurn mentions:   {n_deposit}")
    if n_deposit == 0 and (n_transfer or n_sendtx):
        print("  VERDICT HINT: executes transfers, no real bridge call -> DRAINER LIKELY")
    else:
        print("  VERDICT HINT: bridge calls present — verify they are in the execution path")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
