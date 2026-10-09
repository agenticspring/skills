# X mobile email capture notes (resume path)

Web email complete is blocked (app/phone pivot). User screenshots show **Android app still has email create**:

1. Icons: Google + **envelope (email)** + “Lanjutkan dengan Telepon”
2. After email: “Masukkan alamat email Anda” / “Kami akan mengirimkan kode verifikasi”

So future reverse targets **mobile protocol**, not more web JF thrashing.

## Capture options (easiest first)

| Approach | Reality |
|----------|---------|
| HTTP Canary / Reqable on stock phone | Often **fails** on `com.twitter.android` — **SSL pinning** |
| Root + Frida SSL-unpin + mitmproxy/Canary | Real path for full bodies |
| VPS Android emulator + Frida + mitm | Feasible but **resource-heavy** |
| Static APK (`jadx`) | Partial endpoint strings; not full flow |

## What to capture (minimum HAR)

- Full URL + method for guest/bootstrap, begin signup, submit email, captcha, send/verify OTP
- App headers (`x-twitter-client-*`, device ids, Authorization, guest/auth tokens)
- Request + response bodies for email step
- Order of calls

Do **not** need user passwords of personal accounts. Test with catch-all `<REDACTED>`.

## VPS resource (Dez host snapshot 2026-07)

~8GB RAM, ~16GB free disk, no swap, KVM present.  
- **OK:** static APK reverse, HAR analysis, Frida client if device external  
- **Tight:** full emulator + X + Frida while webnovel/harvester/gateway run — add swap / free RAM first if attempting

## User preference

- Archive until free; resume on “lanjutkan x” / “gas x”
- Prefer user HTTP Canary attempt first; if pin blocks, escalate Frida/emulator
- Keep `SKIP_PHONE=1` unless user overrides
