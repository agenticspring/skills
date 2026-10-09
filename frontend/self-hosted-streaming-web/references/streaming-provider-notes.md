# Streaming provider probe notes (2026-08-01)

Live probe results from MovieBox build. Providers change fast — re-probe before
relying on any single entry. These are the actual HTTP outcomes from a
datacenter IP (VPS).

## Direct-resolve attempts (server-fetched HTML, m3u8/mp4 regex)

| Provider | URL pattern | Result |
|---|---|---|
| vidsrc.to | `/embed/movie/{id}` | HTTP 200 shell → iframe to `vsembed.ru`; no m3u8 server-side |
| vsembed.ru | `/embed/movie/{id}/` | HTTP 200 player page, JS/obfuscated (`sbx.js`, `sources.js`, cloudflare challenge) — no m3u8 in HTML |
| vidsrc.me | `/embed/{id}` | 301 → `vidsrcme.ru`; same JS-obfuscated player |
| 2embed.cc | `/embed/{id}` | HTTP 200; contains `data-src="https://streamsrcs.2embed.cc/swish?id=...&ref=mdrct"` |
| streamsrcs.2embed.cc | `/xps?imdb=tt...`, `/vnest?tmdb=...`, `/vcr?tmdb=...`, `/swish?id=...` | Player shells; JS required, no server-side m3u8 |
| embed.su | `/embed/movie/{id}` | HTTP 000 / dead |
| autoembed.cc | `/embed/movie/{id}` | dead |
| multiembed.mov | `/directstream.php?video_id=` | 404 |
| embed5.cc / embed2.cc / eflix.cc / player.vidsrc.xyz | — | dead |

## Keyless metadata probes

| Source | Endpoint | Result |
|---|---|---|
| TVMaze | `api.tvmaze.com` | **WORKS** — search, detail, episodes, schedule, shows page. No key. |
| IMDb suggestion | `v2.sg.media-imdb.com/suggestion/{c}/{q}.json` | **WORKS** — returns `{d:[{id:"tt...", l, y, i:{imageUrl}, q}]}`. Query-only, no trending. |
| JustWatch | `apis.justwatch.com/content/titles/movie/popular` | 404 / blocked from datacenter IP |
| Consumet (all mirrors) | `api.consumet.org`, vercel/render mirrors | dead |
| movie-web backend | `api.movie-web.app` | dead |
| YTS | `yts.mx/api/v2/list_movies.json` | DNS fail |
| embed-api | `api.embedapi.cc` | dead |
| IMDb chart top | `www.imdb.com/chart/top/` | HTTP 202 bot-wall |

## Playback strategy that works (updated 2026-08-01)

1. **vidlink direct** (WASM resolver, `lib/vidlink.js`): real m3u8/mp4, play in own hls.js `<video>`.
2. **Chinese MacCMS resource stations** (`lib/resources.js`): `?ac=detail&wd=` → `vod_play_url` m3u8, proxied + ad-stripped.
3. **2embed via `/api/embed-proxy`**: server-side ad-strip + window.open shield, iframe. NO sandbox attr.
4. **vidsrc-to/vidsrc-me**: raw iframe fallback only (JS-obfuscated, has ads).
5. Keep `/api/stream-proxy` for HLS: fetch with referer + UA, rewrite relative `.ts`/key URIs to absolute proxied URLs, filter ad segments, return with CORS headers.

The old "direct resolve always fails → iframe is the only pattern" assumption is superseded: vidlink + resource stations prove server-side m3u8 works. The probe table above still documents what raw embed pages do NOT expose.

## ID conventions

- Movies: IMDb `tt...` — accepted by 2embed (`/embed/{tt}`), vidsrc accepts tt too.
- TV: TVMaze numeric id; TVMaze detail gives `externals.imdb` for cross-mapping.
- 2embed also has `tmdb=` params (`vnest`, `vcr`) but those need TMDB ids we no longer use.

## Home-row strategy without TMDB

- `On Air Today` = TVMaze schedule (region US, today's date).
- `Top Rated Series` = TVMaze `/shows?page=0` filtered + sorted by `rating.average`.
- Movies have no keyless trending source — either accept TV-first rows or use
  IMDb suggestion with curated queries. Don't claim a movie-trending source exists.
