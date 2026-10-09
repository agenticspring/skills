#!/usr/bin/env python3
"""OCR probe for invite-code detection in X tweet images (tesseract + PIL).

Usage:
    python ocr_probe.py <image_path> [expected_code]

Tests the exact pipeline used by the invite-code watchdog:
  grayscale -> upscale if small / cap if huge -> autocontrast -> binarize
  -> tesseract psm 3, 6, 11 -> OCR-noise normalization -> BUFO-* extraction

Prints per-psm timing and whether the expected code was found.
Requires: pip install pillow, tesseract binary on PATH.
"""
import re
import subprocess
import sys
import time

from PIL import Image, ImageOps

EXPECTED = sys.argv[2].upper() if len(sys.argv) > 2 else None
PATH = sys.argv[1] if len(sys.argv) > 1 else None

if not PATH:
    print("usage: ocr_probe.py <image_path> [expected_code]")
    sys.exit(1)


def extract_codes_ocr(text: str) -> list[str]:
    """BUFO-* codes from OCR text, tolerating dash read as ':' / space / '°' / '*'.
    Adjust the prefix regex to match the target code scheme."""
    if not text:
        return []
    norm = re.sub(r"(?i)\bBUFO\s*[^A-Za-z0-9]{1,4}\s*", "BUFO-", text)
    return sorted({m.group(0) for m in re.finditer(r"\bBUFO-[A-Z0-9][A-Z0-9_-]{1,31}\b", norm, re.I)})


def main() -> int:
    t0 = time.time()
    img = Image.open(PATH).convert("L")
    print(f"size: {img.size}")
    if max(img.size) > 2000:
        scale = 2000 / max(img.size)
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        print("capped to:", img.size)
    elif max(img.size) < 1600:
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        print("upscaled to:", img.size)
    img = ImageOps.autocontrast(img)
    img = img.point(lambda p: 255 if p > 140 else 0)
    png = "/tmp/ocr_probe_prep.png"
    img.save(png)
    print(f"prep: {time.time() - t0:.2f}s")

    found_all = set()
    for psm in ("3", "6", "11"):
        t1 = time.time()
        r = subprocess.run(["tesseract", png, "stdout", "--psm", psm],
                           capture_output=True, text=True, timeout=90)
        dt = time.time() - t1
        codes = extract_codes_ocr(r.stdout or "")
        found_all.update(codes)
        print(f"psm={psm}: {dt:.2f}s codes={codes}")
        if EXPECTED and EXPECTED in codes:
            print(f"EXPECTED {EXPECTED} FOUND (psm={psm})")
    print(f"total: {time.time() - t0:.2f}s | aggregate codes: {sorted(found_all)}")
    if EXPECTED:
        ok = EXPECTED in found_all
        print(f"RESULT: {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
