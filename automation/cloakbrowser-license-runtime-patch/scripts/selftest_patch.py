#!/usr/bin/env python3
"""End-to-end self-test of the patch path on a throwaway copy.

Proves, on a binary we can afford to break, that:
  1. the VA->offset mapping lands on a real function prologue,
  2. overwriting it writes exactly 3 bytes and nothing else,
  3. the on-disk verification catches the change.

Targets a symbol whose prologue really is `55 48 89`, so the same code path the
Pro binary will take is exercised. The copy is deleted afterwards.
"""
import hashlib
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/opt/cloakbrowser")
from patch_cloak import PROLOGUE, load_segments, nm_symbols, va_to_offset  # noqa: E402

SRC = "/root/.cloakbrowser/chromium-146.0.7680.177.5/chrome"
TMP = Path("/tmp/cloak-patch-selftest")

shutil.rmtree(TMP, ignore_errors=True)
TMP.mkdir(parents=True)
copy = TMP / "chrome"
print(f"copying {SRC} -> {copy} …")
shutil.copy2(SRC, copy)

syms = nm_symbols(SRC)
segs = load_segments(SRC)
data = Path(SRC).read_bytes()

# Find a real function whose first bytes are the exact prologue we overwrite.
cands = [(n, a) for n, a in syms.items() if a > 0x2a93000 and "::" in n and not n.startswith("_")]
random.shuffle(cands)
picked = None
for name, va in cands[:4000]:
    off = va_to_offset(segs, va)
    if data[off:off + 3] == PROLOGUE and name.endswith(")") is False:
        picked = (name, va, off)
        break
if not picked:
    sys.exit("no candidate symbol with the expected prologue found")
name, va, off = picked
print(f"target symbol : {name}\n  VA={va:#x}  file_off={off:#x}  bytes={data[off:off+8].hex(' ')}")

rc = subprocess.run(["/opt/cloakbrowser/venv/bin/python", "/opt/cloakbrowser/patch_cloak.py",
                     "--binary", str(copy), "--target", name], text=True, capture_output=True)
print(rc.stdout.strip())
if rc.returncode != 0:
    print(rc.stderr.strip())
    sys.exit(f"patch_cloak.py failed rc={rc.returncode}")

new = copy.read_bytes()
assert new[off:off + 3] == b"\x31\xc0\xc3", f"patch not present at {off:#x}"

# nothing else changed: patch the original in memory the same way and compare hashes
expect = bytearray(data)
expect[off:off + 3] = b"\x31\xc0\xc3"
h_expect = hashlib.sha256(bytes(expect)).hexdigest()
h_got = hashlib.sha256(new).hexdigest()
print(f"hash(orig+patch)  : {h_expect}")
print(f"hash(file patched): {h_got}")
assert h_expect == h_got, "patched file differs from a surgical 3-byte edit"

print("SELFTEST OK — mapping correct, exactly 3 bytes written, verification works")
shutil.rmtree(TMP, ignore_errors=True)
print(f"cleaned {TMP}")
