# Webnovel auth findings

Session-specific technical findings from reverse-engineering Webnovel auth.

## Durable findings

### Register flow
- Registration page / frontend can expose RSA public key through current JS assets rather than stable HTML fields.
- A hardcoded pubkey is unsafe; runtime extraction is more reliable.
- Registration endpoint success does not by itself prove a usable account exists.

### Email confirmation flow
- Webnovel emails can contain multiple `spmailtechnol.com` URLs.
- The real action link is typically the CTA/tracking form `.../f/a/...`.
- Pixel/beacon links like `.../q/...` are not the activation URL and must be ignored.
- Following the CTA link can resolve to `passport.webnovel.com/confirm.html?...`.
- Directly replaying `/login/confirm` requires care: browser flows may preserve encoded `emailkey` and session assumptions more strictly than naive script replays.

### IMAP/Gmail quirks
- Gmail folder names are locale-dependent. Useful folders include:
  - `INBOX`
  - `[Gmail]/All Mail`
  - `[Gmail]/Semua Email`
- Searching only one folder is brittle.
- Catch-all routing can make strict `TO` matching insufficient; fallback searches over unseen Webnovel mail help.

### Browser/mobile callback flow
- Mobile-web success HAR shows a callback path like:
  - `/id/login/callback?redirectUrl=...&ticket=...&userid=...`
- Browser-success behavior continues into authenticated user-state endpoints after that callback.
- That means `ticket` issuance is not the whole story; session finalization matters.

### Verification discipline
- If browser manual login rejects the password, or forgot-password says the account does not exist, treat the automation as still broken regardless of earlier green-looking responses.

## Suggested future debugging direction
- Compare browser-native register/confirm/login requests against script requests at parameter + cookie level.
- Prove success using the same exact fresh account across register, confirm, and login.
- Prefer browser HAR evidence over inferred endpoint behavior when they disagree.
