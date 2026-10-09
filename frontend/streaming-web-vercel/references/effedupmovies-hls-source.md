# EffedUpMovies (effedupmovies.com) as a native-HLS video source

Validated 2026-08-05 on `https://www.effedupmovies.com/ma-mere-2004/`
(title served: "Ma Mere Uncut Full Movie Watch Online HD Eng subs My Mother").

## Page structure

Each movie page contains a single `<video>` with a direct HLS source:

```html
<source src="https://s2.vvvv.effedupmovies.com/hls/v2/mamere/index.m3u8">
```

Extract from the page HTML:

```js
const m = html.match(/https?:\/\/[^"' ]+\.m3u8[^"' ]*/i);
const manifest = m[0].replace(/&amp;/g, '&');
```

## Playlist shape — SINGLE-FILE HLS, no variants

The master is a single-quality playlist, not a multi-variant master:

```m3u8
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:15
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:12.846167,
index0.ts
#EXTINF:7.340667,
index1.ts
...
```

- 1044 segments for Ma mère (~2h film).
- Segment names are RELATIVE to the m3u8 directory:
  `https://s2.vvvv.effedupmovies.com/hls/v2/mamere/index0.ts`.
- PITFALL: joining a relative segment to the CDN ROOT
  (`base + '/' + line`) gives `.../effedupmovies.com/index0.ts` → HTTP 404.
  Resolve relative to the playlist path via `new URL(line, m3u8Url).href`.
- PITFALL: do not treat the first non-`#` line as a "variant" and probe it as
  a playlist — there are no variants here (that's what the OK.ru resolver does,
  but EUM master is already the playable level).

## CORS / why a proxy

- Master response headers: `content-type: application/vnd.apple.mpegurl`,
  `access-control-allow-origin: https://www.effedupmovies.com` (origin-LOCKED),
  `accept-ranges: bytes`, `cache-control: no-store...`.
- Segment range requests work (HTTP 206) but no permissive CORS → a browser on
  `springmovie.vercel.app` cannot fetch master or segments directly.
- Proxy everything through `/api/eum`:
  - mode `?u=<page url>`: validate against `^https?:\/\/(www\.)?effedupmovies\.com\/`,
    fetch page, extract m3u8, return `{success, streamUrl: '/api/eum?url=' + encodeURIComponent(manifest)}`.
  - mode `?url=<abs>`: host allowlist `(^|\.)effedupmovies\.com$` (SSRF guard);
    if body matches `#EXTM3U|#EXT-X` → rewrite every non-`#` line to
    `/api/eum?url=<absolute>` and serve `application/vnd.apple.mpegurl`
    (`Cache-Control: no-store`); else treat as segment → `video/mp2t`,
    `Cache-Control: private, max-age=3600`, cap size (~40MB).
  - All upstream fetches send `User-Agent` + `Referer: https://www.effedupmovies.com/`.

## Frontend wiring (SpringMovie SPA)

Mirror the OK.ru row in `#player-error`:

```html
<input id="eumInput" class="sel" type="text" placeholder="Tempel link EffedUpMovies (https://www.effedupmovies.com/...)" />
<button class="btn btn-ghost btn-sm" onclick="playEum()">Putar dari EffedUpMovies</button>
<span id="eumMsg" class="sub"></span>
```

`playEum()` mirrors `playOkru()`: `fetch('/api/eum?u=' + encodeURIComponent(u))`
→ on success replace `_sources` with `{ name: 'EffedUpMovies', streamUrl: d.streamUrl, subtitles: [] }`,
`_sourceIdx = 0`, show player area, `_playSource(0)`; on failure write to `eumMsg`.

## Dev-server routing

`tools/dev-server.mjs` keeps a STATIC route map loaded at startup — adding a
new `api/*.js` route requires editing the map AND restarting the server
(otherwise the new path 404s until restart).

## Verification chain

```txt
/api/eum?u=<page>        → 200 {success:true, streamUrl:/api/eum?url=...}
/api/eum?url=<m3u8>      → 200 application/vnd.apple.mpegurl, all 1044 segments rewritten
/api/eum?url=<seg>       → 200 video/mp2t, first byte 0x47 (MPEG-TS sync)
```
