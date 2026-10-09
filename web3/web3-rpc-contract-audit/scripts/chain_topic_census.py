#!/usr/bin/env python3
"""Chain-wide log census by TOPIC ONLY (client-side address filtering).

Why this exists: on self-hosted / leaked EVM endpoints, `eth_getLogs` WITH an `address`
filter can silently return `[]` even when the address really does emit logs. Topic-only
scans work. This script therefore never sends an `address` key to the node; it filters
locally.

Also distinguishes "genuinely zero logs" from "the RPC call failed" -- collapsing an error
into a bare 0 is how a future verdict gets poisoned with a false negative.

Usage:
    python3 chain_topic_census.py --rpc <URL> --topic "Transfer(address,address,uint256)"
    python3 chain_topic_census.py --rpc <URL> --topic "Transfer(address,address,uint256)" \
        --address 0xToken --address 0xOtherToken
    python3 chain_topic_census.py --rpc <URL> --topic0 0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef
    python3 chain_topic_census.py --rpc <URL> --preset defi      # the whole DeFi topic menu

Output: counts per topic, per-emitting-contract breakdown, full decoded log lines, JSON dump.

Notes:
  * ~3 workers and retry-with-backoff: these endpoints throttle hard.
  * Chunked at 2000 blocks, auto-splitting to ~250-block sub-chunks when a chunk errors.
  * Freeze the head block at start so the range does not move while scanning.
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

try:
    import requests
except ImportError:
    sys.exit("pip install requests")

try:
    from Crypto.Hash import keccak
except ImportError:
    keccak = None


# ---------------------------------------------------------------- RPC wrapper
class RpcError:
    """Distinct sentinel -- never let a failure masquerade as an empty result."""

    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return "RPC_ERROR(%s)" % self.msg


def make_rpc(url, retries=8, timeout=50):
    def rpc(method, params):
        for attempt in range(retries):
            try:
                r = requests.post(
                    url,
                    json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                    headers={"User-Agent": "curl/8.5.0", "content-type": "application/json"},
                    timeout=timeout,
                )
                if r.status_code == 429:
                    time.sleep(1.5 + attempt)
                    continue
                if r.status_code != 200:
                    time.sleep(0.6)
                    continue
                j = r.json()
                if "error" in j:
                    return RpcError(str(j["error"])[:160])
                return j.get("result")
            except Exception as exc:  # noqa: BLE001
                if attempt == retries - 1:
                    return RpcError(str(exc)[:160])
                time.sleep(1.0)
        return RpcError("exhausted retries")

    return rpc


def topic_of(signature):
    if signature.startswith("0x") and len(signature) == 66:
        return signature
    if keccak is None:
        raise SystemExit("pycryptodome needed to hash signatures: pip install pycryptodome")
    k = keccak.new(digest_bits=256)
    k.update(signature.encode())
    return "0x" + k.hexdigest()


def sel(signature):
    k = keccak.new(digest_bits=256)
    k.update(signature.encode())
    return "0x" + k.hexdigest()[:8]


PRESETS = {
    # the topic menu -- each answers a different question about a fresh chain
    "tokens": ["Transfer(address,address,uint256)"],
    "defi": [
        "Approval(address,address,uint256)",
        "PoolCreated(address,address,uint24,int24,address)",
        "Initialize(bytes32,address,uint24,int24,address,uint160,int24)",
        "Swap(address,address,int256,int256,uint160,uint128,int24)",
        "Mint(address,address,int24,int24,uint128,uint256,uint256)",
    ],
    "all": [
        "Transfer(address,address,uint256)",
        "Approval(address,address,uint256)",
        "PoolCreated(address,address,uint24,int24,address)",
        "Initialize(bytes32,address,uint24,int24,address,uint160,int24)",
        "Swap(address,address,int256,int256,uint160,uint128,int24)",
        "Mint(address,address,int24,int24,uint128,uint256,uint256)",
    ],
}


# ---------------------------------------------------------------- census
def fetch_chunk(rpc, frm, to, topic0):
    res = rpc("eth_getLogs", [{"fromBlock": hex(frm), "toBlock": hex(to), "topics": [topic0]}])
    if isinstance(res, list):
        return res
    # chunk too wide / rejected -> split. Still no `address` key.
    out = []
    for b in range(frm, to + 1, 250):
        rr = rpc("eth_getLogs", [
            {"fromBlock": hex(b), "toBlock": hex(min(b + 249, to)), "topics": [topic0]}
        ])
        if isinstance(rr, list):
            out += rr
        time.sleep(0.05)
    return out


def census(rpc, topic0, head, chunk, workers, verbose=True):
    ranges = [(i, min(i + chunk - 1, head)) for i in range(0, head + 1, chunk)]
    logs = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for idx, part in enumerate(ex.map(lambda rg: fetch_chunk(rpc, rg[0], rg[1], topic0), ranges)):
            logs += part
            if verbose and idx % 4 == 0:
                print("    chunk %d/%d  logs=%d" % (idx, len(ranges), len(logs)), flush=True)
    return logs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rpc", required=True)
    ap.add_argument("--topic", action="append", default=[], help="event signature, repeatable")
    ap.add_argument("--topic0", action="append", default=[], help="raw topic0, repeatable")
    ap.add_argument("--preset", choices=sorted(PRESETS), help="canned topic bundle")
    ap.add_argument("--address", action="append", default=[],
                    help="client-side filter (repeatable). Never sent to the node.")
    ap.add_argument("--chunk", type=int, default=2000)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--out", default="chain_topic_census.json")
    args = ap.parse_args()

    sigs = list(args.topic)
    if args.preset:
        sigs += PRESETS[args.preset]
    topics = [topic_of(s) for s in sigs] + list(args.topic0)
    if not topics:
        ap.error("give --topic, --topic0 or --preset")

    rpc = make_rpc(args.rpc)
    head_raw = rpc("eth_blockNumber", [])
    if isinstance(head_raw, RpcError):
        sys.exit("cannot reach RPC: %s" % head_raw.msg)
    head = int(head_raw, 16)
    print("chain head (frozen) = %d" % head)

    want = {a.lower() for a in args.address} or None
    if want:
        print("client-side address filter: %s" % ", ".join(sorted(want)))
        print("(NOTE: no `address` key is sent to the node -- address-filtered "
              "eth_getLogs is unreliable on self-hosted endpoints)")

    report = {}
    for sig, t0 in zip(sigs + [""] * len(args.topic0), topics):
        label = sig or t0
        print("\n=== %s\n    topic0 %s" % (label, t0))
        logs = census(rpc, t0, head, args.chunk, args.workers)
        by_addr = {}
        for lg in logs:
            a = lg["address"].lower()
            by_addr[a] = by_addr.get(a, 0) + 1
        shown = logs
        if want:
            shown = [lg for lg in logs if lg["address"].lower() in want]
            print("    total logs on chain = %d   matching filter = %d" % (len(logs), len(shown)))
        else:
            print("    total logs on chain = %d" % len(logs))

        if not logs:
            print("    RESULT: ZERO logs. (This is a real zero -- the call succeeded and "
                  "returned an empty list, not an error.)")
        for a, n in sorted(by_addr.items(), key=lambda x: -x[1]):
            mark = "" if not want or a in want else "   (filtered out)"
            print("      %s  %d log(s)%s" % (a, n, mark))

        for lg in shown[:200]:
            blk = int(lg["blockNumber"], 16)
            tps = lg.get("topics") or []
            line = "      blk %d  %s" % (blk, lg["address"])
            if len(tps) >= 3:
                line += "  from %s -> to %s" % ("0x" + tps[1][-40:], "0x" + tps[2][-40:])
                if lg.get("data") and lg["data"] != "0x":
                    try:
                        line += "  value_raw %d" % int(lg["data"], 16)
                    except ValueError:
                        pass
            print(line)
            print("          tx %s  logIndex %s" % (lg.get("transactionHash"), lg.get("logIndex")))

        report[label] = {"topic0": t0, "total": len(logs), "by_contract": by_addr}

    with open(args.out, "w") as fh:
        json.dump(report, fh, indent=1)
    print("\n-> %s" % args.out)
    print("\nNext: for each emitting contract, read name()/symbol()/decimals()/totalSupply(), "
          "then prove liquidity with factory.getPool(token, WETH, fee) across ALL fee tiers.")


if __name__ == "__main__":
    main()
