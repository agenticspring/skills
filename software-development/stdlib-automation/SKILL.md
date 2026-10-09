---
name: stdlib-automation
description: "Use when building Python web automation that must run on constrained environments (Termux, minimal Docker, air-gapped) with ZERO pip dependencies. Covers RSA PKCS1 encryption via pow(), DER public key parsing, JSONP handling, cookie-based CSRF flow, LightSession pattern, and IMAP email verification polling."
version: 1.0.0
author: spring
license: MIT
metadata:
  hermes:
    tags: [automation, stdlib, lightweight, termux, python, web]
    related_skills: [programming, himalaya]
prerequisites:
  commands: [python3]
---

# Stdlib Automation

Build web automation scripts that work **anywhere Python runs** — Termux, VPS, Docker, air-gapped — with **zero `pip install`** dependencies.

## When to Use

- The target runs on Termux / Android (no compiler toolchain for C extensions)
- You want a single `.py` file the user can `scp` and run immediately
- The authentication flow uses RSA encryption (common in Chinese/Asian web services)
- You need IMAP email verification polling
- The target's subdomain APIs don't require full browser JS execution (bypasses curl_cffi/playwright)
- The user explicitly values lightweight / minimal footprint

## Philosophy

1. **`urllib.request` + `http.cookiejar`** handles cookies, redirects, and session persistence. Build a `LightSession` wrapper.
2. **RSA PKCS1 v1.5** can be done with pure `pow()` — no pycryptodome needed. Parse the DER public key with a simple TLV reader.
3. **JSONP** responses wrap JSON in a callback function. Strip via regex `r"\{.*\}"` before `json.loads()`.
4. **CSRF** tokens often come from a JSONP `getInparams` endpoint that sets a `_csrfToken` cookie.
5. **IMAP** polling uses stdlib `imaplib` + `email` — no external mail libraries.

## Core Patterns

### LightSession — stdlib HTTP session

```python
import http.cookiejar, http.client, urllib.request, ssl, urllib.error

class LightSession:
    def __init__(self, proxy: str | None = None):
        self.cookie_jar = http.cookiejar.CookieJar()
        self.proxy = proxy

    def _build_opener(self) -> urllib.request.OpenerDirector:
        handlers = [
            urllib.request.HTTPCookieProcessor(self.cookie_jar),
            urllib.request.HTTPSHandler(context=ssl._create_unverified_context()),
        ]
        if self.proxy:
            handlers.append(urllib.request.ProxyHandler({
                "http": self.proxy, "https": self.proxy,
            }))
        return urllib.request.build_opener(*handlers)

    def get(self, url: str, params: dict | None = None, timeout: int = 30):
        if params: url += "&" if "?" in url else "?" + urlencode(params)
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36",
        })
        try:
            resp = self._build_opener().open(req, timeout=timeout)
            return resp.status, resp.read().decode("utf-8", errors="replace"), dict(resp.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace"), dict(e.headers)

    def get_cookie(self, name: str) -> str:
        for c in self.cookie_jar:
            if c.name == name: return c.value
        return ""
```

### RSA PKCS1 v1.5 — pure Python (no pycryptodome)

```python
import base64, random

def rsa_pkcs1_encrypt(password: str, n: int, e: int) -> str:
    pwd_bytes = password.encode("utf-8")
    k = (n.bit_length() + 7) // 8          # key size in bytes
    ps_len = k - 3 - len(pwd_bytes)
    if ps_len < 8: raise ValueError("Password too long for key size")
    ps = bytes(random.randint(1, 255) for _ in range(ps_len))
    eb = b"\x00\x02" + ps + b"\x00" + pwd_bytes   # PKCS1 v1.5 padding
    m = int.from_bytes(eb, "big")
    c = pow(m, e, n)
    return base64.b64encode(c.to_bytes(k, "big")).decode()
```

### DER RSA Public Key Parser

```python
def _der_decode_pubkey(b64_pem: str) -> tuple[int, int]:
    """Decode SubjectPublicKeyInfo DER to (n, e)."""
    der = base64.b64decode(b64_pem)
    def read_tlv(data, pos):
        tag = data[pos]
        l = data[pos + 1]
        header = 2
        if l & 0x80:
            nlen = l & 0x7f
            l = int.from_bytes(data[pos+2:pos+2+nlen], 'big')
            header = 2 + nlen
        return tag, l, pos + header, pos + header + l

    # Outer SEQUENCE → AlgorithmIdentifier → BIT STRING → RSAPublicKey
    _, _, vs, _ = read_tlv(der, 0)           # outer SPKI SEQUENCE
    pos = vs
    _, _, _, pos = read_tlv(der, pos)         # AlgoId (skip)
    _, _, vs, _ = read_tlv(der, pos)          # BIT STRING
    inner_pos = vs + 1                        # +1 for unused_bits byte
    _, _, rsa_pos, _ = read_tlv(der, inner_pos)
    _, _, n_s, n_e = read_tlv(der, rsa_pos)
    n = int.from_bytes(der[n_s:n_e], 'big')
    _, _, e_s, e_e = read_tlv(der, n_e)
    e = int.from_bytes(der[e_s:e_e], 'big')
    return n, e
```

### JSONP Response Handler

```python
import re, json

def parse_jsonp(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match: raise ValueError("No JSON found in JSONP response")
    return json.loads(match.group())
```

### IMAP Email Verification Polling

```python
import imaplib, email, re, time

def poll_verification_email(email_addr: str, imap_host: str, imap_user: str,
                            imap_pass: str, timeout: int = 300) -> str | None:
    seen = set()
    start = time.time()
    while time.time() - start < timeout:
        try:
            mail = imaplib.IMAP4_SSL(imap_host, 993)
            mail.login(imap_user, imap_pass)
            mail.select('"[Gmail]/All Mail"')
            ok, msgs = mail.search(None, f'(TO "{email_addr}")')
            if ok == "OK":
                for num in msgs[0].split():
                    if num in seen: continue
                    seen.add(num)
                    _, data = mail.fetch(num, "(RFC822)")
                    msg = email.message_from_bytes(data[0][1])
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() in ("text/plain", "text/html"):
                                body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                    for pat in [r"(https?://[^\s\"<>]*(?:confirm|verify|activate)[^\s\"<>]*)",
                                 r"emailkey=([a-zA-Z0-9_\-]+)"]:
                        m = re.search(pat, body)
                        if m:
                            mail.logout()
                            return m.group(1) if m.lastindex else m.group(0)
            mail.logout()
        except Exception:
            pass
        time.sleep(8)
    return None
```

## Common Pitfalls

1. **`read_tlv` returns `(tag, length, value_start, value_end)` — use `value_end` (4th element) to skip to the next TLV**, not `value_start` (3rd). Mixing them produces nonsensical positions and out-of-range errors.
2. **RSA PKCS1 v1.5 requires `k - 3 - len(M)` ≥ 8** for minimum padding. Short passwords work fine (1024-bit key = 128 bytes, minus 11 = 117 chars max). Longer values fail silently.
3. **Some sites check `User-Agent` and `Accept` headers** — the script defaults to Chrome on Windows. If getting 403/blocked, check if the endpoint requires specific headers.
4. **JSONP callbacks** — the server specifies the callback name in the response. The script uses a dummy name (`jq`, `jQueryTest`) — the server echoes it back. If the callback name must match a registered handler, extract it from the site's JS.
5. **Bit length check**: Always verify `n.bit_length() == 1024` (or whatever key size). A 1024-bit key produces 128-byte ciphertext. Wrong byte count means wrong key parsing.
6. **Proxy with `urllib`**: The `ProxyHandler` takes `{ "http": url, "https": url }`. SOCKS proxies are NOT supported by stdlib — use `curl_cffi` for SOCKS.

## Verification Checklist

- [ ] Script runs with `python3` — no `pip install` needed
- [ ] RSA encryption produces base64 output of expected length (172 chars for 1024-bit key)
- [ ] CSRF token is extracted from cookies, not from response body JSON
- [ ] JSONP response is parsed correctly via regex + json.loads
- [ ] IMAP polling actually finds the verification email (check folder name: Gmail uses "[Gmail]/All Mail")
- [ ] Verification link click returns 200 (not 403/redirect to login)

## Templates

- `templates/webnovel-signup.py` — complete Webnovel signup script demonstrating all patterns above
