# IDLIX (z2.idlixku.com) — Pentos gate resolver notes

Investigated 2026-08-01. IDLIX is **self-hosted, not a scraper**: Next.js
frontend over its own API with a custom "Pentos" gate/claim/redeem flow returning
real HLS + subtitle tracks from CDN `e2e.majorplay.net`. Integrated into MovieBox
as provider layer 3 (lib/idlix.js, commit e4a432c).

## Identity

```text
Frontend:  Next.js (RSC flight payloads), images from image.tmdb.org
API base:  https://z2.idlixku.com   (same API on z1.idlixku.com)
CDN video: e2e.majorplay.net/v/<id>/config-*.json  (shaka-packager HLS)
CDN subs:  e2e.majorplay.net/v/<id>/i18n/{en,id}/<hash>.vtt
```

Related public scraper: `Teramoto669/idlix-scraper` (Next.js REST API) — best
reference for the full flow; `annurdien/IDLIX-API`, `itsmeole/movie-api`,
`sandrocods/IdlixAPI` are simpler variants.

## Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/search?q=<q>&page=1` | GET | → `{results:[{id,slug,contentType:'movie'\|'tv_series',title,...}], total}` |
| `/api/movies/<slug>` | GET | → movie detail incl. `id` (mediaId) |
| `/api/series/<slug>` | GET | → series detail incl. `id`, seasons/episodes |
| `/api/watch/play-info/{movie\|episode}/{mediaId}` | GET | → `{gateToken, unlockAt, serverNow}` |
| `/api/watch/session/claim` | POST | body `{gateToken}` → `{redeemUrl, claim}` |
| `<redeemUrl>` | POST | body `{claim}` → `{url: m3u8, subtitles:[{label,path}]}` |

## Flow

1. `got-scraping` client + shared `CookieJar`; warm Cloudflare by GET `/`.
2. Resolve mediaId:
   - Search first (movie titles match, e.g. "The Furious 2026" → slug
     `the-furious-2026`). Search response is `{results,total}` — **NOT**
     `.data`/`.items`.
   - Page RSC flight regex: `self\.__next_f\.push\(\[\d+,\s*"(.*?)"\]\)` then
     unescape; UUIDs inside are mostly **cast-member li keys**, so the first
     UUID match is usually NOT the mediaId.
   - Reliable: `GET /api/movies/<slug>` → `id` IS the mediaId.
3. `play-info` → wait `unlockAt - serverNow` (Pentos gate, ~15 s).
4. `claim` → `redeem` → m3u8 + subtitles.
5. Cache result 6 h in-module (Map) to skip the gate on repeat views.

## Verification (2026-08-01)

```text
The Furious 2026 -> m3u8 at e2e.majorplay.net/v/z7/... (OK, ~16 s cold)
Obsession 2026   -> m3u8 + subtitles [English, Indonesian]
Subtitle vtt     -> 200, serves fine
Master playlist  -> shaka-packager; has EXT-X-MEDIA audio + subtitle tracks
```

## Pitfalls hit

- `resolveMediaId` first-UUID regex matched cast keys → "no mediaId found"; the
  `/api/movies/{slug}` fallback fixed it.
- `searchIdlix` returning 0 because response parsed as `.data`/`.items` — real
  key is `results`.
- URL `?t=` JWT expires; re-resolve, don't cache the raw URL beyond TTL.
- Master playlist EXT-X-MEDIA URIs must be proxied by rewriteM3u8 (audio/sub
  tracks), same as EXT-X-KEY/EXT-X-MAP; EXT-X-STREAM-INF header lines stay raw,
  the variant URI line below them is rewritten as a normal segment line.
- got-scraping is required for CF cookie warmup; plain fetch gets 403.

## Tradeoffs

- First play of a new title ~16 s (gate) — acceptable as layer 3 fallback, not a
  primary. Cache makes repeats instant.
- Site may change anti-bot (gate/sign) — then this provider silently fails and
  the chain falls through to embed proxy; keep it optional.
- Strong for Western + Indonesian content (unlike MacCMS which favors Chinese
  titles).
