#!/usr/bin/env python3
"""Launchpad token census — chunked eth_getLogs + dexscreener ranking.

Usage:
  python3 scan_launchpad.py <launcher_addr> <deploy_block> "<event_sig>" <token_topic_idx> [--rpc URL] [--latest]
Example (SushiLaunchpad, RH 4663):
  python3 scan_launchpad.py 0x104F1Ab42674565EC3DF0BFEbCcC4186f72fA7ED 21957383 \
    "TokenLaunched(address,address,address,address,int24,string,string,uint16,uint256,uint64,uint16)" 2

Collects every launch event from deploy block to latest, decodes the token
address from the chosen topic, dedupes, then ranks with dexscreener batches.
"""

import json
import sys
import time
import urllib.request
import concurrent.futures

from Crypto.Hash import keccak

RPC = "https://rpc.mainnet.chain.robinhood.com"
DEX = "https://api.dexscreener.com/latest/dex/tokens/"


def keccak256(sig: str) -> str:
    k = keccak.new(digest_bits=256)
    k.update(sig.encode())
    return "0x" + k.hexdigest()


def rpc_call(method, params, rpc=RPC, retries=4):
    for i in range(retries):
        try:
            data = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
            req = urllib.request.Request(rpc, data=data, headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0",
            })
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if i == retries - 1:
                return {"error": str(e)}
            time.sleep(2)


def scan_tokens(launcher, deploy_block, topic0, token_topic_idx, rpc=RPC):
    latest = int(rpc_call("eth_blockNumber", [], rpc=rpc)["result"], 16)
    print(f"latest block: {latest}")

    tokens = {}
    cur = deploy_block
    chunk = 1_000_000
    while cur < latest:
        end = min(cur + chunk, latest)
        for _ in range(3):
            res = rpc_call("eth_getLogs", [{
                "fromBlock": hex(cur), "toBlock": hex(end),
                "address": launcher, "topics": [topic0],
            }], rpc=rpc)
            if "error" in res:
                if "exceeds limit" in str(res.get("error", "")):
                    chunk = max(chunk // 2, 10_000)
                    print(f"  chunk too big, reducing to {chunk}")
                    continue
                print(f"  err at {cur}: {str(res.get('error'))[:80]}")
                break
            logs = res.get("result", [])
            for lg in logs:
                topics = lg.get("topics", [])
                if len(topics) > token_topic_idx:
                    tok = "0x" + topics[token_topic_idx][-40:].lower()
                    tokens[tok] = int(lg["blockNumber"], 16)
            break
        cur = end + 1
        time.sleep(0.2)

    print(f"unique tokens: {len(tokens)}")
    return tokens


def dex_batch(addrs):
    url = DEX + ",".join(addrs)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def rank_tokens(tokens, workers=10):
    addrs = list(tokens.keys())
    batches = [addrs[i:i + 30] for i in range(0, len(addrs), 30)]
    print(f"dexscreener batches: {len(batches)}")

    results = []

    def process(batch):
        out = []
        try:
            d = dex_batch(batch)
            by_token = {}
            for p in d.get("pairs") or []:
                bt = (p.get("baseToken") or {}).get("address", "").lower()
                liq = (p.get("liquidity") or {}).get("usd") or 0
                if bt not in by_token or liq > (by_token[bt].get("liquidity") or {}).get("usd", 0):
                    by_token[bt] = p
            for bt, best in by_token.items():
                out.append({
                    "token": bt,
                    "symbol": best.get("baseToken", {}).get("symbol", "?"),
                    "dex": best.get("dexId", "?"),
                    "mc": best.get("marketCap") or 0,
                    "fdv": best.get("fdv") or 0,
                    "liq": (best.get("liquidity") or {}).get("usd") or 0,
                    "vol": (best.get("volume") or {}).get("h24") or 0,
                    "price": best.get("priceUsd") or 0,
                })
        except Exception:
            pass
        return out

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        for i, res in enumerate(ex.map(process, batches)):
            results.extend(res)
            if (i + 1) % 50 == 0:
                print(f"  processed {i+1}/{len(batches)} batches | with pairs: {len(results)}")

    results.sort(key=lambda r: r["vol"], reverse=True)
    return results


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(__doc__)
        sys.exit(1)
    launcher = sys.argv[1]
    deploy_block = int(sys.argv[2])
    event_sig = sys.argv[3]
    token_idx = int(sys.argv[4])
    topic0 = keccak256(event_sig)
    print(f"topic0: {topic0}")

    tokens = scan_tokens(launcher, deploy_block, topic0, token_idx)
    results = rank_tokens(tokens)

    print("\n=== TOP 20 BY VOLUME 24H ===")
    for i, r in enumerate(results[:20]):
        print(f"  {i+1:2d}. {r['symbol']:16s} vol=${r['vol']:>14,.0f} | mc=${r['mc']:>12,.0f} | liq=${r['liq']:>10,.0f} | {r['token'][:12]}... | {r['dex']}")
