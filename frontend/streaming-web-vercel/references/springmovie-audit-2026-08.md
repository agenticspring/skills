# SpringMovie Audit 2026-08-24

Full audit: playback sources, subtitles, UI mobile/desktop. Fixes deployed (commit 0362c4f).

## Playback Source Matrix (verified live)

| Source | CDN | CORS | Datacenter IP | Status |
|---|---|---|---|---|
| modiplay servers (StreamHG, EarnVids, RPMShare, UpnShare, StreamP2P) | vibuxer/dramiyos via proxy.php | OK | CF blocks curl-default UA only; browser UA = 200 m3u8 | PLAYS (readyState 4, currentTime advancing) |
| Dracin ikun | bfikuncdn.com + kkzycdn.com:65 | open (*) | 200 | PLAYS native |
| Drama ID reelshort | crazymaplestudios.com | open | 200 | PLAYS native |
| Dracin dytt | vip.dytt-network.com / -broadcast.com | NO ACAO | 403 | BLOCKED everywhere via server; unfixable from Vercel |
| Dracin ffzy | vip.ffzy-play9.com / vod.feifei-online.com | NO ACAO | 403 | same as dytt |
| Dracin uku | ukzyvod3.ukubf5.com | HAS ACAO (+credentials) | 403 | plays on residential IPs; blocked on DC |
| subo | — | — | API returns empty list (upstream t=27 empty) | catalog dead upstream |
| SpringStream (LokLok) getPlayInfo | — | — | "Success" but no stream url | still broken upstream (catalog-only) |

## Fixes Shipped

1. New `/api/hls` relay in api/external.js: playlist+segment proxy with per-source host allowlist + referer, share-page → m3u8 extraction, rewriteToProxy for nested playlists. Rewrite added in vercel.json.
2. Dracin player dual-path: dytt/ffzy/uku try `/api/hls?url=…` first then direct URL fallback; ikun/reelshort stay native. Graceful error on total failure.

## Honest Limits

- dytt/ffzy unplayable through Vercel (CDN bans all datacenter IPs incl. Vercel's). Only fix = residential-proxy egress or different station with CORS-open media CDN.
- uku plays for residential users (CORS ok) — the new relay covers the rest partially.
- SpringStream playback depends on LokLok upstream; nothing to fix client-side.

## Subtitles — PASS
- /api/subs (Stremio OS addon): GoT S1E1 63 subs/29 langs incl. Indonesian
- /api/sub SRT→VTT conversion verified byte-level
- Frontend auto-pick ind→may→eng verified live

## UI — PASS
- Desktop clean, mobile CSS correct (bottomnav ≤920px, safe-area)
- Zero emoji repo-wide, JS syntax OK, all views render, search/pagination work

## MacCMS CDNs — CORS/IP Matrix (for future source additions)
ALWAYS verify before adding a station:
1. `curl -s -D -` check ACAO header on media m3u8
2. Test datacenter IP reachability
3. Both must pass for Vercel-hosted playback

Probed stations that failed: jisu (connection refused), lz/bfzy/mozhua/wolong (dead or share-page only).
