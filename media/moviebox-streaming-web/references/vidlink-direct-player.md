# Vidlink direct player (MovieBox hybrid Option A)

Source repo studied: `github.com/4texas4/movie-scraper` ("Zenith Movies",
35 stars/76 forks, vidlink.pro pattern, "Ad-Free Scraper"). Dez chose Option A:
vidlink direct FIRST, embed iframe fallback. Added 2026-08-01.

## Files in /root/moviebox

```text
lib/vidlink.js            — ESM wrapper: WASM singleton boot + getAdv + vidlink API
lib/vidlink/script.js     — Go WASM runtime shim (eval'd; defines globalThis.Dm)
lib/vidlink/fu.wasm       — 2.4MB WASM token generator
app/api/vidlink/route.js  — GET ?id=<tmdb>&type=movie|tv&season=&episode= -> {url}
hls.js                    — npm dep (^1.6.x)
components/ErrorBoundary.js — wraps layout children (see main SKILL pitfall 13)
```

## resolveVidlink(id, season, episode)

1. Boot WASM once (module-level singleton `bootPromise`):
   - `globalThis.window = globalThis; self = globalThis`
   - stub `document = {createElement:()=>({}), body:{appendChild:()=>{}}}`
   - fake `location` (protocol https, host vidlink.pro) — missing it throws
     `Cannot destructure property 'protocol' of 'window.location'`
   - `require('libsodium-wrappers')` → `await sodium.ready` → `globalThis.sodium`
   - `eval(fs.readFileSync('lib/vidlink/script.js'))`
   - `const go = new (globalThis.Go || globalThis.Dm)()` — script uses `Dm`
   - `WebAssembly.instantiate(wasmBuf, go.importObject)` → `go.run(instance)`
   - wait ~500ms → `typeof globalThis.getAdv === 'function'`
2. `token = getAdv(String(id))` (72 chars, base64-ish; all-A's prefix is normal)
3. `https://vidlink.pro/api/b/movie/{token}?multiLang=0`  (TV:
   `.../b/tv/{token}/{season}/{episode}?multiLang=0`)
   headers: Referer/Origin `https://vidlink.pro/`, UA Chrome 124
4. Response: `{sourceId:"mwVault", stream:{qualities:{360,480,720,1080:{type:"mp4",
   url, codecName, size, linkType:2, requiresProxy:true, headers:{}}},
   flags:["cors-allowed"], TTL:3600, deliveryType:"file", captions:[]}}`
   - NO `stream.playlist` for mwVault — pick best quality key (sort numeric desc)
   - `flags:["cors-allowed"]` → browser can fetch mp4 directly; do NOT proxy
   - `requiresProxy:true` means the CDN wants a referer, but direct fetch still
     works in the browser when the URL is fresh (CORS allowed)

## Watch page wiring

- `loadStream` sends `force: idx === 0 ? '' : 'embed'` — provider 0 is "auto"
  (vidlink first), higher indices force embed providers.
- `resolveStream` (sources.js) tries vidlink first when `force !== 'embed' && tmdb`,
  returns `{mode:'direct', provider:'vidlink', url, referer:'https://vidlink.pro/'}`.
- `<DirectPlayer>` component: hls.js for `.m3u8`, native video for `.mp4`;
  `onError`/fatal HLS error → `onFallback()` → parent calls
  `loadStream(activeSeason, activeEp, 1)` (embed provider). 800ms delay + "switch
  ke provider cadangan…" message before switching.

## Verified behavior (2026-08-01)

- `resolveVidlink('969681')` → mp4 1080 from `bcdn.hakunaymatata.com` (spider-man)
- Standalone `next start` prod build: watch page rendered OUR video element
  (not iframe) for vidlink mode; on 429/expired URL the auto-fallback switched to
  the 2embed iframe automatically.
- bcdn 429s datacenter IPs aggressively after repeated tests — a 429 in test env
  does NOT mean the user (residential IP) will fail. Auto-fallback is the safety.

## Pitfalls

- URL `sign`/`t` params expire (TTL 3600s); vidlink may return a stale URL that is
  already 429 by load time. Re-resolve fresh right before playback; never cache.
- Do not stream direct URLs through `/api/stream-proxy` by default — `cors-allowed`
  makes direct browser fetch cleaner and avoids double-proxy + extra rate limits.
- Vercel: `outputFileTracingIncludes: {'/api/vidlink': ['./lib/vidlink/**/*'],
  '/api/stream': [...], '/api/embed-proxy': [...]}` in next.config.mjs; runtime
  `nodejs` on all three routes.
- WASM files 2.4MB — keep out of client bundles; only server routes read them.
- vidlink.pro is a third-party API that can change scheme or block. If `getAdv`
  breaks, re-sync fu.wasm/script.js from 4texas4/movie-scraper or drop to embed.
