# Resource Stations & Source Hunting (session detail, 2026-08-01)

Companion to the MovieBox skill. Everything here was verified live this session.

## 1. Chinese MacCMS resource stations (direct m3u8, no iframe)

Pattern: `GET {api}?ac=detail&wd=<query>` → `{list:[{vod_id, vod_name, vod_year, vod_remarks, type_id}]}`; then `?ac=detail&ids=<id>` → `vod_play_url`.

Play URL format: `播放源$https://...m3u8#第01集$https://...m3u8` — split on `#` for episodes, each part `label$url`. Series: `type_id === 2`. Some stations block keyword search (`code 1002 "Current API forbids keyword search"` — dbzy, maotai).

Verified live (search "spider-man"): 猫眼 `https://api.maoyanapi.top/api.php/provide/vod` → `https://play.maoyanplay.top/20250927/92AyAknq/index.m3u8` (Spider-Man 2). 暴风 → `v.fengbao11.com/...`, 量子 → `cj.lzcaiji.com`. English titles work on many stations.

Full 121-station list harvested from NodeLoc MoonTVPlus thread (topic 83312) — kept in `lib/resources.js` (56 non-adult + 22 adult). Adult stations use `?ac=detail&pg=N` for browse.

### m3u8 quirks
- Master playlist → variant playlist (`#EXT-X-STREAM-INF` → `/510kb/hls/index.m3u8`).
- **AES-128**: `#EXT-X-KEY:METHOD=AES-128,URI="/.../key.key"` — proxy the key URI or playback fails.
- 4000+ segments per movie; relative paths must be absolutized.
- Ad segments appear in sliced CDNs (ffzy/量子/暴风/快看) by name; strip in `rewriteM3u8()` (AD_SEGMENT_RE `/ad|gg|guanggao|logo|maoyan|ys_ad|cm/i`), drop with `#EXT-X-DISCONTINUITY`.

### PHP ad-strip model (NodeLoc topic 31379)
Free PHP: fetch playlist → `preg_match('/RESOLUTION=(.*)\n?(.*)/')` → replace `index.m3u8` with variant → cache MD5-named m3u8 → strip ad segments. Same logic as our `rewriteM3u8`.

## 2. OpenSubtitles v1 legacy (keyless subtitles)

```bash
curl "https://rest.opensubtitles.org/search/query-breaking-bad-s01e01" -H "User-Agent: TemporaryUserAgent"
```
- Works with NO key; response entries have `SubDownloadLink` (e.g. `https://dl.opensubtitles.org/en/download/src-api/vrf-.../filead/<id>.gz`) and `ZipDownloadLink`.
- **Use SubDownloadLink directly** — `GET https://rest.opensubtitles.org/download/{id}` returns 400 "method not specified".
- srt→vtt conversion needed for browser `<track>`/custom overlay: `00:00:01,000` → `00:00:01.000`.
- Sort Indonesian first (`lang === 'id'` / name contains "indonesia"), auto-apply in direct mode.

## 3. vidlink direct resolver (WASM)

- `lib/vidlink.js` boots WASM in serverless: set `globalThis.window/self/document` + `location` stub BEFORE eval'ing script.js; instantiate `fu.wasm`; `getAdv(id)` → 72-char token.
- API: `https://vidlink.pro/api/b/movie/{token}?multiLang=0` (or `/tv/{token}/{season}/{ep}`) with `Referer/Origin: https://vidlink.pro`.
- Response: `stream.playlist` (HLS) OR `stream.qualities.{360,480,720,1080}` mp4 with `requiresProxy: true`, `flags:["cors-allowed"]`. Pick highest quality. Play directly in `<video>` (cors-allowed) — do NOT proxy.
- **Caveat**: URLs have short `t=` expiry and bcdn may 429 datacenter IPs — client-side `onError` → auto-fallback to next provider.
- Vercel: `outputFileTracingIncludes` in next.config.mjs or the WASM won't ship.

## 4. Reverse-engineering streaming sites (how to find their source)

### LokLok (loklok.fun / loklok.tv) — self-hosted, NOT scraping
- loklok.fun: Nuxt, `apiBase: "https://api.loklok.fun"`.
- loklok.tv: Vue2 + Ironman template (`js1.dutun.cc/ironman-pc/1.3.4`), backend `web-api.netpop.app` + `alpha-web-api.rr.tv` = **NetPop/RR.TV** (same RR family as Dez's webnovel domains). `img.netpop.app`, `img.loklok.video`.
- Endpoints: `/cms/web/pc/{search/list,search/search,album/detail,download/urls}`. Requests need `currentTime` + `sign = MD5(AES_encrypt(data, uuid))` + `aesKey = Clouse(uuid)` (Turing obfuscation) — anti-bot too complex for casual scraping; not worth it.
- Lesson: self-hosted backends with signed APIs are high-effort/low-return vs MacCMS stations.

### IDLIX (z2.idlixku.com) — self-hosted with "Pentos" gate
- Next.js app, Cloudflare-protected; metadata via own `/api/{movies,series,search}`; TMDB images.
- Stream flow (reverse-engineered from `github.com/Teramoto669/idlix-scraper`):
  1. Warm CF cookies on `/` (got-scraping + CookieJar).
  2. Extract `mediaId` (UUID) from Next RSC payload (`self.__next_f.push(...)`).
  3. `GET /api/watch/play-info/{movie|episode}/{mediaId}` → `{gateToken, unlockAt, serverNow}`.
  4. Wait `unlockAt - serverNow` (~15s Pentos gate), then `POST /api/watch/session/claim {gateToken}` → `{redeemUrl, claim}`.
  5. `POST {redeemUrl} {claim}` → `{url: m3u8, subtitles:[...]}`.
- Reusable pattern: any "watch/session/claim + redeem" = gated self-host; add cache so repeated plays skip the gate.

### Forum research for sources
- **NodeLoc** (nodeloc.com): Discourse — `GET https://www.nodeloc.com/search/query.json?term=<urlencoded>` returns posts with topic_ids; `GET /t/{id}.json` gives cooked HTML. No Cloudflare.
- **NodeSeek** (nodeseek.com): Cloudflare managed challenge. Capsolver `AntiCloudflareTask` (key CAP-BD487656... had ~$95; needs sticky proxy + Windows Chrome UA) returns `cf_clearance` (IP-bound). Mirror `nodeseek.cc` is CF-free but only recent content; `search.json?q=` works there.
- Goldmine threads: NodeLoc topic 83312 (MoonTVPlus 121-station API list), topic 31379 (m3u8 ad-strip PHP), topic 55732 (扶风 parser billing system).
