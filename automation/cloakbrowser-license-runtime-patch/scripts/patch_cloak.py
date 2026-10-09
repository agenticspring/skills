#!/usr/bin/env python3
"""Patch CloakBrowser Pro binary: neutralise ungoogled::LicenseRuntime::Start/End.

Mechanism (verified by the field notes): the Pro build embeds a license runtime
that registers a seat with the vendor and terminates the process (exit 76) when
the seat cap is hit. `Start` and `End` are the entry points. Overwriting each
prologue with `xor eax,eax ; ret` makes them no-ops, so no seat request is sent
and no denial can fire. The response path is Ed25519-verified, so faking the
server is not an option — returning early is the only local lever.

Usage:
  patch_cloak.py --binary <path/to/chrome> [--dry-run]

Notes:
  * VA -> file offset is derived from the PT_LOAD program headers, so it is
    correct for any build (the old notes hardcoded `VA - 0x1000`).
  * The patch is applied to a single copy of the file. The caller must copy the
    WHOLE Pro directory (icu/snapshot/pak siblings are required).
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROLOGUE = b"\x55\x48\x89"       # push rbp ; mov rsp,rbp
PATCH = b"\x31\xc0\xc3"          # xor eax,eax ; ret
TARGETS = ("LicenseRuntime::Start", "LicenseRuntime::End")


def nm_symbols(binary: str) -> dict[str, int]:
    """Map mangled + demangled name -> VA for every .text symbol."""
    out = subprocess.run(["nm", "-C", binary], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"nm failed on {binary}: {out.stderr.strip()[:400]}")
    syms: dict[str, int] = {}
    for line in out.stdout.splitlines():
        parts = line.split(" ", 2)
        if len(parts) != 3:
            continue
        addr, _typ, name = parts
        try:
            syms[name] = int(addr, 16)
        except ValueError:
            continue
    return syms


def load_segments(binary: str) -> list[tuple[int, int, int]]:
    """[(vaddr, file_offset, filesz)] for every PT_LOAD."""
    out = subprocess.run(["readelf", "-l", "-W", binary], capture_output=True, text=True).stdout
    segs = []
    for m in re.finditer(
        r"LOAD\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)",
        out,
    ):
        off, vaddr, _phys, filesz, _memsz = (int(g, 16) for g in m.groups())
        segs.append((vaddr, off, filesz))
    return segs


def va_to_offset(segs, va: int) -> int:
    for vaddr, off, filesz in segs:
        if vaddr <= va < vaddr + filesz:
            return va - vaddr + off
    raise SystemExit(f"VA {va:#x} is not covered by any PT_LOAD segment")


def find_runtime(syms: dict[str, int], targets=TARGETS) -> dict[str, int]:
    hits: dict[str, int] = {}
    for target in targets:
        matches = {n: a for n, a in syms.items() if target in n and a != 0}
        if not matches:
            continue
        # exact suffix wins over overloads/related helpers
        exact = {n: a for n, a in matches.items() if n.endswith(target + ")") or n.endswith(target)}
        pick = min(exact or matches, key=lambda n: (len(n), n))
        hits[target] = (matches[pick], pick)
    return hits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--all-runtime-symbols", action="store_true")
    ap.add_argument("--target", action="append", default=None,
                    help="symbol substring to patch (repeatable). Default: the license runtime. "
                         "Used to self-test the patch path on a symbol with a known prologue.")
    args = ap.parse_args()

    targets = tuple(args.target) if args.target else TARGETS
    binary = args.binary
    syms = nm_symbols(binary)
    segs = load_segments(binary)
    data = bytearray(Path(binary).read_bytes())

    runtime = {n: a for n, a in syms.items() if "LicenseRuntime" in n}
    if not runtime and not args.target:
        sys.exit("no LicenseRuntime symbols found — this looks like the FREE binary "
                 "(the license runtime only exists in the Pro build)")
    if runtime and not args.target and args.all_runtime_symbols:
        for name, addr in sorted(runtime.items(), key=lambda kv: kv[1]):
            print(f"{addr:#011x}  {name}")

    hits = find_runtime(syms, targets)
    missing = [t for t in targets if t not in hits]
    if missing:
        sys.exit(f"could not locate {missing} among {len(runtime)} LicenseRuntime symbols")

    for target, (va, name) in hits.items():
        off = va_to_offset(segs, va)
        cur = bytes(data[off:off + len(PROLOGUE)])
        state = "ALREADY PATCHED" if cur == PATCH else (
            "prologue ok" if cur == PROLOGUE else f"UNEXPECTED prologue {cur.hex(' ')}")
        print(f"{target:26s} VA={va:#x} off={off:#x}  {state}  <- {name}")
        if cur == PATCH:
            continue
        if cur != PROLOGUE:
            sys.exit(f"refusing to patch {target}: unexpected prologue bytes")
        if not args.dry_run:
            data[off:off + len(PATCH)] = PATCH

    if args.dry_run:
        print("dry-run: nothing written")
        return

    backup = binary + ".orig"
    if not Path(backup).exists():
        shutil.copy2(binary, backup)
    Path(binary).write_bytes(bytes(data))
    Path(binary).chmod(0o755)
    print(f"patched {binary} (backup: {backup})")

    # verify on disk
    check = Path(binary).read_bytes()
    for target, (va, _n) in hits.items():
        off = va_to_offset(segs, va)
        assert check[off:off + len(PATCH)] == PATCH, f"{target} not patched on disk"
    print("verification: both prologues now carry xor eax,eax ; ret")


if __name__ == "__main__":
    main()
