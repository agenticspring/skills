#!/usr/bin/env python3
"""Install a Windows font set on a Linux host so a Windows-spoofing CloakBrowser
stops contradicting its own persona. Idempotent.

Covered: the 8 'Windows tells' the wrapper scores (Segoe UI, Segoe UI Light,
Calibri, Marlett, MS UI Gothic, Franklin Gothic, Consolas, Courier New) plus the
MS Office supplemental pack and the common Windows text fonts.

Sources (public):
  * mrbvrz/segoe-ui-linux   - full Segoe UI family
  * sheying2013/OpenBrowser - Windows font dump under .../wayfern_fonts/win11/
                              (Git LFS: plain raw URLs return 130-byte pointers,
                               use the media.githubusercontent.com endpoint)
  * sheying2013/OpenBrowser - win11 msgothic ttc (declares MS UI Gothic)
Validation: every candidate must be a real font (container magic) AND declare the
requested family (fc-query). Filenames are never trusted.

Usage: install_windows_fonts.py [--dest DIR] [--verify-only]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

OPENB = "sheying2013/OpenBrowser"
OPENB_BRANCH = "main"
OPENB_DIR = "Browserapp/kernels/windows-x64/wayfern_fonts/win11/"
MEDIA = f"https://media.githubusercontent.com/media/{OPENB}/{OPENB_BRANCH}/"
SEGOE_REPO = "mrbvrz/segoe-ui-linux"
MAGIC = {b"\x00\x01\x00\x00": "ttf", b"OTTO": "otf", b"ttcf": "ttc", b"true": "ttf"}

# family that must be declared -> canonical filename, filename hints
TARGETS = [
    ("Segoe UI", "segoeui.ttf", ["segoeui.ttf"]),
    ("Segoe UI Light", "segoeuil.ttf", ["segoeuil.ttf"]),
    ("Calibri", "calibri.ttf", ["calibri"]),
    ("Marlett", "marlett.ttf", ["marlett"]),
    ("MS UI Gothic", "msgothic.ttc", ["msgothic"]),
    # Windows ships Franklin Gothic (base family) + styles; the wrapper's tell is the
    # "franklin gothic" substring, so the base family is what must resolve.
    ("Franklin Gothic", "franklin-gothic.ttf", ["franklin gothic.ttf"]),
    ("Franklin Gothic", "franklin-gothic-italic.ttf", ["franklin gothic italic"]),
    ("Consolas", "consolas.ttf", ["consol"]),
    ("Courier New", "courier-new.ttf", ["cour"]),
    # MS Office supplemental pack (informational for the wrapper, real for probes)
    ("MT Extra", "mt-extra.ttf", ["mt extra"]),
    ("Century", "century.ttf", ["century."]),
    ("Century Gothic", "century-gothic.ttf", ["century gothic"]),
    ("MS Reference Specialty", "ms-reference-specialty.ttf", ["reference specialty"]),
    ("Book Antiqua", "book-antiqua.ttf", ["book antiqua"]),
    ("Bookshelf Symbol 7", "bookshelf-symbol-7.ttf", ["bookshelf"]),
    ("Monotype Corsiva", "monotype-corsiva.ttf", ["corsiva"]),
    ("Bookman Old Style", "bookman-old-style.ttf", ["bookman"]),
    # common Windows text fonts (also feed the Mac/Office tell lists)
    ("Arial", "arial.ttf", ["arialmt.otf", "arial.ttf", "arialmt"]),
    ("Tahoma", "tahoma.ttf", ["tahoma"]),
    ("Georgia", "georgia.ttf", ["georgia"]),
    ("Verdana", "verdana.ttf", ["verdana"]),
    ("Trebuchet MS", "trebuchet-ms.ttf", ["trebuchet"]),
    ("Comic Sans MS", "comic-sans-ms.ttf", ["comic sans"]),
    ("Times New Roman", "times-new-roman.ttf", ["times new roman", "timesnewroman"]),
    ("Cambria", "cambria.ttf", ["cambria"]),
    ("Segoe UI Symbol", "segoe-ui-symbol.ttf", ["segoe ui symbol", "segoeuisymbol"]),
    ("Microsoft Sans Serif", "microsoft-sans-serif.ttf", ["microsoft sans serif", "microsoftsansserif"]),
    ("Webdings", "webdings.ttf", ["webdings"]),
    ("Wingdings", "wingdings.ttf", ["wingdings."]),
    ("Lucida Console", "lucida-console.ttf", ["lucida console", "lucidaconsole"]),
]

TOKEN = ""
try:
    m = re.search(r"^(?:GITHUB_TOKEN_2|GH_TOKEN_2)=(.+)$", open(os.path.expanduser("~/.hermes/.env")).read(), re.M)
    if m:
        TOKEN = m.group(1).strip().strip("'\"")
except OSError:
    pass


def get(url: str, auth: bool = False) -> bytes:
    h = {"User-Agent": "font-fetch"}
    if auth:
        h.update({"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=180) as r:
        return r.read()


def families(path: str) -> str:
    try:
        return subprocess.run(["fc-query", "-f", "%{family}", path],
                              capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return ""


def install(blob: bytes, dest_dir: str, canonical: str, family: str) -> str | None:
    ext = MAGIC.get(blob[:4])
    if ext is None:
        return None
    name = canonical if os.path.splitext(canonical)[1] == "." + ext else os.path.splitext(canonical)[0] + "." + ext
    tmp = "/tmp/_font_validate"
    with open(tmp, "wb") as fh:
        fh.write(blob)
    if family.lower() not in families(tmp).lower():
        return None
    with open(os.path.join(dest_dir, name), "wb") as fh:
        fh.write(blob)
    return name


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="/usr/share/fonts/truetype/win")
    ap.add_argument("--verify-only", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.dest, exist_ok=True)

    win11: list[str] = []
    if not args.verify_only:
        print("listing win11 font set …")
        tree = json.loads(get(f"https://api.github.com/repos/{OPENB}/git/trees/{OPENB_BRANCH}?recursive=1", auth=True))
        win11 = sorted({t["path"][len(OPENB_DIR):] for t in tree["tree"]
                        if t["path"].startswith(OPENB_DIR) and "/" not in t["path"][len(OPENB_DIR):]})
        print(f"  {len(win11)} files")

        for family, canonical, hints in TARGETS:
            present = os.path.exists(os.path.join(args.dest, canonical))
            found = None
            # 1. Segoe UI family: dedicated repo (full files, no LFS)
            if family.startswith("Segoe UI") and hints[0].startswith("segoeui"):
                try:
                    blob = get(f"https://raw.githubusercontent.com/{SEGOE_REPO}/master/{hints[0]}")
                    found = install(blob, args.dest, canonical, family)
                except Exception:
                    pass
            # 2. the win11 dump (LFS -> media endpoint)
            if not found:
                cands = [n for n in win11
                         if any(h in n.lower().replace("_", " ").replace("-", " ") for h in hints)]
                cands.sort(key=lambda n: (sum(w in n.lower() for w in
                                              ("bold", "italic", "oblique", "light", "black", "condensed")), len(n)))
                for cand in cands[:10]:
                    try:
                        blob = get(MEDIA + urllib.parse.quote(OPENB_DIR + cand))
                    except Exception:
                        continue
                    found = install(blob, args.dest, canonical, family)
                    if found:
                        print(f"  {family:24s} OK  {len(blob):>10,}B  {cand} -> {found}")
                        break
            if not found and not present:
                print(f"  {family:24s} MISSING")
            elif found and present:
                print(f"  {family:24s} refreshed")

    subprocess.run(["fc-cache", "-f"], capture_output=True)
    listing = subprocess.run(["fc-list"], capture_output=True, text=True).stdout.lower()
    win = ["Segoe UI", "Segoe UI Light", "Calibri", "Marlett", "MS UI Gothic",
           "Franklin Gothic", "Consolas", "Courier New"]
    off = ["MT Extra", "Century", "Century Gothic", "MS Reference Specialty",
           "Wingdings 2", "Wingdings 3", "Book Antiqua", "Bookshelf Symbol 7",
           "Monotype Corsiva", "Bookman Old Style"]
    w = sum(1 for f in win if f.lower() in listing)
    o = sum(1 for f in off if f.lower() in listing)
    print(f"\nWindows tells: {w}/8   Office pack: {o}/10   total fonts: {len(listing.splitlines())}")
    print("wrapper will report: " + ("Win fonts: ok (8/8)" if w == 8 else f"Win fonts: partial ({w}/8)"))
    return 0 if w == 8 else 1


if __name__ == "__main__":
    sys.exit(main())
