# OK.ru (Odnoklassniki) HLS source — resolver + proxy recipe

Validated 2026-08-05 on `https://ok.ru/video/262156847692` (SpringMovie
`/api/okru`). Goal: let a user paste an OK.ru video link and play it as NATIVE
HLS in our hls.js `<video>` — no iframe.

## Why a server proxy is mandatory

- OK.ru embeds its player via a tokenised `hlsManifestUrl` pointing at the
  CDN `ok6-*.vkuser.net`.
- CDN tokens are bound to the requesting server's IP (`srcIp=82.39.206.183`
  appears in the signed URL) AND the CDN sends no CORS headers. A browser
  cannot fetch the manifest, variant, or segments directly.
- Therefore: resolve server-side, then proxy EVERY playlist URI through our
  route so the browser only ever talks to our origin.

## Resolution (the videoembed trick)

- `https://ok.ru/video/<id>` page exists, but its token can return
  **HTTP 400** on the CDN (`video.m3u8?cmd=videoPlayerCdn...`).
- `https://ok.ru/videoembed/<id>` (same id) carries a **fresh working token**
  (`srcAg=UNKNOWN`) — use THIS page as the source of truth.

Extraction from the raw HTML (the JSON is double-escaped):

```
marker = 'hlsManifestUrl'
i = html.indexOf(marker)
j = html.indexOf('https://', i)          // start of URL
k = html.indexOf('\\&quot;', j)          // end of URL (literal backslash-backslash-quot)
raw = html.slice(j, k === -1 ? j + 2000 : k)
url = raw.replace(/\\\\u0026/g,'&').replace(/\\u0026/g,'&')   // decode query separators
```

## Playlist rewrite (critical)

Master playlist contains variant URIs that are absolute CDN URLs; variant
playlists contain RELATIVE segment names (`LOWEST00000.ts`). Neither is
browser-fetchable. Rewrite every non-`#` line to:

```
/api/okru?url=<encodeURIComponent(new URL(line, base).href)>
```

Then master → variant → segment all round-trip through the route. Segments
are binary; return them as `video/mp2t` (they start with MPEG-TS sync byte
`0x47`).

## Route shape (api/okru.js)

- `?u=<ok.ru video URL>` → resolve mode: return
  `{ success, streamUrl: '/api/okru?url=' + encodeURIComponent(manifest) }`.
- `?url=<vkuser.net m3u8>` → proxy mode: fetch with
  `User-Agent` + `Referer: https://ok.ru/`, if `#EXTM3U|#EXT-X` → rewrite +
  serve `application/vnd.apple.mpegurl` (no-store); else binary segment
  (cap ~30MB, `video/mp2t`, cache 1h).
- SSRF guard: host allowlist regex `/(^|\.)(ok\.ru|okcdn\.ru|vkuser\.net|mycdn\.me)$/i`
  on the proxy target. Reject everything else with 403.

## Frontend wiring

- Player stream-error state gets:
  `<input id="okruInput" placeholder="Tempel link OK.ru (https://ok.ru/video/...)"/>`
  + `<button onclick="playOkru()">Putar dari OK.ru</button>`.
- `playOkru()`: `fetch('/api/okru?u=' + encodeURIComponent(input))` →
  on success set `_sources = [{ name:'OK.ru', streamUrl: d.streamUrl, subtitles: [] }]`
  → `_playSource(0)` (reuses the existing HLS path; quality select fills from
  hls.js levels automatically).
- Because tokens expire (hours), always resolve fresh per play; never cache
  the resolved URL long-term. `Cache-Control: no-store` on resolve.

## Verification chain (do this before shipping)

```
resolve   → 200, success:true, streamUrl=/api/okru?url=...
master    → 200, #EXTM3U, 3 variants (lowest/low/higher) — ALL proxied paths
variant   → 200, playlist of N segments — ALL proxied paths
segment   → 200, first byte 0x47 (MPEG-TS), size matches a real .ts chunk
```

## Search is bot-blocked — keep OK.ru manual

Tested 2026-08-05: OK.ru's server-side search endpoints are bot-blocked for
anonymous requests. `/video/search/ajax?st.query=`, `/video?st.query=`,
`m.ok.ru/video/search` ALL return the same canned result set for ANY query
(searchQuery echo empty; first result always an "Ajax…" video). External
search engines (DuckDuckGo html, Bing) are rate-limited/unstable for server
scraping. So do NOT build auto-search-by-title against OK.ru.

Manual UX that works:
- Player error state: paste-link input + "Putar dari OK.ru" (resolve → native HLS).
- "Buka Pencarian OK.ru" button:
  `window.open('https://ok.ru/video?st.query=' + encodeURIComponent(currentTitle), '_blank')`
  — user searches in their own browser (search works there) and pastes the link back.

Dev server note: `tools/dev-server.mjs` has a static `routes` map — add
`'/api/okru': './api/okru.js'` and RESTART the dev server, otherwise new
routes 404 ("not found" from the dev shim).
