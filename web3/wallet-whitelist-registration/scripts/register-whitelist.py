#!/usr/bin/env python3
"""Batch-register Hermes wallet sets to an NFT whitelist endpoint.

Usage:
  python3 register-whitelist.py <api-url> [start-set] [end-set] [--out FILE] [--delay 0.2]

Endpoint contract: POST JSON {"wallet": "0x..."} -> {"success": true, "entry": {...}}
Adjust `post_wallet()` payload/headers for sites with a different shape.

Private keys are derived ephemerally in /dev/shm and never printed.
"""
import json, os, re, subprocess, sys, tempfile, time, urllib.request, urllib.error
from pathlib import Path

WALLET_FILE = Path("/root/.hermes/.credintial/.springwallet")


def derive_addresses(count: int) -> list[str]:
    sets = []
    for line in WALLET_FILE.read_text().splitlines():
        w = line.strip().split()
        if len(w) not in {12, 15, 18, 21, 24}:
            continue
        f = tempfile.NamedTemporaryFile("w", dir="/dev/shm", delete=False)
        f.write(" ".join(w) + "\n"); f.close(); os.chmod(f.name, 0o600)
        r = subprocess.run(["cast", "wallet", "private-key", "--mnemonic", f.name],
                           capture_output=True, text=True)
        os.unlink(f.name)
        if re.fullmatch(r"0x[0-9a-fA-F]{64}", r.stdout.strip()):
            sets.append(" ".join(w))
        if len(sets) >= count:
            break
    out = []
    for phrase in sets:
        f = tempfile.NamedTemporaryFile("w", dir="/dev/shm", delete=False)
        f.write(phrase + "\n"); f.close(); os.chmod(f.name, 0o600)
        r = subprocess.run(["cast", "wallet", "private-key", "--mnemonic", f.name],
                           capture_output=True, text=True)
        os.unlink(f.name)
        pk = r.stdout.strip()
        addr = subprocess.run(["cast", "wallet", "address", "--private-key", pk],
                              capture_output=True, text=True, check=True).stdout.strip()
        out.append(addr)
    return out


def post_wallet(api_url: str, addr: str, delay: float) -> dict:
    req = urllib.request.Request(
        api_url,
        data=json.dumps({"wallet": addr}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            d = json.loads(e.read().decode())
        except Exception:
            d = {"error": f"HTTP {e.code}"}
    except Exception as ex:
        d = {"error": str(ex)[:100]}
    time.sleep(delay)
    return d


def main():
    if len(sys.argv) < 2:
        print("usage: register-whitelist.py <api-url> [start-set] [end-set] [--out FILE] [--delay 0.2]")
        return 2
    api = sys.argv[1]
    start = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 1
    end = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 100
    out = "/tmp/whitelist-results.json"
    delay = 0.2
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    if "--delay" in sys.argv:
        delay = float(sys.argv[sys.argv.index("--delay") + 1])

    addrs = derive_addresses(end)
    if start > len(addrs):
        print(f"error: start {start} > available {len(addrs)}")
        return 2

    results = []
    for i in range(start, min(end, len(addrs)) + 1):
        addr = addrs[i - 1]
        d = post_wallet(api, addr, delay)
        ok = bool(d.get("success"))
        rid = d.get("entry", {}).get("id", "") if isinstance(d.get("entry"), dict) else ""
        results.append({"set": i, "addr": addr, "ok": ok, "id": rid, "error": d.get("error")})
        print(f"[{i}/{end}] Set{i} {'OK ' + rid if ok else 'FAIL ' + str(d.get('error'))[:60]}", flush=True)

    Path(out).write_text(json.dumps(results, indent=2))
    okn = sum(1 for r in results if r["ok"])
    print(f"DONE ok={okn} fail={len(results)-okn} -> {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
