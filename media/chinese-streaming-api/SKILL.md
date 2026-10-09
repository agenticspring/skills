---
name: chinese-streaming-api
description: Use when building Chinese film/streaming sites and APIs.
---

# Chinese Streaming API

Ecosystem for Chinese film/drama streaming sites. Two tiers: **metadata** (TMDB or MacCMS catalog) and **playback** (proxied m3u8 or signed streams).

## The MacCMS (苹果CMS) Ecosystem

The dominant backend for Chinese streaming sites. Resource sites ("资源站") expose a standard JSON API.

### Universal MacCMS API Format

```
GET https://<resource-site>/api.php/provide/vod
  ?ac=list          → paginated catalog
  ?ac=list&t=1      → filter by category ID
  ?ac=detail&ids=ID → detail + play URLs (vod_play_url)
  ?wd=keyword       → search
  &pg=N             → page number
```

Response fields: `vod_name`, `vod_pic`, `vod_play_url`, `vod_content`, `vod_year`, `vod_area`, `vod_remarks`

`vod_play_url` format: `Episode 1$http://...m3u8#Episode 2$http://...m3u8`

### Known Active Resource Sites (verified 2026-08)

| Key | Site | CDN Image Domain | Catalog Size | Notes |
|-----|------|-----------------|--------------|-------|
| dytt | dyttimage.com | `vod.dyttimage.com` | 22,000+ | 电影天堂, largest |
| ffzy | ffzy5.tv | `tupian.ffeiimg.com` | 19,800+ | 非凡资源 |
| ikun | ikun.im | `ynztctv.com` | 1,500+ | Vertical/portrait HD |
| uku | ukuapi88.com | `img.ukuapi88.com` | 9,300+ | Daily updates |
| subo | — | — | 35,000+ | Archive, full-file shape |

### CDN Domain Fingerprinting

When a streaming site proxies an upstream, image CDN domains in API responses reveal the actual backend, even when the API endpoint is a Vercel/CF proxy. More reliable than trying to identify the API domain directly.

```
img.netpop.app / img.despseek.com  → NetPop (iQIYI-based)
vod.dyttimage.com                  → dytt (电影天堂)
tupian.ffeiimg.com                 → ffzy (非凡资源)
img.ukuapi88.com                   → UKU API
ynztctv.com                        → ikun
```

## NetPop / iQIYI-Based (NXRStream pattern)

Used by sites like Nonthon's NXRStream tab. Authenticated/signed API — not publicly accessible without a valid token. Indicators:
- Images on `img.netpop.app` or `img.despseek.com`
- Response fields: `coverVerticalUrl`, `coverHorizontalUrl`, `definitionList` with codes like `GROOT_LD`, `GROOT_FD`
- Category: `0` = Movie, `1` = Series
- `sign error!` response means missing/invalid request signature

## TMDB (For Western Content)

Standard practice: TMDB for western film/series metadata, MacCMS for Chinese content.

```
Base: https://api.themoviedb.org/3
Key: ?api_key= or Authorization: Bearer

Common endpoints:
  /trending/all/week?language=id-ID
  /movie/popular?language=id-ID
  /tv/popular?language=id-ID
  /discover/movie?sort_by=primary_release_date.desc&vote_count.gte=1
  /search/movie?query=...
  /movie/{id}
  /tv/{id}/season/{season_number}
```

## Typical Site Architecture (Nonthon pattern)

```
Frontend (Vercel/CF Pages)
  ├── /api/login          → password gate (cookie: __Host-*_sess)
  ├── /api/dracin         → MacCMS proxy (action: list|detail|search|episode|fresh|sources)
  ├── /api/dracin-id      → Indonesian-localized source proxy
  ├── /api/dracin-img     → Image proxy (?u=encoded_url)
  ├── /api/nxrstream      → NetPop proxy (action: list|search|detail|media)
  └── Direct TMDB fetch   → from browser JS (key exposed in source)
```

## Recon Technique for Streaming Sites

1. **Login first** — many sites are password-gated; check JS for `/api/login` endpoint
2. **`performance.getEntriesByType('resource')`** — catches all fetch/XHR calls including exposed API keys
3. **Grep inline JS for keywords:** `nxrstream`, `dracin`, `maccms`, `MacCMS`, `GROOT_`, `vod_play_url`
4. **Hit `/api/dracin?action=sources`** — returns list of all resource site keys configured
5. **CDN domain in list response** → identify real upstream backend

## Pitfalls

- `execute_code` with `web_extract` inside the sandbox errors on `results` key — use `terminal` + `curl` directly for HTTP calls to authenticated sites
- NetPop sign errors are not transient — requests need a valid HMAC/signed token, cannot brute-force
- TMDB API keys are often exposed in client-side JS as `?api_key=` — always check `performance.getEntriesByType('resource')` first before digging deeper

## References

- `references/nonthon-api-map.md` — Full API map of nonthon.vercel.app (verified 2026-08)
