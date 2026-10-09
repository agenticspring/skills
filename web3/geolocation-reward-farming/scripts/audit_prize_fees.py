#!/usr/bin/env python3
"""Audit WHO PAYS at each stage of a prize/reward payout — the money rail.

Answers the question operators actually ask ("do we need a gas float?") with on-chain
evidence instead of guesses: for each winner, count the transactions THEY paid for versus
the transactions the operation paid for, and report fee magnitudes.

Two reads per transaction settle it:
    fee payer           = transaction.message.accountKeys[0].pubkey
    winner's SOL delta  = postBalances[i] - preBalances[i]   at the winner's index

Usage
-----
    # winners discovered automatically from the platform's public stats endpoint
    ./audit_prize_fees.py --stats-url https://<host>/v1/stats --treasury <TREASURY_ADDR>

    # explicit addresses (repeatable), or a file with one address per line
    ./audit_prize_fees.py --address <ADDR> --address <ADDR2>
    ./audit_prize_fees.py --address-file winners.txt

RPC resolution order: --rpc  ->  $SOLANA_RPC  ->  ALCHEMY_API_KEY in ~/.hermes/.env
->  https://api.mainnet-beta.solana.com  (public, heavily rate-limited).

Reading the result
------------------
* winner_paid == 0 for the delivery transactions  -> the operation pays for delivery; the
  farming loop needs NO native gas. Any float is only for the winner-initiated cash-out.
* Winner-paid txs of ~1e-5..1e-4 SOL that move a stablecoin  -> that is the cash-out, and
  its cost is dust.
* One tx invoking the ATA program (`ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL`) paid by
  the operation  -> the operation is also paying the new asset's rent.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (compatible; prize-fee-audit/1.0)"
ATA_PROGRAM = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
ENVF = os.path.expanduser("~/.hermes/.env")


def env_line(key: str) -> str | None:
    try:
        for line in open(ENVF):
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return None


def resolve_rpc(explicit: str | None) -> str:
    if explicit:
        return explicit
    if os.environ.get("SOLANA_RPC"):
        return os.environ["SOLANA_RPC"]
    key = os.environ.get("ALCHEMY_API_KEY") or env_line("ALCHEMY_API_KEY")
    if key:
        return f"https://solana-mainnet.g.alchemy.com/v2/{key}"
    return "https://api.mainnet-beta.solana.com"


def rpc(url: str, method: str, params: list, tries: int = 3):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url, data=body,
                headers={"content-type": "application/json", "User-Agent": UA})
            return json.loads(urllib.request.urlopen(req, timeout=40).read()).get("result")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502) and i < tries - 1:
                time.sleep(2 * (i + 1))
                continue
            print(f"  ! rpc {method} http {e.code}", file=sys.stderr)
            return None
        except Exception as e:
            if i < tries - 1:
                time.sleep(2 * (i + 1))
                continue
            print(f"  ! rpc {method} {str(e)[:60]}", file=sys.stderr)
            return None
    return None


def winners_from_stats(url: str, limit: int) -> list[str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())
    out, seen = [], set()
    for row in (data.get("recent") or [])[:limit]:
        addr = row.get("profile") or row.get("address")
        if addr and addr not in seen:
            seen.add(addr)
            out.append(addr)
    return out


def classify(rpc_url: str, winner: str, treasury: str | None, lookback: int) -> dict:
    sigs = rpc(rpc_url, "getSignaturesForAddress", [winner, {"limit": lookback}]) or []
    stats = {"tx_seen": 0, "winner_paid": 0, "treasury_paid": 0, "other_paid": 0,
             "ata_by_operation": 0, "fees": [], "inline": None}
    for s in sigs:
        tx = rpc(rpc_url, "getTransaction",
                 [s["signature"], {"encoding": "jsonParsed",
                                   "maxSupportedTransactionVersion": 0}])
        if not tx:
            continue
        stats["tx_seen"] += 1
        meta = tx["meta"] or {}
        keys = [k.get("pubkey") for k in tx["transaction"]["message"]["accountKeys"]]
        payer = keys[0] if keys else None
        fee = (meta.get("fee") or 0) / 1e9
        progs = {ix.get("programId") for ix in tx["transaction"]["message"]["instructions"]}
        if payer == winner:
            stats["winner_paid"] += 1
            stats["fees"].append(fee)
        elif treasury and payer == treasury:
            stats["treasury_paid"] += 1
            if ATA_PROGRAM in progs:
                stats["ata_by_operation"] += 1
        else:
            stats["other_paid"] += 1
        # inline SOL delta for the winner, on the first tx they are party to
        if stats["inline"] is None and winner in keys:
            i = keys.index(winner)
            pre, post = meta.get("preBalances") or [], meta.get("postBalances") or []
            if len(pre) > i and len(post) > i:
                stats["inline"] = {"payer": payer, "fee_sol": fee,
                                   "winner_delta_sol": (post[i] - pre[i]) / 1e9,
                                   "ata_created": ATA_PROGRAM in progs}
        time.sleep(0.25)
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rpc", help="Solana JSON-RPC url (else $SOLANA_RPC / ALCHEMY_API_KEY)")
    ap.add_argument("--stats-url", help="public stats endpoint whose recent[] lists winners")
    ap.add_argument("--treasury", help="operator/treasury address, to attribute fee payers")
    ap.add_argument("--address", action="append", default=[], help="winner address (repeatable)")
    ap.add_argument("--address-file", help="file with one winner address per line")
    ap.add_argument("--limit", type=int, default=4, help="winners to take from --stats-url")
    ap.add_argument("--lookback", type=int, default=15, help="txs per winner to inspect")
    a = ap.parse_args()

    addrs = list(a.address)
    if a.address_file:
        addrs += [l.strip() for l in open(a.address_file) if l.strip()]
    if a.stats_url:
        addrs += winners_from_stats(a.stats_url, a.limit)
    addrs = list(dict.fromkeys(addrs))
    if not addrs:
        sys.exit("no winners: pass --stats-url, --address or --address-file")

    rpc_url = resolve_rpc(a.rpc)
    print(f"rpc      : {'alchemy' if 'alchemy' in rpc_url else rpc_url[:48]}")
    print(f"treasury : {a.treasury or '(not supplied — fee payers will read as other)'}")
    print(f"winners  : {len(addrs)}\n")

    for w in addrs:
        st = classify(rpc_url, w, a.treasury, a.lookback)
        print(f"--- {w[:20]}…  txs inspected={st['tx_seen']}")
        print(f"      paid by WINNER    : {st['winner_paid']}"
              + (f"   (fees {min(st['fees']):.6f}–{max(st['fees']):.6f} SOL)"
                 if st["fees"] else ""))
        print(f"      paid by TREASURY  : {st['treasury_paid']}"
              + (f"   (ATA rent funded by operator in {st['ata_by_operation']})"
                 if st["ata_by_operation"] else ""))
        print(f"      paid by other     : {st['other_paid']}")
        if st["inline"]:
            i = st["inline"]
            print(f"      latest sample     : feePayer={i['payer'][:14] if i['payer'] else '?'}…  "
                  f"fee={i['fee_sol']:.6f} SOL  winnerΔSOL={i['winner_delta_sol']:+.6f}"
                  + ("  [ATA created]" if i["ata_created"] else ""))
        print()

    print("Read it as: winner_paid==0 on delivery txs => the operation pays for delivery and\n"
          "the farming loop needs no native gas; only the winner-initiated cash-out costs us.")


if __name__ == "__main__":
    main()
