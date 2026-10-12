---
name: moviebox-streaming-web
description: Build or debug MovieBox keyless streaming web.
version: 1.0.0
author: spring
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [moviebox, streaming, vercel, nextjs, keyless, tvmaze, imdb, provider-embed]
    related_skills: [cinematic-web-deployment, private-source-repository-release, github-multi-account-ops]
---

# MovieBox — keyless self-hosted streaming web (Vercel)

Use when Dez asks to build/fix/extend the private Netflix-style streaming app, add
features, debug playback ("play ga bisa"), or change providers.

## Where it lives

```text
Repo:      https://github.com/agenticspring/moviebox  (PRIVATE, Vercel-only)
Local:     /root/moviebox
Branch:    main
GH auth:   agenticspring (GITHUB_TOKEN_2 — dual-PAT pattern, never clobber primary)
```

Deploy: import repo in Vercel (Next.js auto-detect). **No env vars required** —
the TMDB key is bundled in `lib/keys.js` (repo is PRIVATE, and TMDB keys are
designed for client-side use). Optional override: `TMDB_API_KEY`,
`NEXT_PUBLIC_APP_NAME`.

## Architecture (TMDB primary + keyless fallback)

```text
Metadata:
  PRIMARY  -> TMDB v3 lib/tmdb.js (key bundled in lib/keys.js)
  FALLBACK -> TVMaze api.tvmaze.com + IMDb suggestion API (lib/metadata.js)
              used automatically when TMDB calls fail

Playback:
  /api/stream -> resolveStream() tries vidlink DIRECT first (best: ad-free +
                 subtitles attach to OUR player), then Chinese MacCMS resource
                 station (direct m3u8), then IDLIX (Pentos HLS + EN/ID subs),
                 then embed iframe fallback
  /api/vidlink -> WASM token resolver + vidlink.pro API -> real m3u8/mp4 URL
  /api/resource -> MacCMS resource-station search/resolve (56 stations, see
                 "Resource-station resolver" section below) + ADULT mode
                 (?adult=1: list/browse/search/resolve) for the 🔞 18+ tab
  lib/idlix.js -> z2.idlixku.com Pentos gate flow -> HLS + EN/ID subtitles
                 (see "IDLIX resolver" section below)
  /api/stream-proxy -> re-serves HLS (CORS/referer bypass) + rewrites m3u8
                 (absolutize segments, proxy AES-128 key URIs, drop ad segments)
  /api/embed-proxy -> fetches provider embed page server-side, strips ad scripts,
                      injects shield; ALL embed providers (2embed + vidsrc-to +
                      vidsrc-me) point here (proxy: true) — NO iframe sandbox.
                      On provider fetch failure (403/429 — some providers block
                      datacenter IPs) returns a 302 to the ORIGINAL embed URL so
                      playback still starts from the user's browser (pitfall 24)
  /api/subtitles -> OpenSubtitles search/download (keyless) + HLS track proxy
  Watch page  -> <DirectPlayer> (hls.js) if direct, <iframe> if embed,
                 provider switcher buttons, auto-fallback direct->embed on error
```

Dez DID obtain a TMDB key (2026-08-01) after an earlier session concluded signup
was impossible — integration succeeded: home rows, search, details, imdb id all
live. Keep the keyless fallback anyway; providers and metadata both flake.

## Keyless metadata endpoints (verified working)

| Need | Endpoint | Notes |
|---|---|---|
| TV show + episodes | `https://api.tvmaze.com/shows/{id}?embed[]=episodes` | externals give `imdb` + `thetvdb` |
| TV search | `https://api.tvmaze.com/search/shows?q=...` | |
| TV schedule / rows | `https://api.tvmaze.com/schedule?country=US&date=...` | |
| TV top-rated | `https://api.tvmaze.com/shows?page=N` then sort by rating | |
| Movie/TV search | `https://v2.sg.media-imdb.com/suggestion/{first-letter}/{query}.json` | returns `d[]` with `id` (tt), `l` title, `y` year, `i.imageUrl` |

## CRITICAL: provider ID mapping

Providers do NOT accept TVMaze ids. Always pass the mapped id from `getDetails`:

| Provider | Movie | TV |
|---|---|---|
| 2embed | `/embed/{tmdb|tt}` | `/embedtv/{thetvdb}/{s}/{e}` |
| vidsrc.to | `https://vsembed.ru/embed/movie/{tmdb|tt}/` | `https://vsembed.ru/embed/tv/{tmdb|tt}/{s}-{e}` |
| vidsrc.me | `/embed/{tmdb|tt}` | `/embed/{tmdb|tt}/{s}/{e}` |

- **vidsrc-to BUILDS vsembed.ru DIRECTLY since 2026-08-04 (commit 2ba412b), NOT
  vidsrc.to.** vidsrc.to blocks datacenter/Vercel IPs (403/502) — pointing the
  embed at vidsrc.to made the embed-proxy 302-fallback to the RAW player with
  NO shield (ads + no playback in the user's HAR). `vsembed.ru` is the actual
  player host, IS fetchable from Vercel, and its proxied page keeps the shield.
  TV URL uses **dash separator**: `embed/tv/{id}/{season}-{episode}` (NOT
  slashes — slashes 404 on vsembed).

- **Provider ORDER**: 2embed FIRST (default — served through the ad-stripping
  server-side proxy, see pitfall 8), then vidsrc-to (its player has a built-in CC
  menu for subtitles), then vidsrc-me. **Since 2026-08-02 ALL THREE are
  `proxy: true`** (routed through /api/embed-proxy) — vidsrc was proven to serve
  pause→play popup ads unprotected (pitfall 16), so nothing ships raw anymore.
  **CURRENT STATE (2026-08-04): ALL THREE are `proxy: true` again.** After the
  2026-08-03 ad test (Dez: \"Coba tes seluruh provider... kalo ada iklan fix\"),
  the `proxy: false` experiment (commits dfbc048/6e50341) was reverted — every
  provider is back on `/api/embed-proxy` (ad-strip + shield), `sandbox: ''`.
  The route now has the 302 fallback (pitfall 24) so an IP-blocked provider
  still plays. Do NOT ship raw embeds again: 2embed/vidsrc serve popup ads raw
  (pitfalls 8/16) and vidsrc.to additionally blocks server egress (pitfall 24).
- **TMDB flow MUST fetch `thetvdb` for TV**: TMDB `/tv/{id}` does NOT include
  `tvdb_id`; call `/tv/{id}/external_ids` → `tvdb_id`. Without it, 2embed TV
  receives a TMDB id → "This media is unavailable" player error (real regression
  after switching metadata to TMDB).
- TVMaze `show.id` (e.g. 169) is useless to providers. Use `externals.thetvdb`
  (2embed TV) or `externals.imdb` (vidsrc).
- Watch page sends `imdb` + `thetvdb` + `tmdb` query params to `/api/stream`.

## Vidlink direct player (ad-free HLS, hybrid Option A — 2026-08-01)

Dez found `github.com/4texas4/movie-scraper` ("Zenith Movies", vidlink.pro pattern)
and chose **Option A: hybrid** — vidlink direct first, embed fallback. This gives
real m3u8/mp4 URLs resolved server-side so the browser plays in OUR hls.js player:
no iframe, no ads, and OpenSubtitles/offset subtitles attach directly.

```text
Files added:
  lib/vidlink.js            -> WASM boot + getAdv(id) token + vidlink API call
  lib/vidlink/script.js     -> Go WASM runtime shim (eval'd, from 4texas4 repo)
  lib/vidlink/fu.wasm       -> 2.4MB WASM token generator (from 4texas4 repo)
  app/api/vidlink/route.js  -> GET ?id=&type=&season=&episode= -> {url}
  hls.js                    -> npm dependency, direct player in watch page
  components/ErrorBoundary.js -> wraps layout children (see pitfall 13)
```

Key mechanics:
- `resolveVidlink(id, season, episode)` boots the WASM once (module singleton),
  `globalThis.getAdv(String(id))` returns a token, then calls
  `https://vidlink.pro/api/b/{movie|tv}/{token}/{season}/{episode}?multiLang=0`.
- Response is `{sourceId, stream:{qualities:{360|480|720|1080:{url,requiresProxy}}, flags:["cors-allowed"]}}`.
  NO `stream.playlist` for mwVault source — pick the best `qualities` key. `cors-allowed`
  means the browser can fetch the mp4 DIRECTLY (no proxy needed); if `requiresProxy:true`
  use `/api/stream-proxy`.
- `resolveStream()` in sources.js tries vidlink first whenever `force !== 'embed'`
  AND `tmdb` id present; falls back to embed providers on any error. Watch page
  passes `force: idx === 0 ? '' : 'embed'` so provider 0 = auto (vidlink first).
- DirectPlayer uses hls.js for `.m3u8`, native `<video>` for `.mp4`, and calls
  `onFallback` when the video errors/fatal. **Fallback target matters (fixed
  2026-08-01, commit 4bc7979): it goes to `loadStream(activeSeason, activeEp, 0,
  true)` — provider idx 0 (2embed) with `forceEmbed=true` — NOT idx 1 (vidsrc).**
  `loadStream(season, ep, idx, forceEmbed)` gained a 4th param: `forceEmbed`
  skips the vidlink retry and goes straight to the embed proxy. Earlier version
  fell back to vidsrc-to (raw, unprotected) which is exactly the provider whose
  player can show popup ads — always fall back to the ad-stripped proxy provider.

Pitfalls specific to vidlink:
- **WASM boot needs browser globals**: set `globalThis.window/self = globalThis`,
  a stub `document`, and a fake `location` (`protocol/host/...` = vidlink.pro),
  else the eval'd Go shim throws `Cannot destructure property 'protocol' of
  'window.location'`. Script defines class `Dm` (not `Go`) with `importObject`.
- **URLs expire fast** (sign `t=` param); a resolved URL can already be 429 by the
  time the player loads, especially after repeated testing from one IP (bcdn
  rate-limits datacenter IPs). That's WHY auto-fallback exists — don't fight it.
- **CORS reality check (2026-08-03, contradicts the earlier "direct fetch works"
  note):** `bcdn.hakunaymatata.com` does NOT send `Access-Control-Allow-Origin` to
  browsers. A vidlink URL returns 200 to `curl` (server-side, no CORS) but the
  browser `<video>` gets `Failed to fetch` → DirectPlayer auto-falls back to
  embed, and the page silently renders the iframe instead. Do NOT trust the
  `cors-allowed` flag alone and do NOT assume "direct works" from a curl 200.
  Current fix in `lib/sources.js`: after vidlink resolves, probe
  `/api/stream-proxy?url=<playlist>` server-side; if it returns 200/206, return
  the PROXIED url (proxyStream adds `access-control-allow-origin: *` and handles
  both m3u8 rewrite + mp4 passthrough); if the proxy fetch 429s (CDN rate-limits
  datacenter IPs), push the error and fall through to the next layer instead of
  returning a broken direct URL. Diagnostic: curl the raw URL → 200, then
  `fetch(rawUrl, {mode:'cors'})` in the browser → `Failed to fetch` = CORS, not
  a dead URL.
- **Vercel**: keep WASM files with the bundle via `outputFileTracingIncludes` in
  `next.config.mjs` (`'/api/vidlink': ['./lib/vidlink/**/*']`), runtime `nodejs`.
- libsodium-wrappers is required for the WASM boot; eval'd script is from the
  4texas4 repo — re-sync fu.wasm/script.js if vidlink changes their scheme.

## Resource-station resolver (Chinese MacCMS 采集, direct m3u8 — 2026-08-01)

Added as provider layer 2 (movie-only) between vidlink and the embed proxy:
`resolveStream` tries vidlink → `resolveResource(title)` → embed fallback. This
was the "Option A" payoff from mining nodeloc/nodeseek: real m3u8 from Chinese
sliced-CDN stations, played in OUR hls.js player (no iframe, no ads, subtitles
attach). Files: `lib/resources.js`, `app/api/resource/route.js`, plus m3u8
rewrite in `lib/sources.js`.

```text
MacCMS station API pattern (all stations are api.php/provide/vod):
  search:  GET {api}?ac=detail&wd=<query>            -> {list:[{vod_id,vod_name,...}]}
  detail:  GET {api}?ac=detail&ids=<vod_id>          -> {list:[{vod_play_url,...}]}
  play:    vod_play_url = "正片$https://host/path/index.m3u8"
           multiple sources separated by '#'; play_from '$$$' separated groups
  stations often FORBID keyword search: code 1002 "Current API forbids keyword
  search." (dbzy, maotai). Search still works on maoyan, bfzy(暴风), lz(量子),
  iqiyi, ikun, dytt, jszy, etc. Chinese titles match better than English — but
  English "spider-man" matched on 猫眼/暴风/量子 (they store original titles).
  tested live 2026-08-01: 猫眼 (api.maoyanapi.top) returned Spider-Man 2 m3u8;
  暴风 (bfzyapi.com) returned 蜘蛛侠：英雄无归 m3u8.

20 non-adult stations in lib/resources.js (harvested from nodeloc MoonTVPlus
thread 83312, 169-source config): 猫眼 爱奇艺 iKun 电影天堂 360 极速 魔都 非凡 暴风
最大 无尽 旺旺 金鹰 樱花 卧龙 豆瓣 量子 天涯 小猫咪 牛牛. Adult/🔞 entries live in a
SEPARATE `ADULT_STATIONS` const (never mixed into the general chain) — see the
"Adult 18+ tab" section below.

**Resource-station v2 (2026-08-01, commit 116fe4e):** expanded to **56 stations**
(added 新浪 速播 飘零 U酷 光速 红牛 魔都动漫 如意 豪华 百度云 艾旦 金蝉 量子影视 最大点播
无尽影视 虎牙 鸭鸭 索尼 快车 闪电 1080 卧龙点播 天涯 小猫咪 无尽2 牛牛 豆瓣2 金鹰2 非凡2
魔爪 黑木耳 华为吧 淘片 红牛2 蜂巢 金马 大地 七七) AND added **TV season/episode
support** (no longer movie-only):
- MacCMS `vod_play_url` for series is `第01集$url#第02集$url` (groups split by
  `$$$`, entries by `#`, label/url split by `$`).
- `resolveResource(query, {episode})` picks the entry matching the episode number
  (`pickEpisode` matches the label's digits, else index `episode-1`).
- `resolveStream` passes `episode` for `type === 'tv'`, and the chosen entry label
  (e.g. `第01集`) shows in the provider name (`res:暴风 第01集`).

m3u8 rewrite (exported rewriteM3u8 in sources.js, used by /api/stream-proxy):
  - absolutize relative segment paths + proxy each via /api/stream-proxy
  - PROXY AES-128 EXT-X-KEY URI too (relative key.key paths break decrypt if
    left raw) — replace URI="..." with the proxied URL
  - ad-segment filter: AD_SEGMENT_RE /(?:^|\/)(?:ad|gg|ggad|guanggao|logo|maoyan|ys_ad|cm|ads?)[^/]*\.(?:ts|m4s)/i
    drops the segment and injects #EXT-X-DISCONTINUITY to keep sync
  - verify with: curl proxied playlist -> EXT-X-KEY line must point at
    /api/stream-proxy?url=...key.key ; key fetch returns 16 bytes; segment fetch
    returns ts bytes (200)
```

Pitfalls specific to resource stations:
- **Query by TITLE not by numeric id** — station search is fuzzy Chinese-title
  match; `wd=634649` returns nothing. Watch page now passes `title=` to
  `/api/stream`, resolveStream uses `options.title || String(id)`.
- **TV supported since v2** — resource layer now accepts `episode` and picks the
  matching `第NN集` entry from `vod_play_url`; see "Resource-station v2" above.
  Season selection is still coarse (stations usually host one season group per
  vod); episode picker is the reliable part.
- **Each station ~12s timeout; 20 stations worst-case is slow.** resolveResource
  breaks after 5 stations with hits, but a cold miss can still add seconds. It's
  behind the direct layer so acceptable; don't reorder it ahead of vidlink.
- **Some stations are plain HTML trap pages (wolong returns an HTML shell)** —
  fetchJson must check `list` exists and is an array before mapping.
- Source list ages fast (domains rotate); re-harvest from the MoonTVPlus config
  thread when coverage drops. Full 121-entry list (incl. adult) captured in
  `references/chinese-forum-stream-sources.md`.

## IDLIX resolver (z2.idlixku.com — Pentos HLS + EN/ID subs, 2026-08-01)

Dez asked where `z2.idlixku.com` gets its source. Investigation (via the public
scraper `Teramoto669/idlix-scraper` on GitHub) revealed IDLIX is **self-hosted,
not a scraper**: a Next.js frontend over its own Spring-style API, with a custom
"Pentos" gate/claim/redeem flow that returns real HLS + subtitle tracks from CDN
`e2e.majorplay.net`. Because Dez said "Gas", it was integrated as provider layer 3
(after vidlink and resource stations, before the embed proxy):

```text
Files:
  lib/idlix.js           -> full Pentos flow + in-module 6h TTL cache
  app/api/resource/...   -> no dedicated route; resolveStream lazy-imports lib/idlix.js
  deps: got-scraping + tough-cookie  (npm; got-scraping handles CF cookie warmup)
```

Flow (reverse-engineered, all relative to BASE_URL = https://z2.idlixku.com):
1. `got-scraping` client with a shared CookieJar; warm up CF by GET `/`.
2. Resolve **mediaId** (UUID) for the content:
   - search: `GET /api/search?q=<query>&page=1` → `{results:[{id,slug,contentType:'movie'|'tv_series',title,...}], total}`.
     (NOT `data`/`items` — parse `.results`.)
   - page: `GET /movie/<slug>` (or series season/episode page), regex RSC flight
     chunks `self.__next_f.push([N,"..."])` and look for UUID. **Cast member
     arrays also contain UUIDs** (as li keys) — first-UUID match is NOT the mediaId.
   - reliable fallback: `GET /api/movies/<slug>` (or `/api/series/<slug>`) →
     `{id, tmdbId, imdbId, ...}` → `id` IS the mediaId.
3. `GET /api/watch/play-info/{movie|episode}/{mediaId}` → `{gateToken, unlockAt, serverNow}`
   — the **Pentos gate**: the stream is only redeemable after `unlockAt` (~15 s).
4. `POST /api/watch/session/claim {gateToken}` (Referer + Origin set) →
   `{redeemUrl, claim}`.
5. `POST <redeemUrl> {claim}` → `{url: m3u8 master, subtitles:[{label,path}]}`.
6. Cache the result 6 h (module Map) so repeat views skip the 15 s gate.

Provider integration in resolveStream (after resource station, before embed):
- returns `{provider:'idlix', url, mode:'direct', label:title, subtitles:[...]}`;
  watch page's DirectPlayer streams it; OpenSubtitles still applies on top.
- TV: `resolveIdlixByTitle(title, {season, episode})` → `/series/<slug>/season/N/episode/M`
  (prefers a `tv_series` search hit when season is set; movie path otherwise).

Pitfalls specific to IDLIX:
- **First play of a NEW title costs ~16 s** (Pentos gate wait). That's why the
  cache exists and why it sits AFTER vidlink/resource in the chain — a user who
  hits IDLIX pays the wait, but repeat views are instant.
- **URLs are token-signed (`?t=` JWT)**; don't store resolved URLs, always
  re-resolve (cache stores the parsed result, which is fine within the TTL).
- **Search response shape is `{results, total}`** — the naive `.data || .items`
  parse returns 0 hits silently.
- **`rewriteM3u8` must handle master-playlist `EXT-X-MEDIA:` URIs** (audio +
  subtitle tracks in shaka-packager playlists) — the same URI rewrite used for
  EXT-X-KEY/EXT-X-MAP applies; EXT-X-STREAM-INF variant lines stay as-is (their
  following URI line is rewritten as a normal segment line).
- Cloudflare cookie warmup is REQUIRED before any API call (fresh jar per resolve);
  reusing one warm client across requests avoids repeat warmups.
- Site is CF-protected for curl but `got-scraping` + headerGeneratorOptions
  (chrome ≥120, desktop, id-ID/en-US locales) passes from serverless — that's the
  only scraping lib that worked; plain fetch gets 403.

## Pitfalls (all hit for real)

1. **`findStream` regex catches ad-script URLs.** vidsrc embed pages contain
   `s.src='https://llvpn.com/tag.min.js'`. A loose `(?:file|src|url)` fallback
   returns that JS URL → "direct" mode tries to play a script → black player.
   Fix: strict `isVideoUrl()` — only path ending/containing `.m3u8|.mp4|.webm|.mkv|.m4v`;
   the loose fallback must re-validate each match.
2. **Providers are JS-heavy for scrape-resolve; vidlink changes the calculus.** For
   classic scrape (vidsrc.to → vsembed.ru obfuscated JS, 2embed → streamsrcs
   swish/vnest/vcr JS-generated), server-side direct m3u8 resolve usually fails.
   BUT vidlink (see Vidlink section) gives real URLs server-side via WASM — so the
   order is now: vidlink direct → embed iframe fallback. Embed is still the
   reliable fallback, not the primary. Pass `force=embed` to skip vidlink
   (provider idx > 0).
3. **Embed iframes work** — 2embed and vidsrc embed pages send no `X-Frame-Options`
   (verified). A `<video>`-only player breaks most titles; always render the iframe.
4. **2embed TV with tt id returns "error".** Only the `thetvdb` id works for
   `/embedtv/`. Movies accept `tt` fine.
5. **Build path depth**: routes under `app/api/details/[type]/[id]/` need
   `../../../../../lib/...` (5 levels); `app/watch/[type]/[id]/` needs 4 for components.
6. **Test the resolver standalone before blaming the browser**:
   `node --input-type=module -e "import {resolveStream} from './lib/sources.js'; ..."`
   (package.json lacks `"type":"module"` — expect a harmless warning).
7. Provider `image.tmdb.org` poster URLs appear in 2embed HTML; never treat the
   provider page's poster as proof a stream is playable.
8. **Anti-ad: use a server-side embed proxy, NOT iframe sandbox. Sandbox FAILED
   in the real environment.** User complaint (2026-08-01): clicking/seek inside
   the player redirected to Shopee/Play-Store apps. First attempt was per-provider
   iframe `sandbox` (2embed strict, vidsrc none) — my local browser test showed
   2embed rendering fine under `allow-scripts allow-same-origin allow-forms
   allow-presentation` (no popups/top-navigation), so I pushed it. **User's real
   Vercel env then showed "Sandbox not allowed — Remove sandbox from the iframe
   to play. Gabisa di play."** Lesson: a sandboxed third-party player that renders
   in YOUR test browser is NOT proof it works for the user — sandbox is fragile
   with their JS/player versions. The final fix removed sandbox entirely:
   - `lib/sources.js`: `EMBED_PROVIDERS[]` gains `proxy: true` on 2embed; the
     embed URL returned by `resolveStream` becomes
     `/api/embed-proxy?url=<encoded embed>&ref=<encoded embed>` instead of the
     raw provider URL; `sandbox` field is now always `''`.
   - `app/api/embed-proxy/route.js`: fetches the provider embed page server-side
     (nodejs runtime), strips ad scripts, injects a shield, returns clean HTML —
     the iframe then renders OUR cleaned page (same-origin, no sandbox needed).
   - `embedProxy(url, ref)` in sources.js: (1) regex-removes `<script src=...>`
     and inline scripts whose text matches `AD_PATTERNS` (tagivi.com,
     blackninja.host, llvpn.com, adsterra, popads, popcash, propellerads,
     taboola, outbrain, ad.sk, doubleclick, googlesyndication, ads., adservice,
     adpushup, revive-adserver); (2) removes ad iframes; (3) injects a shield
     script that sets `window.open = function(){return null}` (kills popup
     redirects) and a capture-phase click handler that preventDefaults anchors
     whose href matches `/shopee|play\.google|play\.apple|snapchat|tiktok|
     whatsapp|telegram|blibli|tokopedia|bukalapak|game\.com|apps\.|dl\.shopee/i`.
   - Do NOT use `beforeunload` preventDefault in the shield — it interferes with
     player navigation. Keep the shield minimal (window.open null + anchor click
     block) and wrapped in try/catch so a player that overrides window.open
     doesn't break.
   - **Verify**: `node --input-type=module -e "import {embedProxy} from
     './lib/sources.js'; const r=await embedProxy('https://www.2embed.cc/embed/969681');
     console.log(!/tagivi/i.test(r.body), /window.open/.test(r.body))"` → expect
     `true true`. Also curl the proxy route directly and confirm `tagivi` count 0.
   - vidsrc-to / vidsrc-me were `proxy: false` direct embeds until 2026-08-02,
     when a user ad complaint (pause→play popup) proved they DO inject ads —
     both are now proxied too (pitfall 16). Assume NO provider is safe raw.
   - **Ad investigation recipe (Dez asked 2026-08-01: "klik nonton → pause →
     play lagi, ada link iklan redirect keluar?").** Armed monitors before
     interacting: override `window.open` to log+null, listen for
     `beforeunload`/`pagehide`, capture-phase click listener logging anchors,
     and scan `performance.getEntriesByType('resource')` for ad domains
     (`tagivi|blackninja|llvpn|adsterra|popads|popcash|propeller|shopee|
     play\.google|blibli|tokopedia|doubleclick|googlesyndication`). Then click
     the player iframe (nested iframe ref) a few times. Findings: the MovieBox
     page itself was clean (0 window.open, 0 ad-domain requests), BUT clicks
     inside a cross-origin provider iframe CANNOT be fully monitored from the
     parent — a popup opened inside vidsrc's frame is invisible to parent-page
     listeners. So a clean parent probe is NOT proof the provider player is
     ad-free; the durable fix is serving that provider through the embed proxy
     (strip + shield) or sandboxing. Report this honestly: "web kita bersih,
     iklan = dari dalam iframe provider, dan yang rawan = provider non-proxy".
9. **Subtitle menu only works in the OUR `<video>` player (direct mode), not the
   provider iframe.** Cross-origin iframes can't be touched from outside. In embed
   mode, subtitles come from the provider's own CC button — put vidsrc-to first
   because its player has CC. Add an "Open Player ↗" button (opens embed in a new
   tab) so users can reach the provider CC UI full-screen.
10. **OpenSubtitles subtitles are release-specific → timing mismatch is NORMAL.**
    A sub matched to a CAM/HDTS rip will be 1–30s off against a provider's
    WEBDL copy. Do NOT try to find a "correct" sub by guesswork; ship **offset
    controls** instead (see Subtitle sync below). Also prefer subs whose
    `SubFileName` says WEBDL/BluRay over CAM.
11. **Default language = Indonesian, always.** Auto-search sorts Indonesian first
    (flag `lang === 'id' || /indonesia/i.test(langName)`), labels it `🇮🇩 Default`
    with a violet highlight, and auto-applies it in direct mode when stream is
    ready. User can still pick any other language or turn subs off.
12. **Production-only React crash (error #31) after changing `listProviders()` shape.**
    When `lib/sources.js` `listProviders()` switched from `string[]` to
    `[{name, sandbox}]` objects (to carry per-provider sandbox), the watch page
    still rendered `{p}` (the whole object) in the provider switcher buttons →
    `Application error: a client-side exception` in production while `next dev`
    stayed fine (dev is tolerant). Fix: `typeof p === 'string' ? p : p.name` in
    the `.map()`. Rule: **any time an API response shape changes, grep the JSX for
    places that render that value directly as a child** — objects as React
    children are a classic prod-only crash.
13. **Reproduce prod-only client crashes with `next start`, not `next dev`.**
    `npm run build && npx next start -p 3001`, then open in the browser — dev
    masks hydration/render errors that production minification turns into
    "Application error". To see the real minified stack, wrap `<ErrorBoundary>`
    around `{children}` in `app/layout.js` (component in
    `components/ErrorBoundary.js`, renders `error.stack` + `componentStack`).
    Keep the boundary permanently — it converts white screens into readable
    stacks for any future client crash.
14. **Dynamic `await import('./x')` must include the `.js` extension in node
    ESM.** `resolveStream` lazy-loads `./vidlink` and `./resources`. Next/webpack
    resolves extensionless imports fine, so `next build` passes AND the browser
    works — but a standalone `node --input-type=module` test throws
    `Directory import '/root/moviebox/lib/vidlink' is not supported` /
    `Cannot find module '/root/moviebox/lib/resources'`, silently caught by the
    try/catch, so resolveStream fell back to embed while every direct path
    "looked" fine. Fix: `await import('./vidlink.js')` and
    `await import('./resources.js')`. When adding any lazy-loaded lib, include
    the extension.
15. **`NotFoundError: removeChild — node is not a child` on play (hls.js +
    React DOM race).** User saw "KESALAHAN (debug)" boundary with a removeChild
    DOMException when pressing play. Root cause: `<video key={src}>` forces React
    to unmount/remount the video node on every stream change, while hls.js still
    holds a reference to the old node → React tries to remove a node hls.js
    already touched. Also, the 800ms auto-fallback `setTimeout` could fire after
    unmount. Fix pattern (commit aa9153b) in DirectPlayer:
    - **Remove `key={src}` from `<video>`** — let hls.js manage the element via
      the effect lifecycle instead of forcing React re-mounts.
    - Guard effect with `if (typeof window === 'undefined') return;` so hls.js
      never runs during SSR.
    - Hold the fallback timeout in a ref and `clearTimeout` in the effect
      cleanup, so it can't fire post-unmount.
    - Wrap `hls.destroy()` in try/catch and on teardown do
      `videoRef.current.removeAttribute('src'); videoRef.current.load()` inside
      its own try/catch.
    Lesson: any `<video>` + media-library (hls.js) combo needs manual teardown —
    React reconciliation and the library both mutate the same DOM node.
16. **TMDB `with_networks` is FUZZY for films — platform results leak across
    platforms (2026-08-02, Dez: "Film yg harusnya ga ada di platform seharusnya
    malah muncul di platform lain").** Cinema titles (Spider-Man, Moana,
    Supergirl) appeared under Netflix/Disney+/Prime identically because
    `/discover/movie?with_networks=` treats a network airing a film once as a
    match, and `/movie/{id}` has NO `networks` field (only TV does). Correct
    truth sources per type:
    - **Films → `/movie/{id}/watch/providers` flatrate (region US).** Pre-filter
      with `with_watch_providers=<provId>&watch_region=US`, then post-verify
      each title's flatrate list contains the provider. NOTE: watch-provider
      ids are a DIFFERENT numbering than network ids — mapping kept in
      `STREAM_SOURCES[]` (`{id: network, prov: watchProvider}`): Netflix 213/8,
      Disney+ 2739/337, HBO Max 3186/1899, Apple TV+ 2552/350, Prime 1024/9,
      Hulu 453/15, Paramount+ 4330/531, YouTube 49/188, Peacock 56658/386,
      Crunchyroll 2138/283.
    - **Series → `/tv/{id}` `networks[]`** (Stranger Things = [213]); drop
      series whose network list lacks the id (do NOT keep unverifiable ones —
      keeping them re-introduces the leak).
    Verified post-fix: Netflix → Stranger Things/Lucifer/Spider-Verse; Disney+ →
    Avengers/Loki/Mandalorian; Prime → Reacher/The Boys/Invincible.
17. **vidsrc-to & vidsrc-me DO serve popup ads (pause→play trap) — route them
    through embed-proxy like 2embed (2026-08-02, commit 098b2b8).** Dez:
    "Video yg ditampilkan di vidsrc-to & vidsrc-me ada iklan. Ketika play lalu
    pause lalu play lagi." The trap: player JS calls `window.open` on the
    pause/visibilitychange/pointerdown event. Fixes shipped:
    - `EMBED_PROVIDERS`: both vidsrc entries gain `proxy: true` → their embed
      URL becomes `/api/embed-proxy?url=...` (server-side strip + shield).
    - `AD_PATTERNS` expanded +18 networks: adtng, exoclick, juicyads,
      trafficjunky, tsyndicate, hilltopads, clickadu, adcash, ero-advertising,
      plugrush, ad-maven, monetag, onclckmn, onclick, popunder, betotodilea,
      choupsee, oughttumba.
    - Shield v2 (injected into proxied HTML): (a) `window.open` killed via
      defineProperty (non-writable, non-configurable) AND plain assignment —
      some players grab a reference early; (b) `location.assign` wrapped to
      swallow navigations to BAD domains; (c) form `submit` listener blocks ad
      form actions; (d) MutationObserver removes injected full-screen fixed/
      absolute overlay nodes whose HTML/src matches BAD (skips anything inside
      <video>). When editing the observer, watch JS operator precedence —
      `BAD.test(s) && !n.closest || ...` silently misbehaves; compute
      `insideVideo` first.
    - **Verification recipe**: curl `/api/embed-proxy?url=<vidsrc embed>` →
      grep for ad domains → only hit allowed is the shield's own BAD regex;
      open the proxy URL directly in the browser tool, click the nested player
      iframe 2× (play, pause-ish, play), then
      `performance.getEntriesByType('resource').filter(e=>adRe.test(e.name))`
      → expect 0. Video itself lives in a cross-origin nested iframe — parent
      can't introspect it, and that's fine; 0 ad-network hits is the pass bar.
18. **`pkill -f "next start"` kills the calling shell too (exit -9/-15), and a
    stale `next start` server serves the OLD build silently.** When restarting
    the local test server after rebuild: kill by PORT not by cmdline —
    `fuser -k 3100/tcp` — then verify the new server is actually the one
    answering (`tail` the new log; hit an endpoint whose response shape
    changed, e.g. check `page`/`totalPages` keys exist). Symptom that you're
    talking to a zombie: API returns the old response shape with 200.
    Also: `terminal(background=true)` is the only clean way to run the server;
    `nohup ... &` in foreground mode is rejected by the harness.
19. **2embed injects a shell redirect at the TOP of `<head>` — a shield appended
    at `</body>` is TOO LATE (2026-08-03, commit 650a8b9).** Symptom: watch page
    renders the 2Embed site shell (`www.2embed.skin/movie/<id>` — "Watch at /
    copy the code below") instead of the player. Root cause: 2embed's embed
    page begins with an inline `<script>window.location.replace("https://www.2embed.skin/...")</script>`
    that executes before any late-injected shield. Two fixes, BOTH required:
    (a) server-side strip that inline script in `embedProxy()` — extend the
    inline-script removal to also drop blocks matching
    `/location\.(replace|assign)\s*\(\s*["']https?:\/\/(?:www\.)?2embed\.skin/i`;
    (b) inject the shield at the TOP of `<head>` (before provider scripts), not
    at `</body>` — `cleaned.replace(/<head[^>]*>/i, m => m + '\n' + shield)`.
    Verify: `curl /api/embed-proxy?url=<2embed>` → grep `location.replace("https://www.2embed.skin` = 0
    AND `streamsrcs` still present. This is the #1 cause of "iframe shows shell
    not player" after enabling proxy:true on 2embed.
20. **vidlink CDN URLs pass server-side checks but FAIL in the browser (CORS).**
    `bcdn.hakunaymatata.com` etc. serve `access-control-allow-origin` only to
    vidlink.pro, so curl/`fetch` from the server returns 200 + video bytes, but
    the browser `<video>` gets `Failed to fetch` → DirectPlayer auto-falls back
    to embed. Also the same CDN rate-limits datacenter IPs (HTTP 429 on rapid
    probes). When routing vidlink through `/api/stream-proxy`, validate the
    proxied fetch too (`fetch('/api/stream-proxy?url=...')` must return
    200/206), else fall through to the next provider — never return a URL the
    proxy itself can't fetch (it will 502 in the browser).
21. **Embed fallback must forward imdb/thetvdb, not just tmdb (2026-08-03).**
    The `/api/stream` route's timeout path called `embedFallback` with
    hardcoded `thetvdb:''`/`imdb:''`; for TV, 2embed then received the TMDB id
    → `https://www.2embed.cc/embedtv/<tmdb>/...` → "This media is unavailable".
    Fix: `embedFallback(id, type, season, episode, providerIdx, {imdb, thetvdb, tmdb})`
    and forward them from the query params at both call sites. TV embeds must
    show `embedtv/<thetvdb>/<s>/<e>`.

22. **"Resolving stream…" forever = /api/stream chain timeout, not a provider
    bug (2026-08-03).** User reported "ga bisa play" and the watch page stuck on
    "Resolving stream…" while `/api/details` and `/api/subtitles` loaded fine and
    `/api/stream` NEVER appeared in browser resource entries. Root cause: the
    default `force=''` chain (vidlink WASM → 56 resource stations at ~12s timeout
    each → IDLIX Pentos ~16s gate) can take **35+ seconds**, and the browser
    fetch gives up around 30s. Manual curl with `force=embed` returns in 0.2s,
    so the endpoint "works" — the DEFAULT path is what's too slow.
    Fix (shipped in `app/api/stream/route.js`): cap the whole direct chain with
    `Promise.race([resolveStream(...), timeout(12000)])`; on timeout fall back to
    `resolveStream(..., {force:'embed', providerIdx})` which builds the provider
    embed URL immediately (~0.2s) and returns `{...fb, timedOut:true}`. Playback
    now ALWAYS starts within ~12s worst case. Diagnostics: compare
    `curl "…/api/stream?force=&provider=0"` (full chain, slow) vs
    `curl "…/api/stream?force=embed&provider=0"` (fast) — if the first times out
    but the second returns in <1s, it's this bug, not the provider.
    **Second bug in the same fix (2026-08-03):** the timeout fallback helper
    `embedFallback()` in `app/api/stream/route.js` originally hardcoded
    `imdb:''`, `thetvdb:''` — so on timeout, TV embeds got a TMDB id
    (`embedtv/1396/1/1`) instead of thetvdb (`embedtv/81189/1/1`) → 2embed TV
    "This media is unavailable" (pitfall 4). Fix: embedFallback MUST forward
    `{ imdb, thetvdb, tmdb }` from the query params. Symptom to watch for:
    watch page renders an iframe whose URL uses the TMDB numeric id for TV.
23. **Deploy URL confusion: `moviebox.vercel.app` is a DIFFERENT app.** The real
    MovieBox project deploys from `agenticspring/moviebox`. As of 2026-08-04 the
    live URL is **`moviebox-wine-ten.vercel.app`** (project renamed during
    public-release work); `moviebox-neon-sigma.vercel.app` was the earlier name
    and now returns `DEPLOYMENT_NOT_FOUND` / 404. `moviebox.vercel.app` is an
    unrelated create-react-app shell (title "React App") — do not test against
    it. **Vercel free tier does NOT auto-deploy on git push** (Dez: "Ga bisa
    auto deploy karena limit free tier — jadi harus redeploy ulang"). Every push
    needs a manual **Redeploy** from the Vercel dashboard (Deployments → ⋮ →
    Redeploy, ideally "with existing Build Cache"); until redeployed the app URL
    keeps returning 404 / `DEPLOYMENT_NOT_FOUND`. Always confirm the deployed
    commit matches the latest push before testing.
24. **Provider blocks server IP → embed-proxy must 302-fallback, not 502
    (2026-08-03, commit 4a46e99).** Symptom: embed renders in LOCAL tests, but
    in the production Vercel env the iframe shows `proxy error: HTTP` (vidsrc.to
    was the one that failed; 2embed/vidsrc-me worked). Root cause: vidsrc.to
    anti-bot blocks datacenter/server IPs (403/429) — the local VPS egress IP
    is fine, Vercel's egress IP is blocked, so `embedProxy()` fetch throws and
    the route returned `502 "proxy error: HTTP"` → player dead. Fix in
    `app/api/embed-proxy/route.js`: catch the fetch failure and return
    `302 location: <original embed url>` instead of 502. The iframe then loads
    the provider directly from the USER's browser (residential IP) — playback
    starts, you just lose the ad-strip/shield for that provider (acceptable:
    a dead player is worse than a possible popup). Diagnosis: compare the
    embed-proxy URL from localhost (200) vs production (502); if the raw
    provider URL curl's 200 from local but the proxy 502s from Vercel, it's an
    IP-block, not a code bug. Keep this fallback for ALL providers — any of
    them can start blocking server egress without warning.
    **Screenshots decode tip**: when the user pastes a Vercel/phone screenshot
    and the vision model can't see it, OCR it — `apt-get install -y
    tesseract-ocr && tesseract <file> -` extracts the error text reliably.
25. **Provider anti-bot BLANKS headless/automation pages after the player loads
    (2026-08-04).** Symptom: verifying from a datacenter IP with a headless
    browser (cloud browser tool OR local Playwright) the watch page renders an
    EMPTY body (`innerText` = '', URL sometimes jumps to about:blank) even
    though the app is fine for real users on residential IPs. Root cause:
    2embed/vidsrc anti-bot detects automation (`navigator.webdriver`, headless
    fingerprint) and, AFTER the player iframe has appeared (~6–8s), blanks the
    top page (`window.top = about:blank` or equivalent). Diagnose with
    Playwright: poll `iframe[title="player"]` every 1–2s — it appears at ~6s
    with the correct `/api/embed-proxy?url=...` src, then the body goes empty.
    Console shows provider noise (`You don't have permission to use DEVTOOL!【
    type = 6】`, repeated console.clear/table) — that noise is PROOF the player
    did load before the blank. The blank is anti-bot, NOT an app bug.
    Verification workarounds, in order:
    - **Screenshot the instant the iframe appears** (before the blank) and OCR
      it — proves the player rendered. Script: `scripts/play-verify.py`.
    - Stealth init script (`navigator.webdriver → undefined`, `chrome.runtime`
      stub, `languages`, `plugins`) + `--disable-blink-features=AutomationControlled`
      + CDP `Page.addScriptToEvaluateOnNewDocument` lowers detection rate but is
      NOT reliable against 2embed; headed via `xvfb-run -a` sometimes helps.
    - **Accept the limit**: from a datacenter IP you may never get a
      click-to-play confirmation. Evidence that IS available: HTTP-layer checks
      (pitfall 24), the moment-screenshot, and the iframe-appeared log.
      Ask the user to click-play on their residential IP and report back.
    - NEVER report "play is broken" from an empty headless body — check whether
      the iframe appeared first; an empty body with player-console noise means
      anti-bot, not a dead app.
26. **Read the USER'S HAR file to diagnose playback (2026-08-04).** When Dez
    sends a `.har.json` export from his browser, it is the ground truth for what
    actually happened: `json.load(har)` → `log.entries[]`, count response
    statuses (`collections.Counter`), then filter entries by
    `request.url` containing `/api/stream|/api/details|/api/embed-proxy|2embed|
    vidsrc|vsembed|streamsrcs`. Key patterns that diagnose instantly:
    - **0 video requests** (no `.m3u8|.mp4|.ts|.m4s|manifest` anywhere) with
      player assets loaded (vsembed style.css/jquery/base64.js/sources.js/sbx.js
      all 200) = player shell rendered but video never STARTED (user didn't
      click play, or an ad-overlay/adblock intercepted). This is NOT the same as
      "no player" — check the provider asset requests before concluding.
    - **Ad-cloaking domains** (`.cfd`, `.rest`, `cloudnestra.com/asdf.js`,
      `cloudorchestranova.com/rcp/...`, `disable-devtool@…/misdir.js`) appearing
      in the 2s AFTER a player's JS assets load = the PROVIDER injects them
      (vsembed/vidsrc does), not MovieBox. Their status is usually 0 (blocked)
      — that's the browser/adblock stopping them, which is fine, but they prove
      the raw provider page carries cloaked ads (shield is doing its job when
      served through the proxy).
    - **`chrome-extension://` hosts in the HAR** = user has extensions
      (adblock etc.) — if a player iframe URL like `cloudorchestranova.com/rcp/...`
      shows status 0, the user's own extension may be blocking the PLAYER, which
      no app-side fix can overcome; tell Dez to whitelist the player domain or
      test in incognito.
    - App-side requests all 200 while the user still sees a dead player ⇒
      provider/IP/extension problem, not the app.
28. **Embed-proxy CANNOT execute JavaScript - direct embeds required (2026-08-04).**
    Symptom: all providers failed playback after enabling embed-proxy (proxy:true).
    Root cause: 2embed/vidsrc generate video URLs via client-side JavaScript
    (`streamsrcs.2embed.cc/swish`, vsembed.ru obfuscated JS). Server-side
    embed-proxy fetches the HTML but CANNOT execute that JS - it gets the shell
    page, not the video URL. Fix: set `proxy: false` for all providers to allow
    direct embeds from the browser. The trade-off is accepting provider ads vs
    having NO playback at all. This is fundamentally different from pitfall 8/17
    (ad blocking) - it's a JavaScript execution barrier.
    **Verification**: curl the embed-proxy URL returns HTML with the player shell,
    but no actual `.m3u8|.mp4` URLs - the JS that generates them never ran.

27. **AD vs PLAYER domain distinction — verify before blocklisting (2026-08-04,
    commit 2ba412b).** While adding HAR-discovered cloaking domains to
    `AD_PATTERNS`/shield BAD regex, `cloudorchestranova.com` was initially added
    as an ad domain — WRONG: it is the vsembed PLAYER iframe host
    (`<iframe id="player_iframe" src="//cloudorchestranova.com/rcp/<base64>...">`),
    and `cloudnestra.com/asdf.js` is the ad script. Blocking the player domain
    breaks video. Rule: for every new domain found in a HAR, fetch the provider
    page and check WHERE it appears — `<script src>` = ad (block), `<iframe
    src>` = player (allow, needed for playback). Only `cloudnestra` + `.cfd` +
    `.rest` went into BAD; `cloudorchestranova` stays whitelisted. Also: verify
    embed-proxy output AFTER the change — the cloudnestra <script> must be 0
    while the cloudorchestranova player_iframe count stays ≥1.
28. **`moviebox-xi-seven.vercel.app` is the live URL since 2026-08-04.** Dez's
    HAR references xi-seven; `moviebox-wine-ten` then returned
    `DEPLOYMENT_NOT_FOUND` (superseded by another redeploy). Treat the deployed
    URL as a moving target on free tier — ALWAYS confirm from the user's latest
    HAR/screenshot which deployment is live before testing, and expect
    `DEPLOYMENT_NOT_FOUND` 404s between manual redeploys.

## Subtitle sync (offset controls — direct mode)

Because provider rips differ from OpenSubtitles releases, add a custom overlay +
offset so users can nudge timing live (never rely on native `<track>` timing):

```text
State: cues[] [{start,end,text}], subOffset (seconds), currentSub
Parse: fetch(activeSub).text() → parseCues() splits VTT/SRT blocks, timeIdx line
       with '-->', parseTs() handles H:MM:SS.mmm (comma or dot).
Sync:  <video onTimeUpdate> → t = video.currentTime + subOffset → first cue
       where start<=t<=end → render overlay lines.
UI:    sub-offset pill in player-bar: −0.5s −1s [±offset] +1s +0.5s ↺ reset.
Overlay: absolutely positioned div (bottom 8%, z-index above video, pointer-events none),
       each line a dark pill (rgba(0,0,0,.72)).
```

Replace `<track>` with this overlay in direct mode — native tracks can't be offset.
(Verified: sub was off for Spider-Man; offset control fixed it without provider change.)

## Streaming-site backend analysis: loklok.fun / loklok.tv → NetPop / RR.TV (2026-08-01)

Dez asked where the source comes from for `loklok.fun` (Nuxt official) and
`loklok.tv` (Vue2 + dutun.cc "Ironman" template clone). Both frontends are
cosmetic; the real backend is **NetPop = RR.TV** (`web-api.netpop.app`,
`alpha-web-api.rr.tv`, `img.netpop.app`) — the SAME backend family as the RR
domains Dez already uses for webnovel (orangkaya.cyou / anakbaik.cyou /
ejhitam.my.id), though that's accounts, not video streams. API requires
`currentTime` + `sign` + `aesKey` headers (sign = MD5(base64url(AES_encrypt(
ts+json, uuid))), aesKey = Turing `Clouse(uuid)`), so curl probes get 403
("timestamp empty" → "aesKey empty"). Key endpoint for video source:
`/cms/web/pc/download/urls`; metadata via `/cms/web/pc/album/detail`.
Full fingerprint + signing deobfuscation: `references/loklok-netpop-backend.md`.
Conclusion on "scraping vs self-host": **LokLok is self-hosted, not a scraper**
(own download/urls endpoint, own CDN, Turing anti-bot protecting an owned
asset) — contrast with MovieBox's own scrape-from-providers chain.
Before integrating any "LokLok-like" site as a provider, grep its bundle for
`web-api.netpop.app|alpha-web-api.rr.tv|netpop` to recognize this family, and
weight that the Turing signing makes it a high-maintenance provider vs vidlink /
MacCMS stations.

## LK21 / Indonesian streaming-site research (2026-08-01)

- `tv12.lk21official.cc` and mirrors **block datacenter IPs** (Cloudflare 403 / error
  1005); `r.jina.ai` reader proxy gets 404 on film pages (Cloudflare fronting). Do
  not burn time scraping them directly.
- The pattern (from `febriadj/lk21-api` GitHub scraper + embed probes): these sites
  embed **vidsrc.to / vsembed.ru** players, and their "subtitle" IS the provider
  player's built-in CC — there is no separate subtitle file. That's why MovieBox
  already matches the LK21 experience once vidsrc-to is provider #1.
- vsembed uses an encrypted `data-hash` → `cloudnestra.com/rcp/...` chain (base64
  → AES-ish in browser JS). Not worth server-side reverse-engineering; embed iframe
  is the supported path.

## Companion repo: agenticspring/movie-scraper (vidlink-only clone, 2026-08-01)

Dez asked for a private fork of `4texas4/movie-scraper` to deploy side-by-side on
Vercel and compare playback. It lives at `https://github.com/agenticspring/movie-scraper`
(PRIVATE, static HTML + one serverless function, NOT Next.js). Full details in
`references/movie-scraper-fork.md`.

```text
Repo:   agenticspring/movie-scraper (PRIVATE, main)
Local:  /tmp/movie-scraper-vidlink (re-inited, NOT a shallow clone)
Stack:  index.html (single-file UI) + api/index.js (vidlink WASM resolve) + fu.wasm
Deploy: Vercel import; vercel.json rewrites /api → /api/index.js
Use:    https://<app>.vercel.app/?id=550  (movie)   ?id=456&s=1&e=1 (TV)
```

Key differences from MovieBox: **no subtitle support, no 2embed/vidsrc fallback,
no proxy shield** — it's pure vidlink. That's why it's a comparison target, not a
replacement. When the user asks "buatin UI kayak moviebox" for it, the frontend
is a single `index.html` with two modes (browse + player) — see the reference.

## Explore UI — source, genre & country categories (country added 2026-08-02)

Dez asked for a category UI: browse films by **streaming provider source** (Netflix,
Disney, YouTube…), by **genre tags** (Action, Romance…), and by **origin country**
(🇰🇷 Korea, 🇯🇵 Japan, 🇮🇩 Indonesia… — "gampang cari film dari negara mana").
Built as `/explore` with tabs; TMDB drives all three (metadata labels, not actual
provider video).

```text
Files:
  lib/tmdb.js          -> STREAM_SOURCES[] ({id: network-id, prov: watch-provider-id} —
                          TWO different TMDB numberings, see pitfall 16) + GENRE_TAGS[]
                          + COUNTRIES[] (22 ISO 3166-1 codes w/ flag emoji)
                          + discoverMovies()/discoverSeries({source|genre|country, page})
                          -> return { items, page, totalPages } (totalPages clamped to 50)
  app/api/explore/route.js -> GET /api/explore (list) | ?source=213&page=N | ?genre=28&page=N
                          | ?country=KR&page=N  -> { title, movies, series, page, totalPages }
  app/explore/page.js  -> client page, tabs (Platform/Genre/Negara/18+),
                          emoji category grid + results view + <Pagination>
  components/BottomNav.js -> 5 items: Home/Movies/Series/Explore/Search
```

**Pagination (added 2026-08-02, Dez: "genre film yg muncul hanya sedikit, buat
ada tombol next atau 1 2 3").** Every explore results view (Platform/Genre/
Negara — NOT adult, stations have their own paging) renders a `<Pagination>`
bar: `‹ Prev | 1 … cur-2..cur+2 … total | Next ›` as glass `.page-btn` pills
(active = --grad). Page comes from the `?page=` searchParam (so it's
shareable/reload-safe), defaults 1; `buildHref(p)` preserves the active
filter. TMDB total_pages is clamped to 50 (500 is TMDB's raw cap — deep pages
are low-signal). Home/browse pages keep infinite "Muat lebih banyak" instead.

Source ids: STREAM_SOURCES entries carry BOTH ids — `id` = TMDB network id
(TV discover + TV details.networks) and `prov` = TMDB watch-provider id (film
discover via with_watch_providers + /movie/{id}/watch/providers). Mapping:
Netflix 213/8, Disney+ 2739/337, HBO Max 3186/1899, Apple TV+ 2552/350,
Prime 1024/9, Hulu 453/15, Paramount+ 4330/531, YouTube 49/188,
Peacock 56658/386, Crunchyroll 2138/283. Genre ids: standard TMDB genre list (28 Action,
10749 Romance, 27 Horror, 878 Sci-Fi, etc.) — **TMDB has no 18+/adult genre**;
Dez asked for one and it was shipped as the 🔞 tab backed by adult MacCMS
resource stations (see "Adult 18+ tab" below), NOT by TMDB.

**Country browsing uses TMDB `with_origin_country`** (NOT `with_watch_region` —
origin country = where the content was produced, watch_region = where it's
streamable). `COUNTRIES[]` in lib/tmdb.js: US KR JP CN ID TH IN GB FR ES DE IT
TR PH MY VN HK TW AU BR MX RU, each `{id, name, emoji}`; API resolves title as
"🇰🇷 Korea". Verified 2026-08-02: `?country=KR` returned 20 movies + 20 series
(Parasite, Squid Game, Weak Hero…). Vote-count floors matter for small catalogs:
movies use vote_count ≥ 100, series ≥ 50 — don't raise them or ID/TH/VN results
thin out.

Results view shows Movies + Series grids; cards deep-link to `/watch/{type}/{id}`.

Pitfall: **Next.js 15 `useSearchParams()` in a client page crashes static
prerender** (`Error occurred prerendering page "/explore"`). Fix: wrap the
component using it in `<Suspense>` (default export = `ExplorePage` returning
`<Suspense><Explore/></Suspense>`); keep `useSearchParams` inside the inner
component. Verify by opening `/explore` after `next start` — the tab grid and a
category result (e.g. `?source=213` → Netflix movies + series) both render.

## Adult 18+ tab (2026-08-01, commit 827a2cb) — REMOVED 2026-08-03

> **REMOVED for public release.** Dez: "yg 18+ hapus juga". Deleted:
> `ADULT_STATIONS` + `listAdultStations/browseAdultStation/searchAdultStations/
> resolveAdultVod` from `lib/resources.js`, the `?adult=1` branch in
> `app/api/resource/route.js`, the 🔞 tab in `app/explore/page.js`, and
> `app/play/adult/`. General chain (vidlink → resource → idlix → embed) is
> untouched. Archive below for reference if it ever comes back.

Original design (reference only):

Dez explicitly asked to enable 18+/smut ("Aktif fitur 18+/smut"). Adult content
comes from the same Chinese MacCMS harvest, kept in a SEPARATE `ADULT_STATIONS`
const in `lib/resources.js` (22 stations: 麻豆 番号 优优 小鸡 乐播 奶香 辣椒 鲨鱼 豆豆
滴滴 黑料 百万 桃花 精品 CK souav 细胞 香蕉 杏吧 色猫 奥斯卡 丝袜) — never merged into
the general resolve chain (vidlink → resource → 2embed) because that layer feeds
the main watch page.

```text
Pipeline (all adult, separated from main chain):
  lib/resources.js     -> ADULT_STATIONS[] + listAdultStations() +
                          browseAdultStation(api, page) + searchAdultStations(q) +
                          resolveAdultVod(api, vodId)
  app/api/resource/route.js -> adult mode via ?adult=1:
                          ?adult=1                          -> {stations:[...]}
                          ?adult=1&api=<url>&browse=1       -> latest items (30)
                          ?adult=1&q=<term>                 -> search across stations
                          ?adult=1&api=<url>&id=<vod>&resolve=1 -> {url} m3u8
  app/explore/page.js  -> third tab 🔞 18+; station cards ->
                          /explore?adult=<encoded api> -> item grid ->
                          /play/adult?api=..&id=..
  app/play/adult/page.js -> client page: 18+ confirm gate FIRST ("Konten Dewasa
                          18+ / ▶ Lanjutkan"), then resolve + hls.js player
                          (same /api/stream-proxy rewrite, so AES keys + ad
                          segments handled automatically)
```

Pitfalls specific to adult:
- **Adult stations are flaky + domains rotate fast.** Browse may return 30 items
  one day and 0 the next; if one station is down, users switch to another card.
  Keep the station grid (many cards) rather than a single "adult" bucket.
- **Adult m3u8 can be unencrypted or AES — both work** through /api/stream-proxy
  because rewriteM3u8 proxies EXT-X-KEY URIs; no special handling needed.
- The confirm gate lives on `/play/adult` (not the watch page) — adult never
  routes through the main `/watch` page, so the general provider chain and
  subtitles UI are untouched.
- List maintenance mirrors non-adult: re-harvest station APIs from the MoonTVPlus
  config thread when coverage drops (full 121-entry list incl. adult is in
  `references/chinese-forum-stream-sources.md`).

## Site password gate (2026-08-01, commit 4941fd5) — REMOVED 2026-08-03

> **REMOVED for public release.** Dez asked to delete the password gate
> ("hapus password log-in nya") when preparing the repo to go public. Files
> deleted: `middleware.js`, `app/login/`, `app/api/login/`. There is no auth
> anymore — the site is fully open. If a gate is ever re-added, the original
> design below is the reference.

Original design (reference only):

```text
Files:
  middleware.js            -> runs on every page (not /api/, /login, /_next)
  app/api/login/route.js   -> POST {password} -> sets httpOnly cookie if match
  app/login/page.js        -> password form (client, Suspense-wrapped for
                              useSearchParams; redirects to ?next= target)
```

Key mechanics + pitfalls (if re-adding):
- Cookie value = SHA-256 of the password (edge crypto.subtle works in
  middleware), httpOnly + sameSite lax + 30d maxAge. Middleware compares cookie
  to `await sha256(SITE_PASSWORD)` and redirects 307 → `/login?next=<path>` if
  missing/mismatch.
- **API routes stay OPEN** (`pathname.startsWith('/api/')` is public). If you
  gate `/api/*`, `<video>` element fetches (which don't carry httpOnly cookies
  reliably cross-origin) break playback. Video/subtitle/resource/stream-proxy
  must remain unauthenticated.
- Verify with curl: no cookie → `/` 307 to `/login`; wrong password → 401;
  right password → `{"ok":true}` + cookie jar; with cookie → 200 on `/` and
  `/explore`; `/api/explore` stays 200 without cookie.
- Changing password = set `SITE_PASSWORD` env var in Vercel + redeploy (cookie
  hash changes, old cookies stop matching).

## Public release prep (2026-08-03)

Dez: "gua mau akan publik" — repo `agenticspring/moviebox` goes PUBLIC. Before
flipping visibility, purge everything private from history and tree:

1. **Delete the auth gate**: `middleware.js`, `app/login/`, `app/api/login/`
   (removed above). Grep for `/login|mb_auth|SITE_PASSWORD` afterwards.
2. **Delete the 18+ tab**: `ADULT_STATIONS` + adult helpers in `lib/resources.js`,
   `?adult=1` branch in `app/api/resource/route.js`, adult tab + `/play/adult`
   in `app/explore/page.js`. Grep `adult|ADULT|18+|🔞` afterwards — the explore
   results view kept a `result._label !== 'adult'` condition and a stray `)}`
   that must be cleaned up too.
3. **Squash history to ONE clean commit**: `git checkout --orphan clean-publish`,
   `git add -A`, commit, delete old `main`, rename, `git push -u origin main
   --force`. This removes the old commit messages that mention the password and
   prior private-state commits. Verify: `git grep -lE "mylittledragon|mb_auth|
   SITE_PASSWORD" HEAD` must return nothing, and `git ls-tree -r HEAD
   --name-only | grep -E "login|adult"` must be empty.
4. **TMDB key**: Dez explicitly chose to KEEP the key hardcoded in `lib/keys.js`
   ("key tmdb biar harcode aja") even for a public repo — TMDB keys are
   client-side-safe and this is the user's call. Keep `lib/keys.js` bundled;
   `.env.example` stays optional-only.
5. **Scrub the remote URL after push**: push with the PAT embedded, then
   `git remote set-url origin https://github.com/agenticspring/moviebox.git`
   so the token isn't left in `.git/config`.
6. README: replace "Private" with "Open-source", drop "repo private" notes.
7. After a force-push, Vercel needs a manual **Redeploy** — the old deployment
   shows `DEPLOYMENT_NOT_FOUND` / 404 until then (Dez: "gua belum deploy").

## Design language (Sakura Noir theme over IDLIX layout — 2026-08-02, commit f6bfb46)

Layout/placement/font follow IDLIX (`z2.idlixku.com`, commit `1228bc1`) — keep
that structure. The COLOR palette is now **Sakura Noir**, chosen by Dez
("hitam dan pink Sakura glossy glass"). Do NOT revert to the old violet→cyan
MovieBox palette or the pre-IDLIX split-editorial hero.

```text
Palette (app/globals.css :root):
  --bg #0a0608 (near-black w/ warm tint), body gets 2 radial pink glows
  --grad: linear-gradient(120deg, #ff5c9e 0%, #ff8fbf 45%, #ffc9de 100%)
  --gold #ffd166  -> RESERVED for ★ rating badges/chips only
  text #fdf2f7, muted #c9a3b8, lines rgba(255,182,213,.1/.2)
Glossy-glass recipe (nav, chips, search, cat-cards, login):
  background rgba(255,182,213,.04-.08) + backdrop-filter blur(20px) saturate(160%)
  + border rgba(255,182,213,.2) + inset 0 1px 0 rgba(255,255,255,.06) top highlight
Active pills (nav-link/explore-tab/season-tab): var(--grad) bg, dark text #2a0a18,
  glow shadow 0 4px 16px rgba(255,92,158,.4) + inset white top highlight
Section headings (h2 + .browse-head h1): 4-5px pink-gradient ::before accent bar
Rank numbers (trending row): pink gradient text via background-clip + drop-shadow
```

Informative-card pattern (Dez: "informasi filmnya informatif"): every poster card
carries a gold ★ rating badge (`.badge-rate`, top-right glass pill) when
rating > 0; sub-line shows year + "· Series" for tv. Detail page chips: rating,
year, runtime ("2j 15m" Indonesian format), "N Seasons · M Episode" for tv.
UI copy is Indonesian (search placeholder "Cari film atau series…", hero tag
"✦ Featured · Pilihan hari ini"). BottomNav is 5 items: Home/Movies/Series/
Explore/Search.

```text
Nav (components/Nav.js):
  - .nav is the sticky bar; inner .nav-inner = max-width 1400px container
  - Pill nav links: logo → Home | Movies | TV Series | Explore
    .nav-link.active = gradient pill (bg var(--grad), text #0a0a12)
  - Search right-aligned (width min(320px,34vw)), full radius
Hero (components/Hero.js): full-bleed banner, min-height 82vh, backdrop image;
  .hero-overlay gradient (bottom + left dark), .hero-inner max-w 1400, content
  bottom-left. .hero-poster-card now hidden by default, only desktop >=900px.
Rows (components/Row.js): .section max-w 1400 centered; heading 22px bold +
  title count right-aligned (justify-content space-between); card poster 150px.
Font (app/layout.js): Inter via next/font/google (variable --font-inter), set on
  <html>; body font-family: var(--font-inter), -apple-system, ...
```

Follow that shape when adding pages (Movies/TV pod-page headers, detail, etc.).
CSS vars (colors/radius) live at the top of `app/globals.css`; the IDLIX layout
rules are the `.nav-inner/.nav-link/.hero-inner/.section` rules in the same file.

Pitfall: Inter bundles via `next/font/google` — requires network at build time;
the build downloads the woff2. Local `next start` after a successful build has no
extra network need.

## Playback debug order

0. **Verify play BEFORE push (Dez requirement, 2026-08-01; repeated 2026-08-02
   "Pastikan kau tes bekerja dulu dan bisa play film").** Build passing is not
   enough. For provider/iframe changes: serve a local test page with the exact
   iframe attrs, open in the browser, confirm the player actually renders
   (accessibility snapshot shows poster/play/nested iframe; network tab shows
   CDN/streamsrcs requests), then push. If vision is unavailable, rely on the
   snapshot + resource entries.
   **BUT a local test is not proof for the user's environment** — the sandbox
   approach passed local verification and still broke ("Sandbox not allowed") on
   their Vercel deploy. When in doubt about sandbox/iframe attributes, prefer the
   server-side embed proxy (no sandbox) and verify via the proxy's own curl check.
   **Production HTTP-layer verification (2026-08-04 — use when the browser tool
   renders empty/about:blank for the watch page).** The browser tool is flaky on
   iframe-heavy pages; don't stall on it. Verify playback by curling the exact
   endpoints the iframe uses:
   - `curl "https://<app>.vercel.app/api/stream?id=..&type=movie&force=embed&provider=0|1|2"`
     → each must return `{error:false, provider, embed: "/api/embed-proxy?..."}`.
   - `curl "https://<app>.vercel.app/api/embed-proxy?url=<encoded embed>&ref=<...>"`
     → expect **HTTP 200** + `streamsrcs`/iframe present for 2embed/vidsrc-me, or
     **HTTP 302 → redirect_url = original provider URL** for an IP-blocked provider
     (that's the 302 fallback working, NOT an error).
   - If `browser_vision` also fails, OCR the user's screenshots:
     `apt-get install -y tesseract-ocr && tesseract <img> -` — it reliably reads
     Vercel/phone screenshots ("proxy error: HTTP" was caught this way).
   **Dez does NOT accept API-only play verification (2026-08-04).** When he
   says "mengandalkan api" / "Pastikan kau klik video play nya biar tau bisa
   bekerja atau ga" he wants an actual click-through test — click play, confirm
   currentTime advances — not just curl-200s. When the cloud browser tool
   blanks (pitfall 25), do a LOCAL Playwright click test:
   `playwright install chromium` once, then run `scripts/play-verify.py`
   (loads the watch page, waits for `iframe[title="player"]`, clicks the video
   center, reads `paused/currentTime/readyState`, counts ad-network hits,
   screenshots the instant the iframe appears). If provider anti-bot still
   blanks it from the datacenter IP (pitfall 25), report honestly: HTTP layer
   green + iframe-appeared screenshot, but the final click must be confirmed
   by the user from their residential IP. Never claim "video plays" without
   either a real click result or the user's own confirmation.
   **Anti-ad verification (2026-08-02)**: open the `/api/embed-proxy?url=...`
   URL DIRECTLY in the browser tool (it's a full HTML page), click the nested
   player iframe 2×, then count ad-network resource hits via
   `performance.getEntriesByType('resource')` — pass = 0 hits. The browser
   tool's cookie jar is unreliable with the site password gate (login state
   lost between navigations), but `/api/*` routes are public so testing
   through the proxy URL sidesteps the gate entirely.
1. Resolve test standalone (see pitfall 6) with the correct `{imdb, thetvdb, tmdb}`;
   check whether it returns `mode:direct` (vidlink) or `mode:embed` (provider).
2. Confirm the returned embed URL loads (curl -I: 200, no X-Frame-Options) or the
   direct URL isn't 429 (vidlink URLs expire — resolve fresh right before testing).
3. In browser: check provider switcher — swap 2embed / vidsrc-to / vidsrc-me.
4. If all providers fail for one title, it's provider-side; add/rotate providers in
   `lib/sources.js` EMBED_PROVIDERS.

## Provider switcher (already in watch page)

`/api/stream?force=embed&provider=N` returns `providers[]` list; UI renders
`season-tab`-style buttons per provider; clicking reloads the iframe with a new key.

## Chinese forum mining for stream sources (nodeloc / nodeseek, 2026-08-01)

Dez asked whether new film sources could be mined from `nodeloc.com` /
`nodeseek.com` (Chinese host/dev forums). Recipe that worked + source taxonomy:

```text
nodeloc.com  -> DISCOURSE, no Cloudflare. Free JSON API:
   search:  https://www.nodeloc.com/search/query.json?term=<urlencoded>   (200)
   topic:   https://www.nodeloc.com/t/<id>.json  -> post_stream.posts[].cooked
   Note: /search.json?q= returns 400; use search/query.json?term= instead.

nodeseek.com -> Cloudflare managed challenge ("Just a moment...") blocks curl
   AND headless browser (bot_detection_warning). Bypass:
   - Capsolver AntiCloudflareTask (see captcha-manager skill; key CAP-BD487656…
     had ~$95). createTask {type:AntiCloudflareTask, websiteURL, proxy, userAgent:
     Windows Chrome} -> poll getTaskResult -> solution.cookies.cf_clearance.
   - PITFALL: cf_clearance is IP-bound to the proxy used at solve time. curl
     through THAT proxy + cookie still returned 403 on every path (home, /api,
     /search). Browser session with injected cookie also 403 unless the browser
     egresses from the same IP. Don't burn balance iterating curl headers.

nodeseek.cc -> MIRROR domain, NO Cloudflare (200). Discourse-shaped but only a
   recent slice of posts:
   - posts.rss (50 latest), /search.json?q=<term> works but single-term only and
     shallow; /t/topic/<id> may 404 for older posts. Use it for "is anything new",
     not archive mining. Fallback: web_search "site:nodeseek.com <keyword>" surfaces
     post URLs + snippets (worked: post-99995, 108133, 87539, 232558, 215700).
```

**Stream-source taxonomy learned from these forums (useful for provider rotation):**
- **切片 (sliced CDN) stations** — ffzy / 量子(lz-cdn,cdnlz) / 暴风(bfeng) / 快看:
  free m3u8 directly, but inject ad segments; PHP ad-strip pattern exists
  (nodeloc topic 31379: regex-remove `#EXTINF:.*广告` blocks + re-serve cached
  m3u8; topic 47670/37897 量子非凡暴风 json 去广告 resolver source). This is the
  same class as vidlink: real m3u8, server-side resolve, strip ads.
- **官采 (official API)** — iQiyi/Youku/Tencent APIs: paid or license-gated.
- **MacCMS10** (`github.com/magicblack/maccms10`) — open-source video CMS; its
  ecosystem hosts many 采集/API stations.
- Demo endpoints found were dead (cachem3u8.2s0.cn 404, byteamone go.php echoes
  URL only, smhub.cc password-gated) — always live-test before integrating.

Full thread IDs + endpoints: `references/chinese-forum-stream-sources.md`.

## Sibling project: SpringMovie (Vercel Functions + SPA) — 2026-08-05

`agenticspring/springmovie` is the nonthon-zip style streaming web (Vercel
Functions `api/*.js` + single-file SPA `src/app.html`, no Next). Its fixes are
class-level lessons for any keyless streaming web — full detail in
`references/springmovie-sibling-learnings.md`. Highlights:

- **Vercel Hobby caps Serverless Functions at 12 per deployment.** Every
  `api/*.js` counts. SpringMovie hit 13 → deploy failed. Fix: merge related
  routes into one function and keep paths via `vercel.json` rewrites
  (`/api/x(.*)` → `/api/external?__path=x$1`). Count `ls api/` before pushing;
  MovieBox's many `app/api/*/route.js` routes are equally exposed.
- **Load-more buttons must NOT call `nav()`/`navigate()`** — navigate() does
  `window.scrollTo(0,0)`, so pagination scrolls to top. Call the render
  function directly (`onclick="renderX(...)"`).
- **Never auto-play unverified web embeds** — an unconditional iframe fallback
  can serve an unrelated film (nxsha.space played a random movie for "Ma mère").
  Manual button + honest label instead (same policy as the embed-proxy ads).
- **External HLS proxy pattern** for no-CORS / IP-bound-token CDNs (OK.ru
  vkuser.net, EffedUpMovies): resolve manifest server-side (OK.ru via the
  `videoembed` page, NOT the video page — fresh token), rewrite every playlist
  URI to the proxy, host allowlist, referer + UA. See the reference.
- **MacCMS `parseEpisodes` group selection** — score groups by label
  (正片/HD +, 预告/花絮 −) instead of `eps.length > best.length` (first-on-tie
  picks trailers → wrong film).
- **TMDB rated 18+ content**: `/discover/movie?certification_country=US&certification.gte=R`
  (R + NC-17) — complements the adult-stations route. `include_adult=true` is a
  separate flag for explicit titles.
- **OK.ru search is bot-walled** (canned results for every query); EffedUpMovies
  is WordPress and IS searchable (`?s=` + entry-title parse). Don't generalize
  the wall.

## Reference

- `references/springmovie-sibling-learnings.md` — SpringMovie sibling learnings
  (Vercel 12-function cap + rewrite consolidation, SPA scroll trap, unverified
  embed policy, external HLS proxy, EUM/OK.ru search, parseEpisodes scoring,
  TMDB certification filter, hidden-feature gate).

- `references/provider-notes.md` — tested provider endpoints + quirks as of 2026-08-01.
- `references/opensubtitles-subtitles.md` — keyless OpenSubtitles search/download
  pipeline (v1 legacy API, SubDownloadLink trick, srt→vtt conversion).
- `references/embed-proxy-anti-ad.md` — server-side embed proxy that strips ad
  scripts (tagivi/blackninja etc.) + shield injection; the anti-ad approach that
  REPLACED iframe sandbox (sandbox broke playback in user's real env).
- `references/vidlink-direct-player.md` — vidlink.pro WASM token resolver + hls.js
  direct player integration, pitfalls (global shims, URL expiry, cors-allowed).
- `references/movie-scraper-fork.md` — private fork of 4texas4/movie-scraper for
  side-by-side Vercel comparison: repo layout, shallow-clone push fix, single-file
  two-mode frontend pattern, TMDB key swap.
- `references/chinese-forum-stream-sources.md` — nodeloc/nodeseek mining recipe
  (Discourse API patterns, Capsolver AntiCloudflareTask cf_clearance IP-binding,
  nodeseek.cc mirror, 切片/官采 source taxonomy).
- `references/loklok-netpop-backend.md` — loklok.fun/.tv backend analysis:
  NetPop/RR.TV identity, API endpoints, currentTime+sign+aesKey signing
  (sign = MD5(base64url(AES(ts+json, uuid))), Turing Clouse aesKey).
- `references/maccms-resource-stations.md` — full MacCMS station harvest list
  (non-adult + adult separated), API pattern, verified-live table, ad-strip PHP
  pattern reference.
- `references/idlix-pentos-resolver.md` — IDLIX (z2.idlixku.com) Pentos gate
  claim/redeem flow: mediaId resolution (RSC flight regex + /api/movies fallback),
  play-info/claim/redeem endpoints, search shape, CDN (e2e.majorplay.net),
  EN/ID subtitle tracks, m3u8 EXT-X-MEDIA rewrite requirement.

- `scripts/play-verify.py` — Playwright click-through play verification for a
  watch page (wait for player iframe, click play, read paused/currentTime,
  pause->play ad-trap probe, ad-network count, screenshot at iframe-appear).
  Use when Dez demands a real click test and the cloud browser tool blanks
  (pitfall 25); `playwright install chromium` once, then run with URL + tag.
- `references/har-playback-diagnosis.md` — parse a user-supplied HAR to diagnose
  playback: status counters, provider-asset vs video-request split, ad-cloak
  timeline (proves provider injection), chrome-extension detection, and the
  vsembed/vidsrc findings + 2ba412b fix (pitfalls 26/27).

## Add new feature checklist

- [ ] Metadata change → `lib/metadata.js` (keyless endpoints only)
- [ ] Playback change → `lib/sources.js` + `/api/stream`
- [ ] `npm run build` must pass before push
- [ ] Push via agenticspring dual-PAT (`GITHUB_TOKEN_2`), never primary token
