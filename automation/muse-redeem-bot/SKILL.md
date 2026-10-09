---
name: muse-redeem-bot
description: "Muse.ai (Meta) account bots + Meta auth/checkout recon."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Meta, Muse, Reverse-Engineering, HAR, CSRF, Playwright, Proxy, Account-Bot]
---

# Muse.ai (Meta) Account + Invite Redeem Bot

Bot bikin akun Muse (produk Meta) otomatis lalu redeem invite code.
Termasuk teknik reverse-engineering alur login/checkout Meta yang bisa dipakai ulang.

> ⚠️ **STATUS: metode per 2026-10-07 sudah MATI** (kode invite habis + kemungkinan
> Meta ganti alur). Skill ini disimpan untuk **teknik & pitfall-nya**, bukan
> sebagai jaminan alur masih jalan. **Selalu recon ulang sebelum dipakai lagi.**

## When to Use / Kapan dipakai
- Bikin bot akun untuk produk Meta (muse.ai atau serupa)
- Reverse-engineering alur login/OAuth/checkout Meta
- Baca HAR file buat nemu API tersembunyi
- Bot multi-akun yang butuh proxy rotation + auto-stop
- Situs dengan CSRF token/cookie yang harus direplikasi

## Struktur project (buat orang awam)
```
install.sh      install dependensi (playwright + chromium)
setup.sh        setup interaktif: kartu, kode, domain, app password, proxy
run.sh          <-- user cuma ketik ini, ditanya mau berapa kali
musebot_ui.py   engine UI (alur klik-klik)
musebot.py      engine hybrid (fase daftar via API)
config.env      data user (perm 600, JANGAN commit)
proxy.txt       daftar proxy, rotasi per nomor akun
```

## ALUR MUSE (7 tahap)
```
1. email          -> input + Continue         pel=login_contact_continue_click
2. kode 6 digit   -> dari email (IMAP)        pel=login_otp_confirm_click
3. nama + ultah   -> ADA 2 VARIAN:
     A) "Finish creating your account" = First/Last + bulan/tgl/tahun
     B) "What's your birthday?"        = cuma bulan/tgl/tahun
   pel=login_birthday_continue_click
4. DISCLOSURE WAJIB -> tombol "Get started"
   pel=onboarding_disclosure_continue_click
5. verifikasi umur -> CC / Instagram / Facebook
   pel=onboarding_confirm_age_click  (KADANG tanpa atribut ini -> cari by teks)
   CC buka TAB BARU ke auth.meta.com/payments/checkout
6. masuk app
7. REDEEM (via API, BUKAN UI):
   POST /api/hatch/invite-code/redeem
   body {"code":"XXX","supportsRedemptionStatus":true}
```

## API MUSE (hasil reverse-engineering)
```
POST /api/auth/native/restart              {}  -> {csrf_token, flow_state, tos}
POST /api/auth/native/send-otp             {"contact_point":"<email>","region":"US"}
POST /api/auth/native/confirm-otp          {"otp_code":"123456"}
POST /api/auth/native/register-completion  {"date_of_birth":"1980-01-01",
                                            "tos_content_version":"ntm_create_account:default_v1_meta_account_v2+docs_v1"}
     -> {redirect_to:"/access", auth_meta_session:{frl_access_token:"FRLA..."}}
POST /api/auth/save-account
POST /api/hatch/accept-tos                 {"disclosure_version":"HATCH_ROW_v0", ...}
GET  /api/hatch/invite                     -> {"invite_state":"ELIGIBLE",...}
POST /api/hatch/invite-code/redeem         {"code":"XXX","supportsRedemptionStatus":true}
POST /api/checkout/init                    {"amount":"1.00","currency":"USD",
                                            "sessionId":"upl_...","productId":"...","receiverId":"..."}
```

### CSRF (kunci utama)
```
header : x-hatch-csrf-token
nilai  : csrf_token dari response /restart
       = cookie hatch_native_auth_csrf DIPOTONG sebelum titik (".")
```
**Token BERGANTI tiap state berubah** -> baca ulang sebelum tiap call.
Cookie HttpOnly -> Playwright `context.cookies()` bisa baca.

### Bootstrap OIDC (wajib sebelum checkout kartu)
```
POST https://auth.meta.com/hatch/session/bootstrap/   form: frl_access_token=<dari register-completion>
  -> 302 -> GET https://auth.meta.com/oidc/callback/?code=...&state=...
```
Tanpa ini, popup kartu gagal: `auth.meta.com/?error=invalid_redirect`

### Cookie berubah setelah akun jadi
```
sebelum: hatch_native_auth_csrf (buat CSRF native auth)
sesudah: HILANG, muncul hatch_sess
```
Jadi `get_csrf()` balik KOSONG setelah akun jadi = NORMAL.
Redeem nggak butuh header CSRF, cukup cookie sesi.

## VERIFIKASI KARTU META (3 GraphQL mutation)
`POST https://auth.meta.com/api/graphql/`:
```
1. PaymentsCometGetServerEncryptionKeyMutation  doc_id 23994203586844376
   -> public key + trust_chain (X.509 Meta Payments Secure Tier)
2. useFBPayAccountMutation                      doc_id 27107429215520990
   -> SUBMIT KARTU: billing_address, credit_card_first_6/last_4/number,
      csc (semua sensitive_string_value), platform_trust_token (JWT)
3. useECPCometFinalizeCheckoutMutation          doc_id 28179730211626671
   -> charge 1.00 USD
```
**Browserless TIDAK realistis**: kartu ditransform client-side + wajib
`platform_trust_token` (device trust, terikat fingerprint) + param anti-CSRF
GraphQL (fb_dtsg/lsd/jazoest/dyn/csr).

## PITFALL (semua sudah ketemu)

### Playwright / UI
1. **Input OTP `class="sr-only"`** (hidden + overlay) -> `click()`/`fill()` GAGAL.
   Pakai JS `focus()` + `page.keyboard.type()`.
2. **Tombol tahap berikutnya di-render duluan (disabled)** -> `button[type=submit]`
   pertama bukan tombol aktif. Selalu target `[data-pel-click='...']`.
3. **Klik Confirm sering timeout** (React re-render) -> fallback JS `click()`.
4. **Select ultah pakai `label=`, bukan `value=`.**
5. **Varian form B default ultah = HARI INI** -> umur 0 tahun. WAJIB override.
6. **Tombol kadang TANPA `data-pel-click`** -> fallback cari by teks.
7. **Verifikasi di-skip** kalau halaman udah lanjut (jangan dianggap gagal).

### Proxy
8. Chromium: `proxy={"server":..., "username":..., "password":...}` TERPISAH.
   Kalau kredensial nempel di URL -> `ERR_TUNNEL_CONNECTION_FAILED`.
9. Chromium buka kebanyakan koneksi -> kena limit sesi proxy. Wajib:
   `--disable-http2 --disable-preconnect --disable-background-networking --disable-dns-prefetch`
10. Rotasi proxy pakai **NOMOR AKUN** (`n % len`), BUKAN index loop.
11. **Cek proxy hidup sebelum run** (`proxy_alive()`) + auto-ganti kalau tunnel gagal.
12. **RANGE IP MENENTUKAN**: sebagian range datacenter diblok Meta untuk API
    (403 Forbidden) padahal web+OTP jalan. Kalau semua akun 403 -> GANTI RANGE,
    jangan ngoprek kode.

### Sesi
13. **Onboarding WAJIB selesai**: kalau `/access/disclosure` belum diklik -> API
    app balas **403 Forbidden** (redeem gagal). Deteksi & klik dulu.
14. Sebelum API call penting: bootstrap app (`goto /access` + tunggu) biar cookie sesi kebuat.
15. Cek sesi: 401 = belum login (gagal), 403 = CSRF saja (JANGAN anggap gagal).

### Metadata / rate limit
16. **Kode invite ada KUOTA** (~10 dan ~30 di 2 contoh). Response:
    `{"success":false,"reason":"used_up"}` -> **STOP run**, jangan lanjut.
17. **OTP rate-limit per IP**. Gejala: `kode email nggak dateng` 200-400s.
    Pulih sendiri 2-4 jam. Banyak IP = banyak kuota.
18. **Redeem harus KONFIRMASI server**: hanya hitung sukses kalau
    `success:true` / `redemptionStatus:"redeemed"`. Retry kalau gagal.
19. Log bukti audit per akun (`redeemed_proof.txt`) — response mentah + timestamp.

## Teknik: baca HAR buat nemu API
```python
import json, urllib.parse
d = json.load(open("capture.har"))
for e in d["log"]["entries"]:
    u = e["request"]["url"]
    if "/api/" in u:
        hd = {h["name"].lower(): h["value"] for h in e["request"]["headers"]}
        print(e["request"]["method"], e["response"].get("status"), u[:120])
        print("  fn:", hd.get("x-fb-friendly-name"))     # nama GraphQL mutation
        pd = (e["request"].get("postData") or {}).get("text","")
        print("  body:", urllib.parse.parse_qs(pd))      # variables, doc_id
```
Yang dicari: endpoint tersembunyi, `doc_id` GraphQL, nama mutation, header khusus.

## Teknik: CSRF token
```python
async def get_csrf(ctx):
    for ck in await ctx.cookies():
        if ck.get("name") == "hatch_native_auth_csrf":
            return (ck.get("value") or "").split(".")[0]   # sebelum titik
    return None
```
Atau dari response `/restart`: `csrf_token`.

## Jalankan API di dalam browser (hindari CORS)
```python
await pg.evaluate("""async (a) => {
    const h = {'content-type':'application/json'};
    if (a.csrf) h['x-hatch-csrf-token'] = a.csrf;
    const r = await fetch(a.path, {method:'POST', credentials:'include', headers:h,
                                   body: JSON.stringify(a.body)});
    let t=''; try{t=await r.text();}catch(e){}
    let j=null; try{j=JSON.parse(t);}catch(e){}
    return {status:r.status, json:j, text:t.slice(0,300)};
}""", {"path": "/api/...", "body": {}, "csrf": csrf})
```

## Proteksi wajib (jangan dihapus)
1. Cek proxy hidup sebelum run -> 0 hidup = run DIBATALKAN
2. Auto-ganti proxy kalau tunnel gagal
3. Cek sesi (401 gagal / 403 lanjut)
4. Redeem via API dulu, UI fallback
5. `used_up` -> STOP RUN + notif
6. Verifikasi di-skip kalau halaman udah lanjut
7. Tombol dicari by atribut ATAU teks

## Hasil nyata (2026-10-07)
- **70 akun** berhasil redeem (3 kode: 10 + 30 + 30)
- Run terbesar: 24 akun -> **17/24 (71%)** dengan jeda 8-12s
- ~140-160s per akun (didominasi verifikasi kartu + settle)
- Redeem via API: ~2 detik (vs 300s+ klik UI & sering gagal)

## Pacing
| jeda | hasil |
|---|---|
| 70-140s | paling stabil |
| 30-60s | disarankan |
| 8-12s | cepat, verifikasi kartu sering gagal (~71%) |

## Keamanan
- HAR file mengandung JWT sesi, `fb_dtsg`, `platform_trust_token`, data kartu
  parsial -> JANGAN disebar.
- `config.env` perm 600 (isi CC + app password). JANGAN commit.
- Kartu cuma kena auth sementara $1 per akun.
