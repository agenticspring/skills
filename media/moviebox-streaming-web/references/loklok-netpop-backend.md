# Streaming-site backend analysis: loklok.fun / loklok.tv → NetPop / RR.TV

Analyzed 2026-08-01 when Dez asked "website ini dapat darimana source nya" for
`https://www.loklok.fun/` and `https://www.loklok.tv/`. These are NOT the same
app and NOT a new source class — both frontends sit on the **NetPop / RR.TV**
backend family, which is the SAME backend family as the RR domains Dez already
uses for webnovel (orangkaya.cyou / anakbaik.cyou / ejhitam.my.id — see memory).
So before treating any LokLok-like site as a fresh provider, check for the
NetPop/RR.TV fingerprints below.

## loklok.fun (Nuxt frontend, "LOKLOK" brand)

```text
Frontend: Nuxt 3 SPA, assets on CDN  https://js1.loklok.media/loklok-pc/prod/<ver>/_nuxt/*
          (grep HTML for _nuxt chunk URLs)
API base: https://api.loklok.fun        (Spring Boot — JSON 404 bodies with
          "timestamp" field prove the backend is alive)
Images:   img.loklok.media
```

## loklok.tv (Vue 2 + "Ironman" template clone)

```text
Frontend: Vue 2 + template "Ironman" from dutun.cc
          bundle: https://js1.dutun.cc/ironman-pc/1.3.4/<hash>.js  (1.9MB, grep-able)
API base: https://web-api.netpop.app/cms/web/pc/...     (LIVE)
          legacy alias seen in bundle: alpha-web-api.rr.tv, alpha-web-api.netpop.app
          other hosts in bundle: h5-api.hehekang.com, h5.loklok.space,
          img.loklok.video, img.netpop.app/cover/...
Images:   img.netpop.app/cover/<yyyyMMdd>/<ts>_<rand>.jpg
```

## Backend identity: NetPop = RR.TV

```text
web-api.netpop.app resolves to Huawei Cloud IP (119.8.166.167) — geo-blocked /
timeout from non-CN curl, but the frontend calls it fine in a normal browser
(so use browser network capture, not curl, to see live calls).
img.netpop.app + web-api.netpop.app + alpha-web-api.rr.tv = one platform.
RR.TV family == the RR domains used for webnovel ops in this environment.
```

## API endpoints found (from Ironman bundle, `"/cms/web/pc/..."` strings)

```text
GET  /cms/web/pc/search/list          (search suggestions / placeholder)
POST /cms/web/pc/search/search        (real search, body {searchKey,page,size})
GET  /cms/web/pc/album/detail         (params {id,page,size}) — film detail
GET  /cms/web/pc/download/urls        (params e) — THE video-source endpoint
GET  /cms/web/pc/news/list, /cms/web/pc/news/detail
GET  /cms/web/pc/article/detail
```

Probe results: `/home` etc. → 404 (Spring Boot, wrong path); `/cms/web/pc/home`
and `/cms/web/pc/search/list` → `403 {"code":"B0001","msg":"timestamp empty."}`,
then with `currentTime` header → `403 ... "aesKey empty"`. So the gate is:
**`currentTime` header + `sign` header + `aesKey` header**, all required.

## Anti-bot signing (from Ironman bundle, reversible but heavy)

```text
Request interceptor adds headers:
  currentTime = Date.now()          (ms)
  sign        = fl(method==='post' ? data : params, uuid, currentTime)
  aesKey      = pl(app) = TuringFront.Clouse(store.state.app.uuid)

fl() algorithm (deobfuscated from `function fl(){...}`):
  raw = String(currentTime) + stableStringify(data/params)
  enc = AES_encrypt(raw, uuid)               // cl.a.encrypt
  b64 = base64url(enc)  (replace '+'->'-', '/'->'_', drop padding)
  return MD5(b64)                            // cl.a.getMd5

So: sign = md5( base64url( aes_encrypt( ts + json, uuid ) ) ).
Clouse() is a Turing-obfuscated frontend function — extracting uuid+aesKey
server-side means running/replicating the obfuscated JS (headless browser or
full JS reimplementation). Feasible but fragile; Turing code can rotate.
```

## Scraping vs self-host — conclusion (Dez asked 2026-08-01)

**LokLok is SELF-HOSTED, NOT a scraper.** Evidence chain (when Dez asked
"Loklok dia scraping juga ga? Atau di upload ke player mereka sendiri"):

```text
1. Own backend API (Spring Boot) with a dedicated endpoint
   /cms/web/pc/download/urls that RETURNS video URLs — a scraper would just
   point at another site's iframe; they serve URLs from their own stack.
2. Own CDN for imagery (img.netpop.app / img.loklok.video) and the video
   CDN behind download/urls — content is encoded/hosted on their infra.
3. Serious anti-bot (currentTime+sign+aesKey, Turing Clouse obfuscation) —
   you protect an ASSET you own; scrapers don't usually bolt on Turing.
4. NetPop is a real streaming company (licensed Asian content: K-drama,
   anime, variety) — upload-and-serve model, not aggregator model.
```

Contrast with MovieBox's own chain: metadata from TMDB, VIDEO from third-party
providers (vidlink / MacCMS stations / embed iframes) — we ARE the scraper.
LokLok being self-hosted + Turing-gated is why it's a high-maintenance source;
vidlink/MacCMS remain the practical providers.

## Practical takeaways for MovieBox / scraping this class

1. **Check identity before integrating**: grep the frontend bundle for
   `web-api.netpop.app | alpha-web-api.rr.tv | netpop | img.netpop.app`.
   If present → it's NetPop/RR.TV; weigh whether you already cover that content
   (this environment's RR webnovel ops use the same family, but that is accounts,
   not video streams — no overlap in practice for movie sources).
2. **Don't burn time on curl probes**: the API needs currentTime+sign+aesKey;
   all three are mandatory (403 with distinct messages proves each gate).
   Use a browser to capture a real signed request if you want the exact payload
   shape; or route through a headless browser to mint aesKey+uuid.
3. **Endpoint value**: `/cms/web/pc/download/urls` is the key one for m3u8
   extraction; `/album/detail` for metadata. If ever unlocked, they'd slot into
   the provider chain like the MacCMS resource stations — but the Turing signing
   makes this a much higher-maintenance provider than vidlink or MacCMS.
4. **Frontend fingerprints for "LokLok-like" sites**: Nuxt+`api.loklok.fun`
   (official) vs Vue2+Ironman+dutun bundle (clone). Both are cosmetic shells;
   the source of truth is the backend host.
