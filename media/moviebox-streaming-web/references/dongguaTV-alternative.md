# DongguaTV (E视界) - Alternative Streaming Web

**Repo**: https://github.com/agenticspring/dongguaTV (PRIVATE)

## What it is
Full streaming web app (Node.js + Express + Vue 3), NOT just an API. More feature-complete than MovieBox but requires manual MacCMS API configuration.

## Key Features (vs MovieBox)
- Real-time SSE search (results stream in)
- Built-in IPTV (~1800 channels)
- Auto speed test + failover
- Edge ad removal via Cloudflare Workers
- Multi-user with cloud sync

## Deployment to Vercel
1. Import repo in Vercel
2. Add env vars:
   - `TMDB_API_KEY` = 56ebc0698d…05ab (bundled)
   - `CACHE_TYPE` = memory (for serverless)
3. Deploy - MacCMS sources already included (56 stations)

## This Session's Work (2026-08-04)
- **Created repo**: https://github.com/agenticspring/dongguaTV (PRIVATE)
- **Added TMDB key**: 56ebc0698d…05ab (same as MovieBox)
- **Added 56 MacCMS sources**: db.json with stations from MovieBox's resource.js
- **Config**: CACHE_TYPE=memory for Vercel deployment

## Why DongguaTV Needs Manual Sources (compared to MovieBox)
Unlike MovieBox which has built-in vidlink (WASM token resolver) that fetches streams server-side, DongguaTV relies entirely on MacCMS APIs. The JavaScript that generates video URLs runs in the browser.

**MovieBox advantage**: Built-in vidlink provides direct m3u8 URLs without needing provider config.
**DongguaTV advantage**: More mature features (live TV, speed test, auto-failover), better ad removal via Cloudflare Workers edge.

## When to Use DongguaTV
- If you want live TV/IPTV (1800+ channels)
- If you have your own MacCMS sources
- If you prefer the Vue 3 + Express stack

## When to Use MovieBox
- If you want zero-config (vidlink works out of the box)
- If you want subtitle support (OpenSubtitles)
- If you want Indonesian UI