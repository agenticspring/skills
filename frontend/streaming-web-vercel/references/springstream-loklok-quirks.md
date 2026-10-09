# SpringStream (LokLok) upstream quirks — probed 2026-08-05

SpringMovie's SpringStream tab = LokLok proxy (`/api/springstream.js`).
Endpoints: web API `https://api.loklok.fun` (crypto-signed, `lib/spring-crypto.js`)
+ mobile API `https://ga-mobile-api.loklok.tv` (no crypto, okhttp UA).

## screen/list params whitelist (the "sign error" trap)

`POST /cms/pc/search/screen/list` with body
`{ size, params, searchScreeningName, order: 'count' }`.

Probe matrix (all with valid signed headers, same device id):

| params | searchScreeningName | result |
|---|---|---|
| `MOVIE` | `Movie` | `00000` Success, movies |
| `''` (empty) | `All` | `00000` Success, movies AND series |
| `TV` | `TV Series` | `B0001` `sign error!` |
| `DRAMA` | `TV Series` | `B0001` `sign error!` |
| `MOVIE,DRAMA` | `All` | `B0001` `sign error!` |
| `MOVIE,TV` / `MOVIE,SETI` / full list | any | `B0001` `sign error!` |

`B0001 sign error!` is a server-side whitelist rejection, NOT a crypto bug —
the signature is fine (MOVIE works). Conclusion: TV-only or multi-category
params are impossible to request. Request `params:''` + `searchScreeningName:'All'`
and filter by `domainType` (`0`=movie, `1`=tv) in the proxy.

List items expose `domainType`, `coverVerticalUrl`, `id`, `name`, `ifErotic`,
`ifSameSex` — but NOT `category`/`subType`, so filtering must use `domainType`.

## Verified results

- `type=movie` → 30 items (The Last Breath, Secretly Greatly, Alex Of Venice...)
- `type=tv` after fix → filtered series (Adulting Season 1, Gqeberha: The
  Empire Season 2, Shaka iLembe Season 1, Meet You at the Blossom...)
- `type=all` → mixed 30.
- LokLok DOES provide movies — user question "itu loklok ga menyediakan film
  kah" was a symptom of the broken TV/All tabs (502), not missing content.

## Other endpoints

- Detail: `GET /cms/web/movieDrama/get?id=&category=` (mobile API) → `episodeVo`
  with `definitionList` + `subtitlingList`. category: 0=movie, 1=tv.
- Search: `POST /cms/pc/search/searchWithKeyWord` `{searchKeyWord, size, sort,
  searchType}`. Most queries work; "squid game" returned [] — do not assume
  full coverage.
- Stream: `GET /media/pc/getPlayInfo` via web API (crypto)
  `{contentId, category, episodeId, definition}` → media URL + subtitles.
  **BROKEN FOR ALL CONTENT (probed 2026-08-05).** Every movie AND every series,
  every definition (GROOT_HD/SD/LD/FD), returns
  `{"msg":"KDF23445 Resource-transcoding.","code":"FDLSxl1000129"}` — upstream
  says the resource is still transcoding / region-gated, so `mediaUrl` is empty
  and the proxy returns 404 `no_stream_url`. SpringStream is therefore
  CATALOG-ONLY: browse + detail + episode lists work, playback never starts.
  Do not waste time re-probing per title — the failure is uniform.

## Code changes that fixed it (api/springstream.js)

```js
let params = 'MOVIE'; let screenName = 'Movie';
if (type === 'all') { params = ''; screenName = 'All'; }
else if (type === 'tv') { params = ''; screenName = 'All'; }
// ... post ...
let items = (data.data || []).map(mapListItem).filter(it => it.id && (it.coverVerticalUrl || it.coverHorizontalUrl));
if (type === 'tv') items = items.filter(it => String(it.domainType) === '1');
else if (type === 'movie') items = items.filter(it => String(it.domainType) === '0');
```
plus `domainType: it.domainType ?? 0` in `mapListItem`.

## Anime: category exists but is EMPTY

Probed 2026-08-05 (user: "loklok ada streaming anime ga?"). `params=ANIME` +
`searchScreeningName=Anime` returns `00000` Success with **0 items** at any
size/order (30/60, count/new/score). Searches for anime titles also fail:
"naruto"/"Doraemon" → `00000` with 0 items; "one piece"/"detective conan" →
`B0001 sign error`. Other categories DO have content: `COMIC` (Champignon
Witch, Emmy&GooRoo), `VARIETY` (The Mommy Club, RHOL). Conclusion: LokLok's
anime shelf is empty (region-gated or never populated) — don't promise anime
from SpringStream. SpringMovie's Anime tab uses TMDB discover
(`with_genres: 16` + `with_original_language: 'ja'`) + modiplay/auto-resolve
instead, which is the correct approach.

## Why Dracin (MacCMS) plays but LokLok doesn't — architecture

User question "Tapi kok bisa play dracin?" (2026-08-05). The two sources are
architecturally opposite:

| | Dracin (MacCMS) | SpringStream (LokLok) |
|---|---|---|
| Stream URL | Public direct m3u8 on station CDN | Generated per-request by `getPlayInfo` API |
| Auth/region | None | Region + session gated ("Resource-transcoding") |
| CORS | ikun: `*`; ffzy/uku/dytt: 403 on datacenter IP but fine from residential browser | n/a (no URL ever reaches the browser) |
| Playable | ✅ (hls.js fetches from user's browser) | ❌ catalog-only |

Key insight: MacCMS `vod_play_url` contains REAL CDN URLs the browser can
fetch directly (some CDNs block datacenter IPs with 403 but allow residential
IPs + send CORS `*` on 200 — ikun returns 200/CORS `*` even from a server IP).
LokLok never exposes a public CDN URL; the stream is locked behind the API.
So a Dracin-m3u8 link that 403s from a VPS still plays in the user's browser,
while LokLok playback is broken for everyone.
