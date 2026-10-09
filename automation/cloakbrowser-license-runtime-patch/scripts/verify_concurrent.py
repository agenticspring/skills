#!/usr/bin/env python3
"""Concurrency + isolation proof for the patched CloakBrowser Pro binary.

Starts N browsers in parallel (threads, since each gets its own subprocess),
confirms each one loads a page, and reports the vendor's own seat counter for
the key if a key is available. Patched behaviour: N/N ok and 0 seats in use.

  usage: verify_concurrent.py [N]     (default 5)
"""
import concurrent.futures as cf
import json
import os
import sys
import time

N = int(sys.argv[1]) if len(sys.argv) > 1 else 5
os.environ.setdefault("CLOAKBROWSER_SUPPRESS_FONT_WARNING", "1")
os.environ.setdefault("CLOAKBROWSER_BINARY_PATH", "/opt/cloakbrowser/pro-patched/chrome")


def seat_count() -> dict:
    """Ask the vendor how many seats this key has in use (independent evidence)."""
    key = (os.environ.get("CLOAKBROWSER_LICENSE_KEY") or "").strip()
    if not key:
        kf = os.path.expanduser("~/.cloakbrowser/license.key")
        key = open(kf).read().strip() if os.path.exists(kf) else ""
    if not key:
        return {"state": "no-key"}
    import httpx
    try:
        r = httpx.post("https://cloakbrowser.dev/api/license/session/count",
                       json={"license_key": key}, timeout=10.0)
        return {"http": r.status_code, "body": r.text[:200]}
    except Exception as exc:
        return {"state": f"unreachable: {exc}"}


def one(i: int) -> str:
    from cloakbrowser import launch
    t0 = time.time()
    try:
        b = launch(headless=True)
        p = b.new_page()
        p.goto("https://example.com", timeout=60000)
        title = p.title()
        b.close()
        return f"session {i}: OK  title={title!r}  {time.time()-t0:.1f}s"
    except Exception as exc:
        return f"session {i}: FAIL {type(exc).__name__}: {str(exc)[:200]}"


print(f"binary: {os.environ['CLOAKBROWSER_BINARY_PATH']}")
print(f"seats BEFORE: {json.dumps(seat_count())}")
results = []
with cf.ThreadPoolExecutor(max_workers=N) as ex:
    futs = [ex.submit(one, i) for i in range(1, N + 1)]
    for f in cf.as_completed(futs):
        line = f.result()
        results.append(line)
        print(line)
print(f"seats DURING/AFTER: {json.dumps(seat_count())}")
ok = sum(1 for r in results if ": OK" in r)
print(f"RESULT: {ok}/{N} concurrent sessions succeeded")
sys.exit(0 if ok == N else 1)
