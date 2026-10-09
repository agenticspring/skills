#!/usr/bin/env python3
"""Watch an OpenSea drop and signal when a target stage goes live.

Usage:
  python3 watch-drop-stage.py <slug> [--target public_sale] [--interval 10] [--timeout 1800]

Reads OPENSEA_API_KEY from /root/NFT-OPENSEA/opensea.env or environment.

Exit codes:
  0  target stage active and minting (supply < max)
  1  sold out (supply >= max or is_minting false)
  2  API/JSON error on every poll (give up)
  3  timeout waiting for target stage

Prints one JSON line per poll with timestamp, active stage, supply, max,
is_minting, and whether the target stage is live. Intended to be run in the
background from the `terminal` tool while OSNM-Z is preflighted, then the
mint is fired immediately when this exits 0.
"""
import argparse, json, os, sys, time, urllib.request
from pathlib import Path

ENV_PATH = Path("/root/NFT-OPENSEA/opensea.env")
BASE = "https://api.opensea.io/api/v2/drops/{slug}"


def load_key():
    if os.environ.get("OPENSEA_API_KEY"):
        return os.environ["OPENSEA_API_KEY"]
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(errors="ignore").splitlines():
            if line.startswith("OPENSEA_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


def fetch(slug, key):
    req = urllib.request.Request(
        BASE.format(slug=slug), headers={"x-api-key": key, "User-Agent": "hermes-stage-watch"}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--target", default="public_sale")
    ap.add_argument("--interval", type=int, default=10)
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    key = load_key()
    if not key:
        print(json.dumps({"error": "OPENSEA_API_KEY missing"}))
        return 2

    deadline = time.time() + args.timeout
    last_state = None
    while time.time() < deadline:
        try:
            d = fetch(args.slug, key)
        except Exception as e:
            print(json.dumps({"error": str(e)[:200]}), flush=True)
            time.sleep(args.interval)
            continue

        active = d.get("active_stage") or {}
        stages = d.get("stages") or []
        supply = d.get("total_supply")
        max_supply = d.get("max_supply")
        is_minting = d.get("is_minting")
        try:
            supply_i = int(supply) if supply is not None else None
            max_i = int(max_supply) if max_supply is not None else None
        except (TypeError, ValueError):
            supply_i = max_i = None

        state = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "active_stage": (active.get("stage_type"), active.get("label")),
            "active_price": active.get("price"),
            "active_end": active.get("end_time"),
            "supply": supply,
            "max": max_supply,
            "is_minting": is_minting,
            "target_live": active.get("stage_type") == args.target,
        }
        if state != last_state:
            print(json.dumps(state), flush=True)
            last_state = state

        # Sold out / mint closed
        if max_i is not None and supply_i is not None and supply_i >= max_i:
            print(json.dumps({"result": "sold_out", **state}), flush=True)
            return 1
        if is_minting is False:
            print(json.dumps({"result": "mint_closed", **state}), flush=True)
            return 1

        # Target stage live -> ready
        if active.get("stage_type") == args.target:
            print(json.dumps({"result": "target_live", **state}), flush=True)
            return 0

        time.sleep(args.interval)

    print(json.dumps({"result": "timeout", **state}), flush=True)
    return 3


if __name__ == "__main__":
    sys.exit(main())
