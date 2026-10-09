#!/usr/bin/env python3
"""
Proxy pool pre-flight probe for batch automation runs.

WHY THIS EXISTS
---------------
Two failure modes cost real runs and are both caught here:

1. Declaring a live pool dead. Premium pools cap *concurrent* sessions per
   account. Sweeping a 100-proxy list at 20 workers reported 4 alive; the same
   list at 2 workers with ~0.8s spacing reported 21. High concurrency looks
   exactly like a dead pool. -> LOW_CONCURRENCY default.

2. Starting a run on a dead pool. Providers rotate credentials while keeping
   the same IPs, so a pool can expire between runs: every IP still resolves but
   every request returns ProxyError/ERR_TUNNEL. A batch then burns itself at
   ~1s per account. -> run this BEFORE account #1 and abort if zero are alive.

USAGE
-----
    python3 proxy-preflight.py proxy.txt
    python3 proxy-preflight.py proxy.txt --url https://target.example/
    python3 proxy-preflight.py proxy.txt --workers 2 --delay 0.8 --alive-out alive.txt

Accept both common proxy.txt line formats:
    host:port:user:pass        (most common in pasted lists)
    http://user:pass@host:port
    http://host:port

EXIT CODES
    0 = at least one proxy alive
    1 = zero alive  -> caller should ABORT the run, never start on a dead pool
    2 = bad input
"""
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    sys.exit("needs: pip install requests")

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/131.0.0.0 Safari/537.36")

# A non-browser GET legitimately returns 400/307 on many targets -- accept them
# as proof the proxy TUNNELS, which is all we are testing here.
ALIVE_STATUS = {200, 301, 302, 307, 400}


def normalise(line: str) -> str:
    """host:port:user:pass -> http://user:pass@host:port ; else assume URL."""
    line = line.strip()
    if not line or line.startswith("#"):
        return ""
    if "://" in line:
        return line
    p = line.split(":")
    if len(p) == 4:
        return f"http://{p[2]}:{p[3]}@{p[0]}:{p[1]}"
    if len(p) == 2:
        return f"http://{line}"
    return line


def probe(proxy: str, url: str, timeout: float):
    """Return (proxy, ok, detail). Detail carries the exit country when known."""
    px = {"http": proxy, "https": proxy}
    try:
        r = requests.get(url, proxies=px, headers={"User-Agent": UA}, timeout=timeout)
        country = ""
        try:
            country = r.json().get("country", "")
        except Exception:
            pass
        return proxy, r.status_code in ALIVE_STATUS, f"HTTP {r.status_code} {country}".strip()
    except Exception as e:
        return proxy, False, type(e).__name__


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("proxy_file")
    ap.add_argument("--url", default="https://ipinfo.io/json",
                    help="probe target; an ipinfo-style JSON gives you the exit country")
    ap.add_argument("--workers", type=int, default=2,
                    help="keep this LOW (2-3). High concurrency marks live proxies dead.")
    ap.add_argument("--delay", type=float, default=0.8,
                    help="seconds between submissions, to respect provider session caps")
    ap.add_argument("--timeout", type=float, default=22)
    ap.add_argument("--alive-out", default="",
                    help="write the alive proxies (original line format) here")
    args = ap.parse_args()

    try:
        raw = [l for l in open(args.proxy_file, encoding="utf-8").read().splitlines()]
    except OSError as e:
        print(f"cannot read {args.proxy_file}: {e}")
        sys.exit(2)

    pairs = [(l.strip(), normalise(l)) for l in raw]
    pairs = [(orig, url) for orig, url in pairs if url]
    if not pairs:
        sys.exit(2)

    print(f"probing {len(pairs)} proxies -> {args.url}")
    print(f"  workers={args.workers}  delay={args.delay}s   "
          f"(LOW concurrency on purpose -- see header)")
    print("-" * 62)

    alive, results = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = []
        for orig, url in pairs:
            futs.append(ex.submit(probe, url, args.url, args.timeout))
            time.sleep(args.delay)
        for f in as_completed(futs):
            proxy, ok, detail = f.result()
            results.append((proxy, ok, detail))
            print(f"  {'OK  ' if ok else 'DEAD'} {proxy[:64]:64} {detail}")

    alive = [p for p, ok, _ in results if ok]
    print("-" * 62)
    print(f"  ALIVE {len(alive)}/{len(pairs)}")

    if args.alive_out and alive:
        keep = [(orig, url) for orig, url in pairs if url in alive]
        with open(args.alive_out, "w", encoding="utf-8") as fh:
            for orig, _ in keep:
                fh.write(orig + "\n")
        print(f"  wrote {len(keep)} alive lines -> {args.alive_out}")

    if not alive:
        print("  ZERO ALIVE -> ABORT the run. Ask for fresh proxy lines "
              "(providers rotate user/pass without changing IPs).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
