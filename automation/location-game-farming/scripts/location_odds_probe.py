#!/usr/bin/env python3
"""Per-period odds/rate poller for location games (and similar public-odds APIs).

WHY: on the worked target the public stats endpoint published the per-open win
probability *per hour*, and it moved by ~1,248x across 60 hours. The lever turned
out to be WHEN you spend the daily quota, not WHERE you play — so the useful
component is a cheap poller that logs one record per period and alerts only when a
NEW period crosses a threshold.

It is read-only: it never opens, claims, or signs anything.

    # single sample, print and exit
    python3 location_odds_probe.py --url https://host/v1/stats --once

    # watch, alert on any new period >= 5%, append one line per period
    python3 location_odds_probe.py --url https://host/v1/stats \
        --threshold 0.05 --interval 60 --hist odds_hourly.jsonl \
        --webhook-env GC_DISCORD_WEBHOOK

    # bootstrap history from a per-period endpoint (this target kept ~62 periods)
    python3 location_odds_probe.py --url https://host/v1/stats \
        --history-url 'https://host/v1/proofs/{hour}' --backfill 96 --once

NOTE: run this under systemd (`Restart=always`), not `screen` — screens were
observed dying silently with no traceback and notifications then stopped unnoticed.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def dig(obj, dotted: str):
    """Follow a dotted path; supports digits as list indices."""
    cur = obj
    for part in dotted.split("."):
        if cur is None:
            return None
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
                continue
            except (ValueError, IndexError):
                return None
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def get_json(url: str, timeout: int = 30, tries: int = 3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        except urllib.error.HTTPError as e:
            if e.code == 429:                      # back off, do not hammer
                time.sleep(8 + 6 * i)
                continue
            return None
        except Exception:
            time.sleep(2 + 2 * i)
    return None


def env_file_values(path: str = "~/.hermes/.env") -> dict:
    out = {}
    try:
        for line in open(os.path.expanduser(path)):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return out


def notify(webhook: str, text: str) -> None:
    if not webhook:
        print("[no webhook] " + text.replace("\n", " | ")[:160], flush=True)
        return
    body = json.dumps({"content": text[:1900], "username": "odds-probe"})
    subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-m", "25",
                    "-X", "POST", webhook, "-H", "Content-Type: application/json", "-d", body],
                   capture_output=True, text=True)


def sample(url: str, hour_path: str, odds_path: str, commit_path: str):
    st = get_json(url)
    if not isinstance(st, dict):
        return None
    odds = dig(st, odds_path)
    if not isinstance(odds, dict) or not odds:
        return None
    hour = dig(st, hour_path)
    try:
        total = sum(float(v) for v in odds.values())
    except (TypeError, ValueError):
        return None
    return {"period": hour, "odds": odds, "total": total,
            "commit": dig(st, commit_path), "at": time.time()}


def load_seen(hist: str) -> set:
    seen = set()
    try:
        for line in open(hist):
            try:
                seen.add(json.loads(line)["period"])
            except Exception:
                pass
    except FileNotFoundError:
        pass
    return seen


def record(hist: str, s: dict, seen: set) -> bool:
    if s["period"] in seen:
        return False
    with open(hist, "a") as f:
        f.write(json.dumps(s) + "\n")
    seen.add(s["period"])
    return True


def top_periods(hist: str, n: int = 5):
    rows = []
    try:
        for line in open(hist):
            try:
                r = json.loads(line)
                rows.append((r["period"], r["total"]))
            except Exception:
                pass
    except FileNotFoundError:
        return []
    rows.sort(key=lambda x: -x[1])
    return rows[:n]


def backfill(hist: str, history_url: str, stats_url: str, n: int,
             hour_path: str, odds_path: str) -> int:
    """Pull past periods from a per-period endpoint, oldest first."""
    cur = sample(stats_url, hour_path, odds_path, "commit.commit")
    if not cur or not isinstance(cur["period"], int):
        print("backfill: could not read a numeric current period", flush=True)
        return 0
    seen = load_seen(hist)
    hours = [cur["period"] - i for i in range(1, n + 1) if cur["period"] - i not in seen]

    def fetch(h):
        d = get_json(history_url.format(hour=h))
        if not isinstance(d, dict):
            return None
        odds = dig(d, odds_path)
        if not isinstance(odds, dict) or not odds:
            return None
        try:
            return {"period": h, "odds": odds, "total": sum(float(v) for v in odds.values()),
                    "commit": dig(d, "commit"), "at": None, "backfilled": True}
        except (TypeError, ValueError):
            return None

    got = 0
    # keep concurrency low — these endpoints rate-limit aggressively
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(fetch, hours):
            time.sleep(0.3)
            if r and record(hist, r, seen):
                got += 1
    totals = sorted(r["total"] for r in
                    [json.loads(l) for l in open(hist)] if r.get("total"))
    if totals:
        print(f"backfilled {got}; history n={len(totals)} "
              f"range {totals[0]*100:.4f}% .. {totals[-1]*100:.4f}%", flush=True)
    return got


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True, help="stats endpoint publishing current odds")
    ap.add_argument("--hour-path", default="commit.hour", help="dotted path to the period id")
    ap.add_argument("--odds-path", default="commit.odds.p", help="dotted path to the tier->probability map")
    ap.add_argument("--commit-path", default="commit.commit", help="dotted path to the commitment hash")
    ap.add_argument("--threshold", type=float, default=0.05, help="alert when a new period total >= this")
    ap.add_argument("--interval", type=int, default=60, help="seconds between polls")
    ap.add_argument("--hist", default="odds_hourly.jsonl", help="one JSON record per period")
    ap.add_argument("--webhook-env", default="GC_DISCORD_WEBHOOK",
                    help="env var (or ~/.hermes/.env key) holding a Discord webhook")
    ap.add_argument("--history-url", default=None,
                    help="per-period endpoint template, e.g. https://host/v1/proofs/{hour}")
    ap.add_argument("--backfill", type=int, default=0, help="how many past periods to fetch")
    ap.add_argument("--once", action="store_true", help="sample, print, exit")
    a = ap.parse_args()

    if a.once:
        if a.history_url and a.backfill:
            backfill(a.hist, a.history_url, a.url, a.backfill, a.hour_path, a.odds_path)
        s = sample(a.url, a.hour_path, a.odds_path, a.commit_path)
        if not s:
            print("sample failed", flush=True)
            return 1
        verdict = "GOOD PERIOD" if s["total"] >= a.threshold else "skip"
        print(f"period={s['period']}  total={s['total']*100:.4f}% (1 in {1/s['total']:.1f})  "
              f"-> {verdict}", flush=True)
        print("  tiers: " + "  ".join(f"{k}={float(v)*100:.4f}%" for k, v in s["odds"].items()),
              flush=True)
        return 0

    webhook = os.environ.get(a.webhook_env) or env_file_values().get(a.webhook_env, "")
    if a.history_url and a.backfill:
        backfill(a.hist, a.history_url, a.url, a.backfill, a.hour_path, a.odds_path)

    seen = load_seen(a.hist)
    print(f"--- odds probe: interval={a.interval}s threshold={a.threshold*100:.1f}% "
          f"history={len(seen)} periods webhook={'yes' if webhook else 'NO'} ---", flush=True)
    last, alerted, fails = None, None, 0

    while True:
        s = sample(a.url, a.hour_path, a.odds_path, a.commit_path)
        if not s:
            fails += 1
            if fails in (5, 20, 60):
                notify(webhook, f"⚠️ odds probe: {fails} consecutive failed samples")
            time.sleep(a.interval)
            continue
        if fails >= 5:
            notify(webhook, "✅ odds probe: sampling recovered")
        fails = 0

        newly = record(a.hist, s, seen)
        rolled = last is not None and s["period"] != last
        if rolled and s["total"] >= a.threshold and alerted != s["period"]:
            alerted = s["period"]
            top = top_periods(a.hist, 5)
            top_txt = "\n".join(f"  #{i+1} period {p} = {v*100:.2f}%" for i, (p, v) in enumerate(top))
            notify(webhook,
                   f"🔥 **GOOD PERIOD — odds >= {a.threshold*100:.0f}%**\n"
                   f"period `{s['period']}`\n"
                   f"total: **{s['total']*100:.2f}%**  (1 in {1/s['total']:.1f})\n"
                   + "\n".join(f"  {k}: {float(v)*100:.4f}%" for k, v in s["odds"].items())
                   + f"\n\ntop periods so far:\n{top_txt}\n\n"
                   + "→ spend the daily quota inside this period.")
        if newly:
            print(f"period {s['period']}  {s['total']*100:.4f}%"
                  + ("   <-- GOOD" if s["total"] >= a.threshold else ""), flush=True)
        last = s["period"]
        time.sleep(a.interval)


if __name__ == "__main__":
    sys.exit(main())
