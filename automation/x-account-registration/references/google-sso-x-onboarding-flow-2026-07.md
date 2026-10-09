# Google SSO Signup → X Onboarding Flow (2026-07-26)

## Summary
Google SSO signup for X (Twitter) works through the web Join Flow. The flow reaches onboarding but hits a **phone gate** before account creation completes. Avoid if user has `SKIP_PHONE` policy.

## Full Verified Flow
1. `https://x.com/i/flow/signup` redirects to `https://x.com/i/jf/onboarding/web?mode=signup`
2. Cookie banner (Indonesian locale): "Terima semua kuki"
3. Click: "Google" button
4. Popup: `accounts.google.com/v3/signin/identifier` with OAuth params for X
5. Enter email, Next → Enter password, Next
6. If first-time Workspace login: speedbump page "Welcome to your new Google Workspace for Education account" → click "I understand" / "Saya memahami"
7. OAuth consent: "Lanjutkan" (Indonesian button text — NOT English "Continue")
8. Google popup closes, redirects back to X via `accounts.google.com/gsi/transform`
9. X onboarding modal appears with URL hash changing through steps

## Onboarding Steps (in order)
1. **signup_dob**: "Kapan ulang tahun anda?" — select valid adult DOB (e.g. 12 Juni 1998)
2. **discoverability_gate**: "Hubungkan dengan teman yang Anda kenal" — click "Tidak sekarang"  
   *Trap: cookie banner can cover the button area; accept cookies first*
3. **Phone gate**: "Masukkan nomor telepon Anda" — this is the terminal block

## Key Technical Details

### DOM State After Redirect
After Google popup closes, the main X page URL changes to hash-based step indicators:
```
https://x.com/i/jf/onboarding/web#/s/signup_dob/r-<random>
https://x.com/i/jf/onboarding/web#/s/discoverability_gate/r-<random>
```

### Cookie Detection
- `auth_token` + `ct0` cookies = account created
- Without these, account is NOT yet created

### Button Localization (Indonesian)
- "Terima semua kuki" = Accept all cookies
- "Berikutnya" = Next
- "Lanjutkan" = Continue
- "Tidak sekarang" = Not now
- "Saya memahami" = I Understand

## Pitfalls
- Cookie banner overlaps the discoverability gate buttons — **must** accept cookies first
- DOB modal uses `<select>` elements — use `select_option()` not fill
- Google consent page can have "Lanjutkan" (Indonesian) vs "Continue" (English) — check locale
- After Google password submit, popup may close quickly — poll context.pages for the X page
- `page.evaluate` on closed Google page crashes — always check `p.is_closed()` before accessing
- **Phone gate is terminal** for skip-phone policy — do not waste time past this point

## Tooling
- CloakBrowser + Playwright for non-headless automation under Xvfb
- Webshare proxies work for signup but may hit riskBlock on some hosts
- GSuite accounts (mangtoha.com) work for Google SSO
- Script path: `/root/x-autoreg/google_sso_x_finish.py`
