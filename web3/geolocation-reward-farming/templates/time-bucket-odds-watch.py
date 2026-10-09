#!/usr/bin/env python3
"""Time-bucket odds watcher — copy and adapt.

Pattern: a reward platform publishes the CURRENT time bucket's win probability in
plaintext (often several tiers whose sum is the real per-action probability), and a
companion endpoint serves past buckets. Those probabilities can swing 100-1000x
between buckets, so the entire edge is *when* you spend your daily quota, not where.

This watcher does three things and nothing else:
  1. polls the bucket endpoint on an interval,
  2. writes ONE record per bucket to a JSONL history file (self-seeding, dedup by bucket),
  3. fires a webhook alert when a NEW bucket crosses a threshold.

It is read-only: it never acts, never spends, never touches a wallet.

ADAPT: BASE, ODDS_PATH (the dotted path to the dict of tier->probability), and the
response shape in `sample()`. Keep the history file so `top_buckets()` can give the
alert context ("this is the 3rd best bucket of the last 60").

Run:
    python3 time-bucket-odds-watch.py --once          # single sample, print and exit
    python3 time-bucket-odds-watch.py                 # daemon loop
    screen -dmS oddswatch python3 time-bucket-odds-watch.py

Env:
    ODDS_THRESHOLD   default 0.05   (alert when a new bucket's total >= this)
    ODDS_INTERVAL    default 60     (seconds between samples)
    ODDS_WEBHOOK     Discord webhook URL, or unset for log-only
    ODDS_ENV_FILE    default ~/.hermes/.env  (fallback source for ODDS_WEBHOOK;
                     never hardcode a secret in this file)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

# ------------------------------------------------------------------ ADAPT THESE
BASE = "https://example.com"
ODDS_PATH = "commit.odds.p"          # dotted path to a dict {tier: probability}
BUCKET_PATH = "commit.hour"          # dotted path to the bucket identifier
HIST = "odds_hourly.jsonl"
LOG = "odds_watch.log"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
# ------------------------------------------------------------------------------

THRESHOLD = float(os.environ.get("ODDS_THRESHOLD", "0.05"))
INTERVAL = int(os.environ.get("ODDS_INTERVAL", "60"))
ENVF = os.path.expanduser(os.environ.get("ODDS_ENV_FILE", "~/.hermes/.env"))


def log(msg: str) -> None:
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def env_values() -> dict:
    """Read a shared secrets file. Nothing is hardcoded in this script."""
    out: dict = {}
    try:
        for line in open(ENVF):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return out


WEBHOOK = os.environ.get("ODDS_WEBHOOK") or env_values().get("ODDS_WEBHOOK", "")


def alert(text: str) -> bool:
    if not WEBHOOK:
        log("no ODDS_WEBHOOK — alert dropped: " + text.replace("\n", " | ")[:120])
        return False
    if not WEBHOOK.startswith("https://"):
        log("ODDS_WEBHOOK does not look like an https url — refusing to send")
        return False
    body = json.dumps({"content": text[:1900], "username": "odds-watch"})
    r = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-m", "25", "-X", "POST",
         WEBHOOK, "-H", "Content-Type: application/json", "-d", body],
        capture_output=True, text=True)
    ok = r.stdout.strip() in ("200", "204")
    log(("alert sent" if ok else f"alert FAILED http={r.stdout.strip()[:20]} ") +
        " :: " + text.replace("\n", " | ")[:120])
    return ok


def dig(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def get(path: str, tries: int = 3):
    """Bounded GET with backoff. History sweeps in particular must stay slow:
    a burst of a few hundred requests will 429 the IP and silently truncate results."""
    for i in range(tries):
        try:
            req = urllib.request.Request(
                BASE + path, headers={"User-Agent": UA, "Accept": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(8 + 6 * i)
                continue
            log(f"http {e.code} on {path}")
            return None
        except Exception as e:
            log(f"transport {str(e)[:60]} on {path}")
            time.sleep(3 + 3 * i)
    return None


def sample():
    """One observation. Returns dict or None. ADAPT the response shape here."""
    st = get("/v1/stats")
    if not st:
        return None
    odds = dig(st, ODDS_PATH)
    bucket = dig(st, BUCKET_PATH)
    if not isinstance(odds, dict) or bucket is None:
        return None
    return {"bucket": bucket, "odds": odds, "total": sum(odds.values()), "at": time.time()}


def fmt(s) -> str:
    return (f"{(s['total'] or 0) * 100:.4f}% (1 in "
            f"{(1 / s['total']) if s['total'] else float('inf'):.1f})  "
            + " ".join(f"{t}={v * 100:.4f}%" for t, v in s["odds"].items()))


def load_seen() -> set:
    out = set()
    try:
        for line in open(HIST):
            try:
                out.add(json.loads(line)["bucket"])
            except Exception:
                pass
    except FileNotFoundError:
        pass
    return out


def top_buckets(n: int = 5):
    rows = []
    try:
        for line in open(HIST):
            try:
                r = json.loads(line)
                rows.append((r["bucket"], r["total"]))
            except Exception:
                pass
    except FileNotFoundError:
        return []
    rows.sort(key=lambda x: -x[1])
    return rows[:n]


def main() -> None:
    if "--once" in sys.argv:
        s = sample()
        if not s:
            sys.exit("sample failed")
        print(f"bucket={s['bucket']}  {fmt(s)}")
        print(f"  threshold={THRESHOLD * 100:.1f}%  -> "
              f"{'HOT — spend quota now' if s['total'] >= THRESHOLD else 'cold — wait'}")
        return

    log(f"--- start interval={INTERVAL}s threshold={THRESHOLD * 100:.1f}% "
        f"webhook={'yes' if WEBHOOK else 'NO'} ---")
    seen = load_seen()
    log(f"history: {len(seen)} buckets already recorded")

    last_bucket, alerted, fails = None, None, 0
    while True:
        s = sample()
        if not s:
            fails += 1
            if fails in (5, 20, 60):
                alert(f"odds watchdog: {fails} consecutive failed samples — check the "
                      f"endpoint and connectivity.")
            time.sleep(INTERVAL)
            continue
        if fails >= 5:
            alert("odds watchdog: sampling recovered.")
        fails = 0

        if s["bucket"] not in seen:
            seen.add(s["bucket"])
            with open(HIST, "a") as f:
                f.write(json.dumps(s) + "\n")
            log(f"bucket {s['bucket']}  {fmt(s)}"
                + ("   <-- HOT" if s["total"] >= THRESHOLD else ""))

        rolled = last_bucket is not None and s["bucket"] != last_bucket
        if rolled and s["total"] >= THRESHOLD and alerted != s["bucket"]:
            alerted = s["bucket"]
            top = "\n".join(f"  #{i + 1} bucket {b} = {v * 100:.2f}%"
                            for i, (b, v) in enumerate(top_buckets(5)))
            alert(f"**HOT BUCKET** — odds >= {THRESHOLD * 100:.0f}%\n"
                  f"bucket `{s['bucket']}`\n"
                  f"total: **{s['total'] * 100:.2f}%** (1 in {1 / s['total']:.1f})\n"
                  + "\n".join(f"  {t}: {v * 100:.4f}%" for t, v in s["odds"].items())
                  + f"\n\nbest buckets so far:\n{top}\n\n"
                  f"-> spend the daily quota in this bucket.")

        last_bucket = s["bucket"]
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
