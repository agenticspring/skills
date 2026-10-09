# Streaming providers — URL/ID matrix, quirks, resolution flow

Verified 2026-08 against live endpoints. Providers change often; re-probe before
relying on any single one, and keep the switcher UI so users can fall back.

## Provider matrix

| Provider | Movie URL | TV URL | Best ID | Notes |
|---|---|---|---|---|
| 2embed | `https://www.2embed.cc/embed/{tmdb|tt}` | `https://www.2embed.cc/embedtv/{thetvdb|tmdb}/{s}/{e}` | movie: tmdb or tt; TV: thetvdb | Most reliable for both. `embedtv/tt...` errors — use thetvdb/tmdb for TV |
| vidsrc-to | `https://vidsrc.to/embed/movie/{tmdb|tt}` | `https://vidsrc.to/embed/tv/{tmdb|tt}/{s}/{e}` | tmdb | 200 page is an iframe wrapper to vsembed.ru; no X-Frame-Options block |
| vidsrc-me | `https://vidsrc.me/embed/{tmdb|tt}` | `https://vidsrc.me/embed/{tmdb|tt}/{s}/{e}` | tmdb | 301 → vidsrcme.ru; heavy ad scripts in page |

## Dead / unreliable (as of check)

```text
embed.su           (embed/movie/) — timeout
vidlink.pro API    — down
api.embedapi.cc    — down
Consumet public    — down (all mirrors)
JustWatch apis.justwatch.com — 404/blocked from VPS
IMDb chart scrape  — HTTP 202 bot wall
YTS api yts.mx     — DNS fail
```

## Stream resolution flow (server-side)

```text
1. build embed url per provider using ctx {tmdb, imdb, thetvdb, type, season, episode}
2. fetch page HTML (UA + referer)
3. findStream() — STRICT media filter:
   - /\.m3u8/ /\.mp4/ /\.webm/ /\.mkv/ /\.m4v/ (case-insensitive)
   - fallback file/src/url= only if isVideoUrl() passes
   - NEVER accept .js/.css/png — ad script false positive
4. if found -> mode 'direct' (play via /api/stream-proxy)
5. else -> mode 'embed' (iframe to provider embed page)
```

## The ad-script bug (real incident)

First version used `(?:file|src|url)\s*[:=]\s*["'](https?://[^"']+)` and matched
`s.src='https://llvpn.com/tag.min.js'` from vidsrc.to's inline ad script.
Result: player "played" a JS file, user saw dead video. Fix = isVideoUrl() gate
before accepting any fallback match. **This is the #1 stream-resolver bug.**

## ID sourcing

- TMDB detail: `imdb_id` available (e.g. Avatar `tt0499549`).
- TVMaze show: `externals.imdb`, `externals.thetvdb` (thetvdb id works with 2embed).
- Movies from IMDb suggestion API: `it.id` is already the tt id.
- Pass all three (tmdb, imdb, thetvdb) into the resolver; each provider picks
  its preferred one.

## HLS proxy rewrite

When proxying an m3u8 playlist, rewrite relative segment URIs so every `.ts`
goes back through `/api/stream-proxy?url=<abs>&ref=<referer>` — this defeats
referer/hotlink protection on CDNs.

## Subtitle parsing

```text
#EXT-X-MEDIA:TYPE=SUBTITLES,NAME="...",LANGUAGE="...",URI="..."
```
Resolve URI against playlist base URL, then proxy. SRT → VTT: add `WEBVTT` and
convert `hh:mm:ss,mmm` → `hh:mm:ss.mmm`.
