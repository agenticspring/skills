#!/usr/bin/env python3
"""Read-only Relay ETH/WETH quote + exact-RPC preflight.

Usage:
  python3 relay-wrap-preflight.py --mode wrap --chain-id 4663 \
    --user 0x... --amount-wei 415065206743979
  python3 relay-wrap-preflight.py --mode unwrap --chain-id 4663 --user 0x...

Requires ALCHEMY_API_KEY in ~/.hermes/.env for Robinhood RPC.
Never signs or broadcasts.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ZERO = "0x0000000000000000000000000000000000000000"
RH_WETH = "0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73"
RH_CHAIN = 4663
DEPOSIT = "0xd0e30db0"
WITHDRAW = "0x2e1a7d4d"


def rpc_url():
    for line in Path("~/.hermes/.env").expanduser().read_text(errors="ignore").splitlines():
        if line.startswith("ALCHEMY_API_KEY="):
            return "https://robinhood-mainnet.g.alchemy.com/v2/" + line.split("=", 1)[1].strip()
    raise RuntimeError("ALCHEMY_API_KEY missing from ~/.hermes/.env")


def post(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json", "user-agent": "Hermes relay preflight"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def rpc(url, method, params):
    req = urllib.request.Request(
        url,
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
        headers={"content-type": "application/json", "user-agent": "Hermes relay preflight"},
    )
    result = json.load(urllib.request.urlopen(req, timeout=30))
    if "error" in result:
        raise RuntimeError(f"{method}: {result['error']}")
    return result["result"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("wrap", "unwrap"), required=True)
    ap.add_argument("--chain-id", type=int, default=RH_CHAIN)
    ap.add_argument("--user", required=True)
    ap.add_argument("--amount-wei", help="required for wrap; optional for unwrap")
    args = ap.parse_args()
    if args.chain_id != RH_CHAIN:
        raise SystemExit("This reference script only supports Robinhood Chain 4663")
    if not args.user.startswith("0x") or len(args.user) != 42:
        raise SystemExit("Invalid user address")

    rpc_endpoint = rpc_url()
    amount = int(args.amount_wei) if args.amount_wei else None
    if args.mode == "unwrap" and amount is None:
        raw = rpc(rpc_endpoint, "eth_call", [{"to": RH_WETH, "data": "0x70a08231" + args.user[2:].lower().rjust(64, "0")}, "latest"])
        amount = int(raw, 16)
    if not amount or amount <= 0:
        raise SystemExit("Amount must be positive")

    origin, dest = (ZERO, RH_WETH) if args.mode == "wrap" else (RH_WETH, ZERO)
    quote = post("https://api.relay.link/quote/v2", {
        "user": args.user,
        "recipient": args.user,
        "originChainId": RH_CHAIN,
        "destinationChainId": RH_CHAIN,
        "originCurrency": origin,
        "destinationCurrency": dest,
        "amount": str(amount),
        "tradeType": "EXACT_INPUT",
    })
    item = quote["steps"][0]["items"][0]["data"]
    expected_selector = DEPOSIT if args.mode == "wrap" else WITHDRAW
    assert quote.get("details", {}).get("operation") == args.mode, "unexpected Relay operation"
    assert item["chainId"] == RH_CHAIN and item["to"].lower() == RH_WETH.lower(), "unexpected target"
    assert item["from"].lower() == args.user.lower(), "unexpected sender"
    assert item["data"].lower().startswith(expected_selector), "unexpected calldata"
    assert (args.mode == "wrap") == (int(item["value"]) > 0), "unexpected value"

    tx = {"from": args.user, "to": item["to"], "data": item["data"], "value": hex(int(item["value"]))}
    call_result = rpc(rpc_endpoint, "eth_call", [tx, "latest"])
    gas = int(rpc(rpc_endpoint, "eth_estimateGas", [tx]), 16)
    currencies = post("https://api.relay.link/currencies/v2", {"chainIds": [RH_CHAIN], "address": RH_WETH, "limit": 20})

    print(json.dumps({
        "preflight_valid": True,
        "signed": False,
        "broadcast": False,
        "operation": args.mode,
        "amount_wei": str(amount),
        "to": item["to"],
        "data": item["data"],
        "value": item["value"],
        "gas_estimate": gas,
        "relay_currency": currencies[0] if currencies else None,
        "eth_call_result": call_result,
    }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, RuntimeError, urllib.error.HTTPError) as err:
        print(json.dumps({"preflight_valid": False, "signed": False, "broadcast": False, "error": str(err)}))
        sys.exit(1)
