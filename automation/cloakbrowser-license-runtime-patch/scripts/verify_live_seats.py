#!/usr/bin/env python3
"""Live seat proof: hold N browsers open (one thread each — Playwright's sync
API forbids nesting two contexts in one thread), then ask the vendor how many
seats this key has registered WHILE they are running.

  usage: verify_live_seats.py [N]        (default 8)

Keyless by default (proves the patched build needs no key). Set
CLOAKBROWSER_KEEP_KEY=1 to keep the key so the UNPATCHED build can register its
seats — that is the control run. The seat counter is queried over plain HTTP by
this script; the browser never sees the key when it is unset.
"""
import concurrent.futures as cf
import json
import os
import sys
import time

N = int(sys.argv[1]) if len(sys.argv) > 1 else 8
if os.environ.get("CLOAKBROWSER_KEEP_KEY") != "1":
    os.environ.pop("CLOAKBROWSER_LICENSE_KEY", None)
os.environ.setdefault("CLOAKBROWSER_BINARY_PATH", "/opt/cloakbrowser/pro-patched/chrome")
os.environ.setdefault("CLOAKBROWSER_SUPPRESS_FONT_WARNING", "1")

BINARY = os.environ["CLOAKBROWSER_BINARY_PATH"]
alive: list = []


def seat_count() -> str:
    import httpx
    kf = os.path.expanduser("~/.cloakbrowser/license.key")
    key = open(kf).read().strip() if os.path.exists(kf) else ""
    if not key:
        return "no-key"
    try:
        r = httpx.post("https://cloakbrowser.dev/api/license/session/count",
                       json={"license_key": key}, timeout=10.0)
        return r.text.strip()
    except Exception as exc:
        return f"unreachable: {exc}"


def open_one(i: int) -> str:
    from cloakbrowser import launch  # imported per-thread on purpose
    try:
        b = launch(headless=True)
        p = b.new_page()
        p.goto("https://example.com", timeout=60000)
        title = p.title()
        alive.append(b)
        return f"session {i}: OPEN  ({title!r})"
    except Exception as exc:
        return f"session {i}: FAIL {type(exc).__name__}: {str(exc)[:150]}"


print(f"binary      : {BINARY}")
print(f"key in env  : {'CLOAKBROWSER_LICENSE_KEY' in os.environ}")
with cf.ThreadPoolExecutor(max_workers=N) as ex:
    lines = [f.result() for f in cf.as_completed([ex.submit(open_one, i) for i in range(1, N + 1)])]
for line in sorted(lines):
    print("  " + line)

ok = sum(1 for line in lines if ": OPEN" in line)
print(f"\nLIVE sessions open: {ok}/{N}")
print(f"vendor seat counter WHILE {ok} live : {seat_count()}")
time.sleep(3)
print(f"vendor seat counter (+3s)          : {seat_count()}")
for b in alive:
    try:
        b.close()
    except Exception:
        pass
print("all browsers closed")
sys.exit(0 if ok == N else 1)
