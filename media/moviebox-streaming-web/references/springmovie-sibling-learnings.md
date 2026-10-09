# SpringMovie (sibling project) — learnings for keyless streaming webs

SpringMovie = `agenticspring/springmovie` (Vercel Functions + single-file SPA in
`src/app.html`, NOT Next.js — the "nonthon-zip" style). MovieBox is Next.js.
These lessons transfer to any keyless streaming web on Vercel.

## Vercel Hobby plan: 12 Serverless Functions cap (2026-08-05)

Vercel Hobby deployments fail with:

```
No more than 12 Serverless Functions can be added to a Deployment on the Hobby plan.
```

Every `api/*.js` file (Vercel Functions) counts. SpringMovie hit 13 (index,
login, logout, stream, subs, sub, dracin, dracin-id, dracin-img, springstream,
okru, eum, resolve) → deploy failed. FIX: consolidate several routes into ONE
function and keep the public paths via rewrites in `vercel.json`:

```json
{
  "source": "/api/okru(.*)",
  "destination": "/api/external?__path=okru$1"
}
```

Dispatch inside `api/external.js` on `req.query.__path`, falling back to
parsing `req.url` pathname (dev-server passes the original path; Vercel rewrite
may replace it). Shared helpers (getText/getBuffer/rewriteToProxy) live once.
Function count went 13 → 11.

RULE: never add a new `api/*.js` without merging/removing another. Check the
count with `ls api/` before pushing. MovieBox with many `app/api/*/route.js`
routes is equally exposed — consolidate before adding routes.

## SPA load-more button jumps to top (scroll bug)

If every page change goes through `navigate()` and `navigate()` does
`window.scrollTo(0,0)`, a "Muat lebih banyak" button that calls `nav({...})`
will scroll the page to the top on every pagination click. Fix: pagination
buttons call the render function DIRECTLY (e.g. `onclick="renderGenrePage('adult','movie',2)"`),
never `nav()`. Applies to every view with an append-mode render (list/genre/
provider/dracin/springstream).

## Player: never AUTO-play unverified web embeds

Symptom: user clicks a title (e.g. "Ma mère" S1E1), the direct stream returns
no_source, and the player automatically falls back to an unverified web iframe
(nxsha.space) which serves an unrelated film (Indian movie). Root cause: the
client appended `IFRAME_SOURCES` to `_sources` unconditionally. Fix: no
automatic iframe fallback. Show an honest error + a MANUAL "Coba Sumber Web"
button (labeled "konten bisa tidak sesuai"). Same policy as MovieBox's
anti-ad stance: an unverified fallback that plays wrong content is worse than
an error.

## External HLS proxy pattern (no-CORS / IP-bound tokens)

Some sources (OK.ru `ok6-*.vkuser.net`, EffedUpMovies `s2.vvvv.effedupmovies.com`)
serve HLS that the browser cannot fetch directly:
- CDN sends no `Access-Control-Allow-Origin`, or only to its own origin.
- Tokens bind to the SERVER IP (`srcIp=` in the OK.ru URL), so the manifest must
  be fetched and relayed from the same server that resolved it.

Pattern (both `/api/okru` and `/api/eum`; SpringMovie merged both + resolve into
`api/external.js`):
1. Resolve: fetch the page server-side, extract the `.m3u8` URL:
   - OK.ru: `https://ok.ru/videoembed/<id>` (NOT the video page — videoembed
     gives a FRESH token that works; the `/video/<id>` page token 400s), find
     `hlsManifestUrl`, take the `https://` substring up to the next `\&quot;`,
     unescape `\\u0026`→`&`, `\\/`→`/`.
   - EffedUpMovies: page HTML, regex first `https?://...\.m3u8`.
2. Proxy: `?url=<manifest-or-segment>` → fetch with UA + Referer
   (ok.ru / effedupmovies.com), rewrite EVERY non-# line of the playlist to
   `/api/<route>?url=<absolute>` (so the browser never touches the CDN), serve
   segments as `video/mp2t`, cap segment size (~40MB), `Cache-Control: no-store`
   on playlists, `private, max-age=3600` on segments.
3. SSRF guard: host allowlist regex (`(^|\.)ok\.ru$` family / `*.effedupmovies.com`),
   403 otherwise. Range support: server-side fetch ignores Range; hls.js is fine
   with full segments.

Verified: master 200 → variant 200 → segment 200 with MPEG-TS sync byte 0x47.

## OK.ru search is bot-walled server-side

All OK.ru search endpoints (`ok.ru/video?st.query=`, `/video/search/ajax`,
`m.ok.ru`, `/dk` GET/POST with warm cookies) return IDENTICAL canned results
for every query to anonymous server clients (title = generic "Социальная сеть
Одноклассники"). Search engines from datacenter IPs: DDG html/lite
rate-limited after 1 request, Bing soft-blocked, Google `emsg=SG_REL`
(JS-required). Conclusion: don't build server-side OK.ru title search; the
working path is: user searches in their own browser (native OK.ru search or
Google `site:ok.ru/video "<title>"`) → pastes the link → resolve via the
videoembed flow.

## EffedUpMovies auto-search (WordPress `?s=`)

Unlike OK.ru, EffedUpMovies IS searchable server-side — it's WordPress:
`https://www.effedupmovies.com/?s=<q>` → parse `<h2 class="...entry-title...">
<a href="..." title>`, extract title + url + year `(\d{4})`. Return candidates;
player adds them to the server bar ("EUM · Ma Mere (2004)") — click → resolve →
play. Manual paste field stays for exact links. Lesson: check whether a source
is WordPress/CMS before assuming search is blocked — the OK.ru wall does not
generalize.

## MacCMS parseEpisodes: score play groups, don't take the first

`vod_play_url` packs multiple play groups separated by `$$$`, entries by `#`,
label/url by `$`. Old code `if (eps.length > best.length) best = eps` keeps the
FIRST group on a tie — if group 1 is a trailer/teaser, the wrong content plays.
Score groups:
```
score = eps.length*10
+20 if label matches 正片/全集/HD/高清/国语/粤语/中字
-50 if label matches 预告/花絮/片花/宣传/广告/彩蛋
pick max score; ties keep the earlier group
```
Also only accept `.m3u8` entries (some groups are HTML share pages — filtered
out naturally). This is the "film A plays wrong film" bug class.

## TMDB adult-rating filter (complement to adult stations)

TMDB has no 18+ genre tag; for RATED content (not the `adult` flag) use
discover with US certification:
`/discover/movie?certification_country=US&certification.gte=R` (US cert order
G < PG < PG-13 < R < NC-17, so gte=R = R + NC-17). Returns ~19k titles.
`include_adult=true` is a separate flag for explicit content (add it to search
and discover params to include adult-flagged titles). MovieBox's "TMDB has no
18+/adult genre" claim is still true for a genre TAG; certification filter is
the rated-content route.

## Hidden feature gate pattern

User asked for a secret 18+ entry: remove the card from the Genre menu, and in
the search `oninput` handler, if `q.toLowerCase() === '18+u'`, clear the input
and `navigate('genre', {g:'adult', kind:'movie'})` instead of running a TMDB
search. Generic pattern: search-box secret codes for hidden views.
