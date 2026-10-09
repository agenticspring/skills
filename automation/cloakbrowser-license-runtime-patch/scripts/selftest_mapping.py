#!/usr/bin/env python3
"""Self-test the VA->file-offset mapping used by patch_cloak.py.

For a sample of .text symbols in the cached binary, compare the bytes objdump
resolves at the symbol's VA with the bytes read at the computed file offset.
A clean run proves the mapping (and therefore where we will patch) is right.
"""
import random
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/opt/cloakbrowser")
from patch_cloak import load_segments, nm_symbols, va_to_offset  # noqa: E402

BIN = sys.argv[1] if len(sys.argv) > 1 else "/root/.cloakbrowser/chromium-146.0.7680.177.5/chrome"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 20
TEXT_VA = 0x2a93000  # .text start in the free v146 build; used only to pick candidates

syms = nm_symbols(BIN)
segs = load_segments(BIN)
data = Path(BIN).read_bytes()
cands = [(n, a) for n, a in syms.items() if a > TEXT_VA and a < TEXT_VA + 0xE000000]
sample = random.sample(cands, min(N, len(cands)))
print(f"symbols: {len(syms)} | text candidates: {len(cands)} | PT_LOAD segs: {len(segs)}")

ok = bad = 0
for name, va in sample:
    off = va_to_offset(segs, va)
    disk = data[off:off + 12]
    out = subprocess.run(
        ["objdump", "-d", "--start-address", hex(va), "--stop-address", hex(va + 12), BIN],
        capture_output=True, text=True,
    ).stdout
    got = b""
    for line in out.splitlines():
        m = re.match(r"\s*[0-9a-f]+:\s*((?:[0-9a-f]{2} )+)", line)
        if m:
            got += bytes(int(b, 16) for b in m.group(1).split())
    if got and got[:12] == disk[:12]:
        ok += 1
    elif got:
        bad += 1
        print(f"MISMATCH {name} VA={va:#x} off={off:#x}\n  disk={disk.hex(' ')}\n  objd={got[:12].hex(' ')}")
    else:
        bad += 1
        print(f"NO-DISASM {name} VA={va:#x} off={off:#x}")

print(f"mapping check: {ok} ok / {bad} bad")
sys.exit(1 if bad else 0)
