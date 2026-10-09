# Repo adaptation: bluk-cf to custom domain + Gmail IMAP

Base repo: https://github.com/iAm-182/bluk-cf.git (nodriver, Cloudflare signup + Workers AI token).
Default email layer uses a temp-mail API (mail_api + jwt). Replace with catch-all domain to Gmail IMAP.

## config.json (add these keys)
```json
{
  "mail_mode": "gmail_imap",
  "gmail_user": "<REDACTED>",
  "gmail_app_password": "xxxx xxxx xxxx xxxx",
  "imap_host": "imap.gmail.com",
  "mail_domains": ["<REDACTED>"],
  "headless": false,
  "delay_between_accounts": 60,
  "email_verify_timeout": 180,
  "email_verify_poll_interval": 8,
  "output_file": "results.json"
}
```
NOTE: the cf-bulk/.env uses `app_pasword:` (typo key, colon-delimited). A loader must accept both `app_pasword` and `app_password`, and split on `:` not `=`.

## src/gmail_imap.py
```python
import imaplib, email as email_lib, ssl, time
class GmailIMAP:
    def __init__(self, user, app_password, imap_host="imap.gmail.com", timeout=30):
        self.user=user; self.app_password=app_password.replace(" ",""); self.imap_host=imap_host
    def connect(self):
        ctx=ssl.create_default_context()
        self._conn=imaplib.IMAP4_SSL(self.imap_host, timeout=self.timeout)
        self._conn.login(self.user, self.app_password); self._conn.select("INBOX")
    def close(self):
        if self._conn:
            try: self._conn.logout()
            except Exception: pass
    def fetch_recent(self, target_email, since_ts, limit=30):
        if not self._conn: self.connect()
        typ,data=self._conn.search(None,"UNSEEN")
        out=[]
        for num in reversed(data[0].split()[-limit:]):
            typ,msg_data=self._conn.fetch(num,"(RFC822)")
            for part in msg_data:
                if not isinstance(part,tuple): continue
                msg=email_lib.message_from_bytes(part[1])
                if target_email.lower() not in (msg.get("To","") or "").lower(): continue
                body=""
                if msg.is_multipart():
                    for p in msg.walk():
                        if p.get_content_type()=="text/plain":
                            body+=p.get_payload(decode=True).decode(errors="ignore")
                else:
                    body=msg.get_payload(decode=True).decode(errors="ignore")
                out.append({"id":num.decode(),"from":msg.get("From",""),
                            "to":msg.get("To",""),"text":body,"html":body})
        return out
    def mark_seen(self, mail_id):
        try: self._conn.store(mail_id,"+FLAGS","\\Seen")
        except Exception: pass
```

## src/email_verifier_gmail.py
Reuses extract_verification_link from email_verifier.py, polls Gmail:
```python
from .gmail_imap import GmailIMAP
from .email_verifier import extract_verification_link
async def verify_cloudflare_email_gmail(page, email, gmail_user, gmail_app_password,
        imap_host="imap.gmail.com", timeout=180, poll_interval=8):
    client=GmailIMAP(gmail_user, gmail_app_password, imap_host)
    start=time.time()
    try:
        while time.time()-start < timeout:
            mails=client.fetch_recent(email, since_ts=start, limit=30)
            for mail in mails:
                blob=" ".join(str(mail.get(k,"")) for k in ("from","subject","text","html")).lower()
                if "cloudflare" not in blob or not any(w in blob for w in ("verify","verification","confirm","activate","email")):
                    continue
                link=extract_verification_link(mail)
                if not link: continue
                await page.get(link); await asyncio.sleep(15)
                body=str(await page.evaluate("document.body?document.body.innerText:''", return_by_value=True)).lower()
                url=str(await page.evaluate("location.href", return_by_value=True)).lower()
                if any(k in body for k in ("verified","success","already verified")) or ("dash.cloudflare.com" in url and "login" not in url):
                    client.mark_seen(mail["id"]); return EmailVerifyResult(True, link=link)
            await asyncio.sleep(poll_interval)
        return EmailVerifyResult(False, error=f"not_found_after_{timeout}s")
    finally:
        client.close()
```

## main.py patches
1. Imports: `from src.email_verifier_gmail import verify_cloudflare_email_gmail`
2. In create_account: branch on mail_mode. For gmail_imap skip EmailGenerator, set email=f"{username}@{domain}", mail_jwt="". Else legacy temp-mail path.
3. Verify step: if mail_mode=="gmail_imap" call verify_cloudflare_email_gmail(page, email=email, gmail_user=..., gmail_app_password=..., imap_host=...); else verify_cloudflare_email(...).
4. uc.start(...) MUST include:
   browser_executable_path=os.environ.get("CHROME_BIN","/usr/bin/chromium-browser"),
   browser_args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage"],
   sandbox=False.

## Run
```bash
cd /root/bluk-cf && . .venv/bin/activate
export CHROME_BIN=/usr/bin/chromium-browser
export DISPLAY=:99          # Xvfb must be running: Xvfb :99 -screen 0 1280x800x24 &
python3 main.py --accounts 1 --no-dashboard --delay 10
```
