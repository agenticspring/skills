# Gmail IMAP — Folder Names by Locale

## Problem
Gmail uses locale-dependent folder names. `mail.select('"[Gmail]/All Mail"')` fails on Indonesian Gmail.

## Folder Names

| English | Indonesian | Other |
|---------|-----------|-------|
| INBOX | INBOX | INBOX |
| [Gmail]/All Mail | [Gmail]/Semua Email | [Gmail]/Alle Nachrichten (DE) |
| [Gmail]/Spam | [Gmail]/Spam | [Gmail]/Spam |
| [Gmail]/Trash | [Gmail]/Tong Sampah | [Gmail]/Papierkorb |
| [Gmail]/Sent Mail | [Gmail]/Surat Terkirim | [Gmail]/Gesendet |

## Strategy
Always try multiple folder names in order:
```python
folders = ['INBOX', '"[Gmail]/All Mail"', '"[Gmail]/Semua Email"']
```

## IMAP Search Filters

```python
# By recipient (reliable for non-catchall)
mail.search(None, f'(TO "{email_addr}")')

# By sender + unseen (fallback for catch-all domains)
mail.search(None, '(UNSEEN FROM "webnovel")')
```

## Email Structure

Webnovel emails are HTML-only (no text/plain). Always try `text/html` when `text/plain` is empty.

## Tracking Links

Webnovel uses `post.eu.spmailtechnol.com` for email tracking. Links look like:
```
https://post.eu.spmailtechnol.com/f/a/LONGHASH~~/...
```

These redirect to:
```
https://passport.webnovel.com/confirm.html?emailkey=BASE64&appid=900&areaid=1
```

Always follow the redirect to get the real activation URL.
