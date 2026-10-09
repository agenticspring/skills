#!/usr/bin/env python3
"""
Mass signup skeleton — batch registration with proxy rotation & IMAP verification.
Copy this, customize the register() function for your target site, then run:

    python3 mass_signup.py [count]
"""
from __future__ import annotations
import base64, http.cookiejar, imaplib, json, os, random, re, ssl, sys, time, urllib.request
import email as email_lib
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).parent
PROXY_FILE = HERE / "proxy.txt"
ACCOUNTS_FILE = HERE / "accounts.txt"

# ── Config (override these) ──
DOMAIN = os.environ.get("DOMAIN", "example.com")
IMAP_HOST = os.environ.get("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
IMAP_USER = os.environ.get("IMAP_USER", "")
IMAP_PASS = os.environ.get("IMAP_PASS", "")
FIXED_PASSWORD = os.environ.get("PASSWORD", "")  # "" = random

# ── Proxy Pool ──
class ProxyPool:
    def __init__(self, path):
        self.proxies, self.dead, self.idx = [], set(), 0
        if path.exists():
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"): continue
                parts = line.split(":")
                if len(parts) == 4:
                    self.proxies.append(f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}")
                elif len(parts) == 2:
                    self.proxies.append(f"http://{line}")
    def mark_dead(self, url):
        try: self.dead.add(self.proxies.index(url))
        except ValueError: pass
    def random(self):
        alive = [p for i,p in enumerate(self.proxies) if i not in self.dead]
        return random.choice(alive) if alive else None
    @property
    def alive_count(self): return len(self.proxies) - len(self.dead)

# ── Lightweight HTTP Session ──
class LightSession:
    def __init__(self, proxy=None):
        self.jar = http.cookiejar.CookieJar(); self.proxy = proxy
    def _opener(self):
        h = [urllib.request.HTTPCookieProcessor(self.jar),
             urllib.request.HTTPSHandler(context=ssl._create_unverified_context())]
        if self.proxy:
            h.append(urllib.request.ProxyHandler({"http":self.proxy,"https":self.proxy}))
        return urllib.request.build_opener(*h)
    def get(self, url, params=None, timeout=30):
        if params: url += ("&" if "?" in url else "?") + urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"})
        try:
            r = self._opener().open(req, timeout=timeout)
            return r.status, r.read().decode("utf-8",errors="replace"), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8",errors="replace"), dict(e.headers)
        except urllib.error.URLError as e:
            return 0, f"URLError: {e.reason}", {}
    def get_cookie(self, name):
        for c in self.jar:
            if c.name == name: return c.value
        return ""

# ── Identity ──
NAMES = {
    "usa": {
        "first": ["James","John","Mary","Patricia","Robert","Michael","Jennifer","Linda"],
        "last": ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis"],
    },
    "asia": {
        "first": ["Wei","Jun","Li","Jing","Hao","Yuto","Hiro","Sora","Minjun","Jisoo","Ananya","Priya"],
        "last": ["Wang","Li","Zhang","Liu","Chen","Sato","Suzuki","Tanaka","Kim","Park","Sharma","Verma"],
    },
    "europe": {
        "first": ["Liam","Noah","Emma","Olivia","Lukas","Finn","Hanna","Anna","Matteo","Leonardo","Sofia","Giulia"],
        "last": ["Mueller","Schmidt","Schneider","Martin","Bernard","Garcia","Rodriguez","Rossi","Russo","Jansen","Andersen","Jensen"],
    },
}

def gen_identity(domain):
    region = random.choice(list(NAMES.keys()))
    pool = NAMES[region]
    first = random.choice(pool["first"]); last = random.choice(pool["last"])
    num = random.randint(10, 999)
    email = f"{first.lower()}.{last.lower()}{num}@{domain}"
    password = FIXED_PASSWORD or "".join(random.choices("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",k=random.randint(5,8)) + random.choices("0123456789",k=random.randint(2,4)))
    return email, password, region

# ── Registration (override this) ──
BAN_CODES = {11401, -11051, -11055, -11053}

def register(email, password, proxy=None) -> tuple[int, str]:
    """Override with target site's registration flow. Returns (code, msg)."""
    # Placeholder: replace with actual HTTP calls
    sess = LightSession(proxy)
    # ... site-specific logic ...
    return 0, "ok"

# ── IMAP ──
def poll_email(email_addr, timeout=120):
    if not IMAP_PASS: return None
    seen, start = set(), time.time()
    while time.time() - start < timeout:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            mail.login(IMAP_USER, IMAP_PASS)
            mail.select('"[Gmail]/All Mail"')
            ok, msgs = mail.search(None, f'(TO "{email_addr}")')
            if ok == "OK":
                for num in msgs[0].split():
                    if num in seen: continue
                    seen.add(num)
                    _, data = mail.fetch(num, "(RFC822)")
                    msg = email_lib.message_from_bytes(data[0][1]); body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() in ("text/plain","text/html"):
                                try: body = part.get_payload(decode=True).decode("utf-8",errors="ignore")
                                except: continue
                                break
                    else: body = msg.get_payload(decode=True).decode("utf-8",errors="ignore")
                    # Extract verification URL
                    m = re.search(r"(https?://[^\s\"<>]*(?:confirm|verify|activate)[^\s\"<>]*)", body)
                    if m:
                        mail.logout(); return m.group(1)
            mail.logout()
        except: pass
        time.sleep(6)
    return None

# ── Main ──
def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    no_imap = "--no-imap" in sys.argv

    proxy_pool = ProxyPool(PROXY_FILE)
    print(f"Mass Signup — {count} accounts, {proxy_pool.alive_count} proxies, IMAP={'on' if IMAP_PASS and not no_imap else 'off'}")

    success, failed = 0, 0
    for i in range(count):
        email, password, region = gen_identity(DOMAIN)
        proxy = proxy_pool.random() if proxy_pool.alive_count else None
        print(f"[{i+1}/{count}] {region.upper()} — {email}")

        code, msg = register(email, password, proxy)
        if code == 0:
            print("  ✅ Registered")
            with open(ACCOUNTS_FILE, "a") as f: f.write(f"{email}:{password}\n")
            success += 1
            if not no_imap:
                url = poll_email(email)
                if url: print(f"  📧 Verified: {url[:80]}")
        elif code in BAN_CODES:
            if proxy: proxy_pool.mark_dead(proxy)
            print(f"  ❌ Banned ({code}), {proxy_pool.alive_count} proxies left")
            if proxy_pool.alive_count:
                code2, _ = register(email, password, proxy_pool.random())
                if code2 == 0:
                    print("  ✅ Registered (retry)")
                    with open(ACCOUNTS_FILE, "a") as f: f.write(f"{email}:{password}\n")
                    success += 1
                    continue
            failed += 1
        else:
            print(f"  ❌ Failed: code={code} {msg[:80]}")
            failed += 1

    print(f"\nDone: {success} success, {failed} failed")

if __name__ == "__main__":
    main()
