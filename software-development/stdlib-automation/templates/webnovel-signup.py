#!/usr/bin/env python3
"""
Webnovel Signup — complete working example of stdlib-automation patterns.

Run anywhere (Termux, VPS, laptop) with zero pip dependencies.

Usage:
  python3 webnovel-signup.py <email> <password> [proxy_url]

Flow:
  1. Get CSRF token from ptlogin.webnovel.com JSONP API
  2. RSA-encrypt password using Webnovel's public key (1024-bit)
  3. Submit registration via JSONP endpoint
  4. Poll Gmail IMAP for verification email
  5. Click verification link

Key observations:
  - passport.webnovel.com subdomain has NO Cloudflare JS challenge
    (only main www.webnovel.com does) — pure HTTP works.
  - Password must be 6-18 alphanumeric chars only (no symbols/spaces).
  - IPs get temporarily suspended after a few attempts.
"""
import base64, http.cookiejar, http.client, imaplib, json, os, random, re, ssl
import sys, time, urllib.error, urllib.request, email as eml
from pathlib import Path
from urllib.parse import urlencode

PUBKEY_B64 = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDOf5B7Sg/EsfK+29BhFn1SUgoXgcLP9Dl1Sf3g3PgwRTEkqMwhFVpIYoNVo1TV1q6Y6dRYZ1BExt/tqQqJcLvQhCKcb4JuINKdftwG5le+Q2n6S/Ioyx7euYZgkmm3LSQ5VW7y+VGpMvBi70CTNFAcIM4j4J1YzLN/RRpFysAxBQIDAQAB"
APP_ID, AREA_ID = "900", "1"
RETURN_URL = "https://www.webnovel.com/"

def _der_decode_pubkey(b64):
    der = base64.b64decode(b64)
    def tlv(d, p):
        t, l = d[p], d[p+1]
        h = 2
        if l & 0x80:
            nl = l & 0x7f
            l = int.from_bytes(d[p+2:p+2+nl], 'big')
            h = 2 + nl
        return t, l, p+h, p+h+l
    _,_,v,_ = tlv(der, 0); p=v
    _,_,_,p = tlv(der, p); _,_,v,_ = tlv(der, p)
    _,_,rp,_ = tlv(der, v+1); _,_,ns,ne = tlv(der, rp)
    n = int.from_bytes(der[ns:ne], 'big')
    _,_,es,ee = tlv(der, ne)
    return n, int.from_bytes(der[es:ee], 'big')

def rsa_encrypt(pwd, n, e):
    pw = pwd.encode()
    k = (n.bit_length()+7)//8
    ps = bytes(random.randint(1,255) for _ in range(k-3-len(pw)))
    m = int.from_bytes(b"\x00\x02"+ps+b"\x00"+pw, 'big')
    return base64.b64encode(pow(m,e,n).to_bytes(k,'big')).decode()

class Session:
    def __init__(self, proxy=None):
        self.jar = http.cookiejar.CookieJar(); self.px = proxy
    def get(self, url, params=None, timeout=30):
        if params: url += "&" if "?" in url else "?" + urlencode(params)
        h = [urllib.request.HTTPCookieProcessor(self.jar),
             urllib.request.HTTPSHandler(context=ssl._create_unverified_context())]
        if self.px: h.append(urllib.request.ProxyHandler({"http":self.px,"https":self.px}))
        req = urllib.request.Request(url, headers={
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36"})
        try:
            r = urllib.request.build_opener(*h).open(req, timeout=timeout)
            return r.status, r.read().decode("utf-8","replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8","replace")
    def cookie(self,name):
        for c in self.jar:
            if c.name==name: return c.value
        return ""

def poll_imap(email_addr, imap_user, imap_pass, timeout=300):
    seen = set(); start = time.time()
    while time.time()-start < timeout:
        try:
            m = imaplib.IMAP4_SSL("imap.gmail.com",993)
            m.login(imap_user, imap_pass); m.select('"[Gmail]/All Mail"')
            ok, msgs = m.search(None, f'(TO "{email_addr}")')
            if ok=="OK":
                for n in msgs[0].split():
                    if n in seen: continue
                    seen.add(n); _,d = m.fetch(n, "(RFC822)")
                    msg = eml.message_from_bytes(d[0][1])
                    body=""
                    if msg.is_multipart():
                        for p in msg.walk():
                            if p.get_content_type() in ("text/plain","text/html"):
                                body=p.get_payload(decode=True).decode("utf-8","ignore"); break
                    else: body=msg.get_payload(decode=True).decode("utf-8","ignore")
                    for pat in [r"(https?://ptlogin\.webnovel\.com[^\s\"<>]*)",
                                 r"emailkey=([a-zA-Z0-9_\-]+)"]:
                        mt=re.search(pat,body)
                        if mt: m.logout(); return mt.group(1) if mt.lastindex else mt.group(0)
            m.logout()
        except: pass
        time.sleep(8)
    return None

def main():
    if len(sys.argv)<3:
        print("Usage: python3 webnovel-signup.py <email> <password> [proxy]"); sys.exit(1)
    email,pwd = sys.argv[1].strip(), sys.argv[2].strip()
    proxy = sys.argv[3] if len(sys.argv)>=4 else os.environ.get("PROXY_URL","")
    print(f"Signup {email} proxy={proxy or 'none'}")

    n,e = _der_decode_pubkey(PUBKEY_B64)
    print(f"RSA {n.bit_length()}-bit OK")

    s = Session(proxy)
    s.get(f"https://passport.webnovel.com/register.html?appid={APP_ID}&areaid={AREA_ID}&target=iframe&returnUrl={RETURN_URL}")
    _,b = s.get("https://ptlogin.webnovel.com/login/getInparams", {
        "callback":"jq","_csrfToken":"","method":"LoginV1.getInParamsCallback",
        "format":"jsonp","appid":APP_ID,"areaid":AREA_ID,"target":"iframe","returnurl":RETURN_URL})
    csrf = s.cookie("_csrfToken")
    if not csrf: print("No CSRF"); sys.exit(1)
    print(f"CSRF {csrf[:20]}...")

    enc = rsa_encrypt(pwd,n,e)
    _,b = s.get("https://ptlogin.webnovel.com/login/doregister", {
        "_csrfToken":csrf,"method":"LoginV1.registerCallback","format":"jsonp","callback":"jq",
        "appid":APP_ID,"areaid":AREA_ID,"accountType":"102","backUrl":RETURN_URL,
        "account":email,"email":email,"password":enc,"validateCode":"","nextAction":"0","fromuid":"0","returnurl":RETURN_URL})
    m = re.search(r"\{.*\}",b,re.DOTALL)
    r = json.loads(m.group())
    if r.get("code")==0:
        print("Registered OK")
    else:
        print(f"Fail: {r.get('code')} {r.get('msg')}"); sys.exit(1)

    url = poll_imap(email, os.environ.get("IMAP_USER",""), os.environ.get("IMAP_PASS",""))
    if url:
        s.get(url); print("Verified OK")
    print(f"Done: {email} -> https://www.webnovel.com/login")

if __name__=="__main__":
    main()
