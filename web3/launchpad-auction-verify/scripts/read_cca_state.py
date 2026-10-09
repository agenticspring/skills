#!/usr/bin/env python3
"""Read CCA auction state on Robinhood Chain (chain 4663).

Usage:
  python3 read_cca_state.py <AUCTION_ADDRESS> [RPC_URL]

Reads the core state functions of a Continuous Clearing Auction and prints a
verdict-friendly summary. Stdlib only.

Selectors verified against Uniswap liquidity-launcher-sdk CCA_ABI.
"""
import json
import subprocess
import sys

RPC_DEFAULT = "https://rpc.mainnet.chain.robinhood.com"

CALLS = {
    "endBlock": "0x083c6323",
    "isGraduated": "0x9e5f2602",
    "claimBlock": "0x37dfbc4b",
    "currencyRaised": "0x998ba4fc",
    "remainingSupply": "0xda0239a6",
    "sweepUnsoldTokensBlock": "0x8a76bfe4",
    "tokensRecipient": "0x3c05e7bc",
}


def rpc_call(rpc: str, to: str, data: str) -> str:
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "eth_call",
        "params": [{"to": to, "data": data}, "latest"],
    })
    out = subprocess.run(
        ["curl", "-s", "--max-time", "15", "-X", "POST",
         "-H", "Content-Type: application/json", "-d", payload, rpc],
        capture_output=True, text=True, timeout=20,
    )
    try:
        return json.loads(out.stdout).get("result", "")
    except Exception:
        return ""


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    auction = sys.argv[1]
    rpc = sys.argv[2] if len(sys.argv) > 2 else RPC_DEFAULT

    print(f"Auction: {auction}")
    print(f"RPC:     {rpc}\n")
    for label, selector in CALLS.items():
        res = rpc_call(rpc, auction, selector)
        if not res or res == "0x":
            print(f"{label:24s} (no data)")
            continue
        v = int(res, 16)
        if label == "isGraduated":
            print(f"{label:24s} {bool(v)}")
        else:
            print(f"{label:24s} {v}")

    print("\nVerdict guide:")
    print("  isGraduated=true  -> bids settle to FULL tokens, no ETH refund")
    print("  past endBlock + !graduated -> failed auction; creator can sweepUnsoldTokens")
    print("  claimBlock in future -> bids locked until claims open")
    return 0


if __name__ == "__main__":
    sys.exit(main())
