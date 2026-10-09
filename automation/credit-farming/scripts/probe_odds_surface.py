#!/usr/bin/env python3
"""Dump a farm target's reward-probability surface and measure its time variance.

Answers, with measurements instead of guesses:
  * what IS the current win probability, and does it reconcile with a second source?
  * how much does it vary over time (is a fixed schedule losing money?)
  * does geography move it at all (control test), or only availability?

Read-only: sends only GET requests to documented public endpoints. It never
authenticates, never touches a wallet, never performs a reward-bearing action.

Typical use (defaults match the GoCollect-class layout):

    python3 probe_odds_surface.py --base https://gocollect.fun \
        --cross-path /v1/store --cross-key chances.free \
        --region 39.04,-77.49 --region -6.20,106.80 --region 64.14,-21.94

Adapt the paths with --stats / --odds-key / --hour-key / --proofs / --preview for
other targets. Harvest gently: the default 1.1 s spacing and 429 backoff exist
because a 12-worker burst silently truncated a 500-window sample to 62 rows.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as stx
import sys
import time
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def dig(obj, dotted: str):
    """Fetch a nested key: dig(j, 'commit.odds.p'). Returns None if absent."""
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


class Fetcher:
    def __init__(self, proxy_file: str | None = None, timeout: int = 30):
        self.proxies: list[str] = []
        self._i = 0
        if proxy_file and os.path.exists(proxy_file):
            for line in open(proxy_file):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # accept host:port:user:pass (fleet form) or a full URL
                if line.startswith("http"):
                    self.proxies.append(line)
                else:
                    bits = line.split(":")
                    if len(bits) == 4:
                        h, p, u, w = bits
                        self.proxies.append(f"http://{u}:{w}@{h}:{p}")
        self.timeout = timeout

    def _opener(self):
        if not self.proxies:
            return urllib.request.build_opener()
        url = self.proxies[self._i % len(self.proxies)]
        self._i += 1
        return urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": url, "https": url}))

    def get(self, url: str, tries: int = 4):
        for attempt in range(tries):
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": "application/json"})
            try:
                return json.loads(self._opener().open(req, timeout=self.timeout).read())
            except urllib.error.HTTPError as e:
                if e.code == 429:                      # back off, do not truncate the sample
                    time.sleep(8 + 6 * attempt)
                    continue
                print(f"  ! http {e.code} on {url}", file=sys.stderr)
                return None
            except Exception as e:
                print(f"  ! transport {str(e)[:60]} on {url}", file=sys.stderr)
                time.sleep(2 + 2 * attempt)
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="e.g. https://target.com")
    ap.add_argument("--stats", default="/v1/stats")
    ap.add_argument("--odds-key", default="commit.odds.p",
                    help="dotted path to the per-tier odds object inside --stats")
    ap.add_argument("--hour-key", default="commit.hour")
    ap.add_argument("--proofs", default="/v1/proofs/{hour}",
                    help="per-window history endpoint; {hour} is substituted")
    ap.add_argument("--proofs-odds-key", default="odds.p",
                    help="dotted path to the odds object inside a proofs row")
    ap.add_argument("--cross-path", default=None,
                    help="second endpoint to reconcile the odds against, e.g. /v1/store")
    ap.add_argument("--cross-key", default=None,
                    help="dotted path in --cross-path, e.g. chances.free")
    ap.add_argument("--preview", default="/v1/crates/preview?lat={lat}&lng={lng}",
                    help="geometry endpoint for the geography control test")
    ap.add_argument("--region", action="append", default=[],
                    metavar="LAT,LNG", help="repeatable; control test locations")
    ap.add_argument("--history", type=int, default=60, help="windows to harvest")
    ap.add_argument("--delay", type=float, default=1.1, help="seconds between requests")
    ap.add_argument("--proxy-file", default=None, help="optional host:port:user:pass list")
    ap.add_argument("--out", default="odds_surface.json", help="where to save the harvest")
    args = ap.parse_args()

    f = Fetcher(args.proxy_file)
    base = args.base.rstrip("/")

    # ---- 1. current surface + cross-check -------------------------------------
    stats = f.get(base + args.stats)
    if not stats:
        sys.exit("could not read the stats endpoint")
    tiers = dig(stats, args.odds_key)
    hour = dig(stats, args.hour_key)
    if not isinstance(tiers, dict) or not tiers:
        sys.exit(f"no odds object at '{args.odds_key}' — inspect the payload manually")
    total = sum(float(v) for v in tiers.values())

    print(f"=== current window: hour {hour} ===")
    for k, v in sorted(tiers.items(), key=lambda kv: -float(kv[1])):
        print(f"  {k:<12} {float(v)*100:.5f}%")
    print(f"  {'TOTAL':<12} {total*100:.5f}%  = 1 in "
          f"{(1/total):.1f}" if total else "  TOTAL 0 — guard your divisions")

    if args.cross_path and args.cross_key:
        cross = f.get(base + args.cross_path)
        other = dig(cross, args.cross_key) if cross else None
        if isinstance(other, (int, float)):
            ok = abs(float(other) - total) < 1e-12
            print(f"  reconcile vs {args.cross_path}:{args.cross_key} = {other!r}  "
                  f"{'MATCH (this is the real probability)' if ok else 'MISMATCH — wrong field?'}")
        else:
            print(f"  could not read {args.cross_path}:{args.cross_key}")

    if isinstance(stats.get("wins"), int) and isinstance(stats.get("opens"), int) and stats["opens"]:
        print(f"  lifetime cross-check: wins/opens = {stats['wins']}/{stats['opens']} "
              f"= {100*stats['wins']/stats['opens']:.3f}%")

    # ---- 2. harvest history, deduped, politely --------------------------------
    print(f"\n=== harvesting up to {args.history} windows (delay {args.delay}s) ===")
    rows: dict[int, float] = {}
    misses = 0
    for i in range(1, args.history + 1):
        h = (hour - i) if isinstance(hour, int) else None
        if h is None:
            break
        row = f.get(base + args.proofs.format(hour=h))
        odds = dig(row, args.proofs_odds_key) if row else None
        if isinstance(odds, dict) and odds:
            rows[h] = sum(float(v) for v in odds.values())
        else:
            misses += 1
        time.sleep(args.delay)

    print(f"  collected {len(rows)} windows ({misses} unavailable/throttled)")
    if len(rows) < 10:
        print("  !! sample too small to conclude anything — increase --history, "
              "increase --delay, or rotate proxies. Do NOT design a strategy on this.")

    vals = [v for v in rows.values() if v > 0]
    zeros = sum(1 for v in rows.values() if v <= 0)
    if not vals:
        sys.exit("no usable history")
    if zeros:
        print(f"  note: {zeros} window(s) reported exactly zero odds — guard divisions")

    lo, hi, med, mean = min(vals), max(vals), stx.median(vals), stx.mean(vals)
    print(f"\n=== variance over {len(vals)} windows ===")
    print(f"  worst  {lo*100:.4f}%  (1 in {1/lo:,.0f})")
    print(f"  median {med*100:.4f}% (1 in {1/med:,.1f})")
    print(f"  best   {hi*100:.4f}%  (1 in {1/hi:,.1f})")
    print(f"  mean   {mean*100:.4f}%   stdev {stx.stdev(vals)*100:.4f}%")
    print(f"  spread max/min = {hi/lo:,.1f}x")
    if len(vals) >= 10:
        top = sorted(vals)[-max(1, len(vals) // 10):]
        print(f"  top-decile mean {stx.mean(top)*100:.4f}% vs mean {mean*100:.4f}%"
              f"  ->  {stx.mean(top)/mean:.2f}x by choosing the window")
    for thr in (0.03, 0.05, 0.10, 0.15):
        n = sum(1 for v in vals if v >= thr)
        print(f"  windows >= {thr*100:>4.0f}%: {n:>3}/{len(vals)} ({100*n/len(vals):5.1f}%)")

    # ---- 3. geography control test -------------------------------------------
    if args.region:
        print("\n=== geography control test (same endpoint, different locations) ===")
        seen_round, seen_exp = {}, {}
        for spec in args.region:
            try:
                la, ln = (float(x) for x in spec.split(","))
            except ValueError:
                print(f"  bad --region {spec!r} (want LAT,LNG)")
                continue
            g = f.get(base + args.preview.format(lat=la, lng=ln))
            crates = (g or {}).get("crates") or []
            ids = [c.get("id", "") for c in crates]
            rounds = {i.split(":")[1] for i in ids if ":" in i}
            exps = {c.get("expiresAt") for c in crates}
            seen_round[spec] = rounds
            seen_exp[spec] = exps
            has_odds = any(k for c in crates for k in c if k not in
                           ("id", "lat", "lng", "expiresAt"))
            print(f"  {spec:<18} crates={len(crates):>3}  round={sorted(rounds)}  "
                  f"odds_field_in_payload={has_odds}")
            time.sleep(args.delay)
        allr = set().union(*seen_round.values()) if seen_round else set()
        alle = set().union(*seen_exp.values()) if seen_exp else set()
        if len(allr) <= 1 and len(alle) <= 1 and len(seen_round) > 1:
            print("  => identical round id + expiry across locations: ONE global grid.")
            print("     Region cannot change the odds. It can only change competition")
            print("     (whether the crate you want is still there). Say exactly that.")
        else:
            print("  => rounds/expiry differ per location: geography MAY be a real axis.")
            print("     Investigate before dismissing it.")

    json.dump({"hour": hour, "tiers": tiers, "total": total,
               "history": {str(k): v for k, v in sorted(rows.items())}},
              open(args.out, "w"), indent=1)
    print(f"\nsaved -> {args.out}")


if __name__ == "__main__":
    main()
