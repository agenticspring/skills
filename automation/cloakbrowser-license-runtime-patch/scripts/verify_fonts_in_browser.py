#!/usr/bin/env python3
"""End-to-end font proof INSIDE the patched CloakBrowser.

1. fc-match: which file fontconfig resolves for each family (host level).
2. Width probe in the real browser: each family is compared against a
   deliberately NONEXISTENT family as the negative control. A family whose width
   equals the control fell back to a generic font; anything else was really used.
   (Comparing only against serif/sans-serif/monospace gives false verdicts, and
   document.fonts.check() returns true even for missing families.)
"""
import os
import subprocess

os.environ.setdefault("CLOAKBROWSER_BINARY_PATH", "/opt/cloakbrowser/pro-patched/chrome")
os.environ.pop("CLOAKBROWSER_LICENSE_KEY", None)
os.environ.setdefault("CLOAKBROWSER_SUPPRESS_FONT_WARNING", "1")

WIN = ["Segoe UI", "Segoe UI Light", "Calibri", "Marlett", "MS UI Gothic",
       "Franklin Gothic", "Consolas", "Courier New"]
OFFICE = ["MT Extra", "Century", "Century Gothic", "MS Reference Specialty",
          "Book Antiqua", "Bookshelf Symbol 7", "Monotype Corsiva", "Bookman Old Style"]
FAMS = WIN + OFFICE

print("=== fc-match (host fontconfig) ===")
for fam in FAMS:
    out = subprocess.run(["fc-match", "-f", "%{family}|%{file}", fam], capture_output=True, text=True).stdout
    resolved, path = (out.split("|") + [""])[:2]
    tag = "OK      " if fam.lower() in resolved.lower() else "FALLBACK"
    print(f"  {tag} {fam:24s} -> {resolved:26s} {os.path.basename(path)}")

print("\n=== width probe inside the patched browser ===")
from cloakbrowser import launch  # noqa: E402

b = launch(headless=True)
p = b.new_page()
p.goto("about:blank")
res = p.evaluate(
    """(fams) => {
  const s = document.createElement('span');
  s.style.cssText = 'position:absolute;left:-9999px;font-size:72px;white-space:nowrap';
  s.textContent = 'Hamburgefonstiv 0123456789 Wg';
  document.body.appendChild(s);
  const w = (css) => { s.style.fontFamily = css; return s.getBoundingClientRect().width; };
  const out = {__nothing: +w('"NoSuchFontXYZQQ"').toFixed(2)};
  for (const f of fams) out[f] = +w(`"${f}"`).toFixed(2);
  s.remove();
  return out;
}""",
    FAMS,
)
nothing = res.pop("__nothing")
print(f"  negative control (nonexistent family): {nothing}")
ok = 0
for fam, width in res.items():
    used = abs(width - nothing) > 0.01
    ok += used
    print(f"  {'USED    ' if used else 'FELL-BACK'} {fam:24s} {width:>9}")
print(f"\n{ok}/{len(FAMS)} families render with their own metrics inside the patched build")
b.close()
