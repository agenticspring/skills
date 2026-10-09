---
name: self-hosted-streaming-web
description: Use when building or extending a keyless streaming web.
version: 1.0.0
author: spring
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [streaming, movie, vercel, nextjs, keyless, tvmaze, imdb, moviebox, self-host]
    related_skills: [cinematic-web-deployment, github-repo-management]
---

# Self-Hosted Streaming Web (keyless, Vercel-ready)

Use when Dez asks for a self-hosted movie/TV streaming site ("web film", "nonton tanpa iklan", "Netflix-style", "deploy ke Vercel sendiri") or to extend the existing **MovieBox** repo at `agenticspring/moviebox` (PRIVATE).

## Reference implementation

- Repo: `https://github.com/agenticspring/moviebox` (private, `agenticspring`)
- Stack: Next.js 15 App Router + React 19, hand-rolled CSS, zero UI frameworks, zero ad SDKs
- Structure: `app/api/{home,search,details,stream,stream-proxy,embed-proxy,resource,explore,subtitles,login}`, `lib/{metadata,tmdb,sources,vidlink,resources,keys}.js`, `middleware.js`, `app/{explore,login,play/adult}`, `components/{Nav,Hero,Row,BottomNav,ErrorBoundary}`
- Deploy: import to Vercel, **no env vars required** (TMDB key bundled in `lib/keys.js`; optional `SITE_PASSWORD` to override the login gate)
- UI theme: **Cinema Glass** — deep ink `#07070b`, violet→cyan→green gradient, glassmorphism, editorial split hero; deliberately NOT a Netflix clone (palette vars in `app/globals.css`)

## Core architecture

```text
metadata (TMDB primary + TVMaze/IMDb keyless fallback) → /api/* → frontend
playback chain (lib/sources.js resolveStream):
  1. vidlink (WASM token → direct m3u8/mp4, our hls.js player)
  2. resource stations (56 Chinese MacCMS api.php/provide/vod → direct m3u8)
  3. IDLIX (z2.idlixku.com Pentos gate → HLS + EN/ID subtitles; lib/idlix.js)
  4. 2embed via /api/embed-proxy (server-side ad-strip + shield, iframe)
  5. vidsrc-to / vidsrc-me (raw iframe fallback, has ads)
/ api/stream-proxy → re-serve HLS/segments (CORS + referer + AES key + ad filter)
```

- **TMDB primary metadata** (v3 key in `lib/keys.js`): home rows, search, details, external_ids (thetvdb for 2embed TV), network/genre discover for Explore.
- **vidlink direct** (`lib/vidlink.js` + `lib/vidlink/{script.js,fu.wasm}`): WASM boots in serverless, `getAdv(id)` → token → `vidlink.pro/api/b/{movie|tv}/{token}` → `stream.playlist` or best `stream.qualities` mp4. URLs are `cors-allowed` — play directly in `<video>`, no proxy needed. **WASM must be included in Vercel build**: `outputFileTracingIncludes: { '/api/vidlink': ['./lib/vidlink/**/*'], ... }` in `next.config.mjs`.
- **Chinese resource stations** (`lib/resources.js`): MacCMS pattern `GET {api}?ac=detail&wd=<query>` → list → `?ac=detail&ids=<id>` → `vod_play_url` ("第01集$url#第02集$url"). Movie + TV episode support. 22 adult stations kept separate (browse via `?adult=1`).
- **IDLIX Pentos resolver** (`lib/idlix.js`, deps `got-scraping` + `tough-cookie`): z2.idlixku.com is SELF-HOSTED (not a scraper) with a gate flow — CF cookie warmup → search `/api/search` → mediaId via `/api/movies/<slug>` (RSC-flight UUID regex catches cast-member keys, unreliable) → `/api/watch/play-info/{movie|episode}/{mediaId}` gives `{gateToken, unlockAt, serverNow}` (~15 s Pentos gate) → POST `/api/watch/session/claim` → POST redeemUrl → `{url: m3u8, subtitles:[{label,path}]}` from CDN `e2e.majorplay.net` (EN/ID vtt). Cache result 6 h in-module so repeat views skip the gate. First play of a new title ~16 s — it sits AFTER vidlink/resource for that reason. Full flow + pitfalls: `references/idlix-pentos-resolver.md` (in moviebox-streaming-web skill).
- **Embed ad-strip proxy** (`/api/embed-proxy` + `embedProxy()` in sources.js): server-fetch the embed page, strip `<script src>`/inline scripts/iframes matching AD_PATTERNS (tagivi, blackninja, llvpn, adsterra, popads, …), inject a shield that nulls `window.open` and blocks ad anchor clicks (shopee/play.google/tiktok/…). **Do NOT use `sandbox` on the iframe** — 2embed/vidsrc players refuse to play ("Sandbox not allowed") — proxy-strip instead.
- **Subtitles**: OpenSubtitles v1 legacy API keyless (search + `SubDownloadLink` download, srt→vtt). UI: custom `<div class="sub-overlay">` rendered from parsed cues (NOT `<track>`) with offset controls (−0.5s/−1s/+1s/+0.5s) for sync; default Indonesian first + auto-apply in direct mode.
- **Password gate**: `middleware.js` SHA-256 cookie `mb_auth` (30d httpOnly), `/login` page, `/api/login` POST. API routes stay open (video elements can't send httpOnly cookies cross-origin) — gate pages only.

## Verified keyless endpoints (tested 2026-08-01)

```bash
# TVMaze (works, no key)
curl "https://api.tvmaze.com/shows/1"                       # detail
curl "https://api.tvmaze.com/search/shows?q=breaking"        # search
curl "https://api.tvmaze.com/shows/1/episodes?specials=1"    # episodes
curl "https://api.tvmaze.com/schedule?country=US&date=YYYY-MM-DD"  # home row
curl "https://api.tvmaze.com/shows?page=0"                   # top-rated proxy

# IMDb suggestion (works, no key)
curl "https://v2.sg.media-imdb.com/suggestion/a/avatar.json" # → {d:[{id:"tt...",l,y,i:{imageUrl}}]}
```

IMDb suggestion is **query-based only** — no trending/popular endpoint. Use TVMaze top-rated as the hero/trending proxy. Movie details are thin (title/year/poster); there is no keyless synopsis source that worked from datacenter IP.

## Playback reality (critical)

- **Server-side m3u8 IS possible now** via (a) vidlink WASM resolver and (b) Chinese MacCMS resource stations — both return direct m3u8/mp4 that our own hls.js `<video>` plays. Prefer these (no iframe, no ads, subtitles attach).
- vidsrc.to/vidsrc.me redirect to JS-obfuscated players (vsembed.ru, cloudorchestranova) — **no m3u8 in server-fetched HTML**; only usable as raw iframe fallback.
- 2embed endpoints (`streamsrcs.2embed.cc/{xps,vnest,vcr,swish}`) return player shells requiring browser JS — no server-side m3u8; use `/api/embed-proxy` ad-stripped iframe instead.
- embed.su, autoembed, multiembed, embed5, embedb, eflix, playerx → dead/404.
- JustWatch / Consumet / api.movie-web.app / YTS / embed-api → dead or geoblocked from datacenter IP.
- **Direct-mode player needs hls.js** for m3u8 (native `<video>` only plays mp4/webm). `DirectPlayer` component: `new Hls({enableWorker:true})`, loadSource, attachMedia, destroy on cleanup.
- **ID mapping**: movies = TMDB id preferred (vidlink/resource/2embed all accept it); TV = TMDB id for vidlink, thetvdb for 2embed (`/tv/{id}/external_ids` → tvdb_id); resource stations search by TITLE (Chinese stations match English titles too, e.g. "spider-man").

## Pitfalls

1. **TMDB signup was blocked from datacenter IPs** (CloudFront 403 on POST
   `/signup`) in an early attempt — but on 2026-08-01 Dez supplied a working TMDB
   v3 key (via the settings page after registration), and MovieBox now runs TMDB
   as PRIMARY metadata with the keyless stack as automatic fallback. Rule: keep
   both layers; never treat "signup blocked" as "impossible forever". The key
   lives in `lib/keys.js` (private repo; TMDB keys are client-side-safe).
2. **Next.js nested route import depth** — `app/watch/[type]/[id]/page.js` and `app/api/details/[type]/[id]/route.js` are 4 levels deep; components need `../../../../` and lib needs `../../../../../`. A wrong `../` count fails the build — verify with a quick node script or the build error.
3. **HLS proxy must rewrite segment URLs** — `lib/sources.js` `proxyStream()` rewrites relative `.ts` URIs to absolute `/api/stream-proxy?...` URLs; without this, m3u8 playback fails on referer/CORS.
4. **Provider IDs**: movies use IMDb `tt...` ids (many providers accept them); TV uses TVMaze id. 2embed accepts `tt` for movies and `tmdb` params exist but need TMDB ids — prefer IMDb-id-friendly providers.
5. **Providers die/change** — treat `lib/sources.js` as a living list; when a source stops resolving, swap entries, don't rewrite the app.
6. **Repo is PRIVATE by user request** — never make it public; keys/creds (if ever added) must stay out of git (`.gitignore` covers `.env*`).
7. **GITHUB_TOKEN_2 = agenticspring** for repo ops; export it as GITHUB_TOKEN/GH_TOKEN before `gh repo create/push` (same dual-PAT pattern as X autoreg).
8. **Production-only React crash #31 "Objects are not valid as a React child"** — when `listProviders()` changed from `string[]` to `[{name,sandbox}]`, the watch page rendered `{p}` directly. Dev tolerates, prod build crashes with `Minified React error #31`. Fix: render `p.name`. Always reproduce on `next start` (prod), not just `next dev`, before pushing player/UI changes.
9. **hls.js + React `removeChild` crash** — `NotFoundError: removeChild: node is not a child` on play. Causes: `key={src}` on the `<video>` (React force-remount racing hls.js attachMedia), and fallback `setTimeout` firing after unmount. Fix: no `key` on video, guard `typeof window`, cancel pending timer in cleanup, `try/catch` hls.destroy + removeAttribute('src').
10. **Dynamic import needs `.js` extension in node ESM** — `await import('./vidlink')` fails at runtime ("Directory import ... not supported resolving ES modules") though webpack dev passes; use `./vidlink.js`. The failure is silent (caught) — it silently degraded to embed fallback.
11. **Do NOT sandbox provider iframes** — "Sandbox not allowed. Remove sandbox from the iframe to play." comes from vidsrc/vsembed/cloudnestra when `sandbox` attr present. Strip ads via server-side embed-proxy instead (works for 2embed; vidsrc needs full access).
12. **Playlist rewrite must also proxy `#EXT-X-KEY:URI`** — Chinese resource stations use AES-128; if the key URI stays relative/cross-origin, decrypt fails. `rewriteM3u8()` absolutizes + proxies key, segments, AND applies AD_SEGMENT_RE filter (`/ad|gg|guanggao|logo|maoyan.../i`) with `#EXT-X-DISCONTINUITY` on drop. **Also proxy `#EXT-X-MEDIA:URI` (audio/subtitle tracks in shaka-packager master playlists, e.g. IDLIX majorplay CDN) and `#EXT-X-MAP:URI`** — same URI-rewrite rule. `#EXT-X-STREAM-INF:` header lines stay raw; the variant URI line below them is rewritten as a normal segment line.
13. **`useSearchParams` needs `<Suspense>` wrapper** in Next 15 client pages — `/explore` prerender failed without it ("Export encountered an error"). Wrap the component that calls it.
14. **Password gate + streaming**: gate pages via middleware cookie, but leave `/api/*` open — video elements with `crossOrigin="anonymous"` won't send httpOnly cookies, so locked APIs break playback. Also `/login` itself and `_next` static must stay public.
15. **Resource-station ad-strip PHP pattern** (from NodeLoc thread 31379) is the model for our `rewriteM3u8`: fetch playlist → split segments → drop ad segments → cache. Chinese sliced CDNs (ffzy/量子/暴风/快看) embed ad segments by name pattern.
16. **Network/forum source research**: NodeLoc is Discourse → `https://www.nodeloc.com/search/query.json?term=<urlencoded>` works keyless; NodeSeek is Cloudflare-managed-challenge (Capsolver `AntiCloudflareTask` + sticky proxy + Windows Chrome UA solves it, IP-bound `cf_clearance`) — but mirror `nodeseek.cc` is CF-free for browse/search.json on recent content. Best yields: search MacCMS resource-station API lists (MoonTVPlus thread had 121 station URLs).

## Workflow

1. Check `agenticspring/moviebox` exists (gh repo view) before creating anything.
2. `npm run build` locally until green BEFORE pushing.
3. Push via git with `agenticspring` identity; verify `git ls-remote` HEAD + repo visibility.
4. Tell Dez: no env vars needed on Vercel; import + deploy only.
5. Honesty rule: metadata sources are verified working; playback providers are best-effort and change — say so plainly.

## References

- `references/streaming-provider-notes.md` — provider probe results, dead ends, and ID conventions (append as providers change).
- `references/resource-stations-and-source-hunting.md` — Chinese MacCMS resource-station mechanics, ad-strip/AES proxy patterns, OpenSubtitles keyless API, and how to reverse a streaming site's source (LokLok/NetPop, IDLIX/Pentos, forum research).
- `references/streaming-code-review-security.md` — review checklist for Next.js streaming diffs: SSRF/open-fetch through media proxies, unsandboxed same-origin embed proxy risks, subtitle parsing/iframe UI pitfalls, and open-access removal checks.
