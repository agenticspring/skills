# Provider endpoint notes (tested 2026-08-01)

All tests used `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) ... Chrome/124.0`.
Playback IDs: movies = IMDb `tt...`; TV = `thetvdb` for 2embed, `tt` for vidsrc.

## 2embed (preferred — reliable, no X-Frame-Options)

```text
Movie: https://www.2embed.cc/embed/{tt}          -> 200, player page
TV:    https://www.2embed.cc/embedtv/{thetvdb}/{s}/{e}  -> 200, player page
```

- Movie with `tt` verified OK (Avatar `tt0499549` → 9305-byte player page).
- TV with `tt` returns "error" in player — must use thetvdb id
  (Breaking Bad thetvdb=81189 → `/embedtv/81189/1/1` OK).
- Player sources are JS-generated:
  `streamsrcs.2embed.cc/{xps,xps-tv,vnest,vnest-tv,vcr,vcr-tv}` and
  `streamsrcs.2embed.cc/swish?id=<token>&ref=mdrct` (token from embed page).
  `xps?imdb=` exists for movies. No server-side m3u8 without running JS.

## vidsrc.to

```text
Movie: https://vidsrc.to/embed/movie/{tt}   -> 200 -> iframe vsembed.ru/embed/movie/{tt}/
TV:    https://vidsrc.to/embed/tv/{tt}/{s}/{e}
```

- Embed page = thin iframe shell → `https://vsembed.ru/embed/...` (obfuscated JS,
  `sbx.js`, `sources.js`, Cloudflare challenge). Direct m3u8 extraction fails.
- Page contains ad-script injection `llvpn.com/tag.min.js` — the classic
  false-positive for loose `findStream` regex.

## vidsrc.me

```text
Movie: https://vidsrc.me/embed/{tt}  -> 301 -> vidsrcme.ru/embed/{tt} (JS player)
TV:    https://vidsrc.me/embed/{tt}/{s}/{e}
```

- Redirects to `vidsrcme.ru`; JS-heavy (cloudorchestranova iframe, base64). Same story.

## Dead / unreliable (as of check)

```text
api.consumet.org + mirrors (consumet-api-rho.vercel.app, consumet-api-7xmp.onrender.com)  -> down
api.movie-web.app                                 -> down
vidlink.pro/api                                   -> down
embed.su                                          -> timeout
api.embedapi.cc                                   -> HTTP 000
yts.mx                                            -> DNS fail
apis.justwatch.com (popular/search)               -> 404 from this host
embed5.cc / embed2.cc / eflix.cc / player.vidsrc.xyz -> dead
multiembed.mov                                    -> 404
```

## What works keyless for metadata (verified)

```text
TVMaze:
  /shows/{id}?embed[]=episodes    -> full TV detail incl externals.imdb/thetvdb
  /search/shows?q=                -> TV search
  /schedule?country=US&date=      -> on-air rows
  /shows?page=N                   -> browse; sort by rating.average for top-rated

IMDb suggestion (search):
  https://v2.sg.media-imdb.com/suggestion/{first-letter}/{query}.json
  -> { d: [ { id: "tt...", l: title, y: year, i: { imageUrl } } ] }
  Also works when querying the tt id itself (movie detail fallback, thin).
```

## LK21-style sites (the "subtitle langsung ada" reference)

Indonesian streaming sites (lk21official.cc / lk21online.mom / wgfilm21.net) are
Cloudflare-blocked to datacenter IPs and reader proxies (curl → 403/1005,
r.jina.ai → 404, Wayback → empty). Their architecture is public via the
`febriadj/lk21-api` repo:

```text
GET {LK21_URL}/{movieId}  -> HTML with div#load-sources > ul > li
  each li: <a> provider name + href = embed URL, <span> resolutions
```

- They scrape the LK21 page for a **list of embed servers** (usually vidsrc.to /
  vsembed variants) and iframe the chosen one.
- Their "subtitle langsung muncul" is the **provider player's own CC button**,
  NOT a separate subtitle file. vidsrc.to → vsembed player has a CC menu; that is
  the whole trick. MovieBox already mirrors this: vidsrc-to first + "Open Player ↗"
  + a CC hint overlay on the embed.
- vsembed `data-hash` is nested/obfuscated (double base64 → AES in JS); not
  worth reversing server-side. No provider query param (`?lang=`, `?sub=`) forces
  CC — sizes unchanged. Just surface the player CC.

## Lessons

- Never let `findStream` return non-video URLs. Strict extension whitelist only.
- The reliable default is embed iframe (`force=embed`), direct only when a real
  m3u8/mp4 is found.
- Provider pages rotate; when a title fails on all, edit `lib/sources.js`
  EMBED_PROVIDERS (keep 2embed first — best tt/thetvdb support).
