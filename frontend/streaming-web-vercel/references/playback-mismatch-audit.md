# Playback content-mismatch audit (film A plays wrong content)

How to audit a streaming engine when the user reports "film A plays but the
content is not film A". Validated 2026-08-05 on SpringMovie (agenticspring/springmovie).

## Root causes to check, in order of likelihood

### 1. Dracin/MacCMS episode-group selection — CONFIRMED LATENT BUG (fixed)
`vod_play_url` packs play groups separated by `$$$`; each group is
`Ep$url#Ep$url`. Old parser picked the group with the most `.m3u8` entries and
on an EQUAL count kept the FIRST group:

```js
if (eps.length > best.length) best = eps;   // tie -> first group
```

If a station ships a teaser/trailer m3u8 group before the full-film group
(both 1 ep), the trailer plays. Fixed with label scoring:

```js
let score = eps.length * 10;
if (/正片|全集|完整|HD|高清|国语|粤语|中字|超清|蓝光/i.test(joined)) score += 20;
if (/预告|花絮|片花|宣传|广告|彩蛋|片段|精彩集锦/i.test(joined)) score -= 50;
if (score > bestScore) { bestScore = score; best = eps; }
```

Real data: dytt/uku/subo group 1 is a `/share/...` HTML page (filtered by the
`.m3u8` check) and group 2 is the real stream, so the old parser happened to
behave; the tie-break is a latent trap for stations that do trailer groups.
Also note: `.mp4` groups are deliberately skipped (hls.js player expects
`.m3u8`), which is fine for playback but means an mp4-only station yields
`no_playable_episodes`.

### 2. fetchWithMirror base vs mirror vod_id mismatch
`fetchWithMirror` tries base then mirror on error. If base and mirror are
DIFFERENT catalog domains, the same `vod_id` can resolve to different titles.
Probe: fetch page 1 from base and mirror, map `vod_id -> vod_name`, compare
intersection. uku base vs `api.ukuapi88.com` was 20/20 identical — safe there;
re-check per station before assuming.

### 3. Western/TMDB path via /api/stream (modiplay)
TMDB id is mapped to modiplay's internal file code by THEIR server. We cannot
verify content without playing, but we CAN sanity-check:
- Fetch the embed page URL that appears in `sources[].streamUrl` (the `ref=`
  query) and read `<title>` / `og:title`.
- Real result: Dune 2 embed title matched the request; Spider-Man embed title
  was generic ("Embed") — no mismatch evidence. Do not hard-fail on generic
  titles; use it as a warning signal only.
- `resolveSource` takes the FIRST `serve_m3u8` regex match in the player HTML —
  if an ad/preview server appears first in the page, that server wins. Prefer
  iterating all candidates and picking a playable one.

### 4. SpringStream (LokLok) media — unavailable ≠ wrong film
`action=media` commonly returns 404 `no_stream_url` (upstream `mediaUrl`
empty). That means "cannot play", NOT "wrong film". Report it as unavailable;
do not treat it as a mismatch.

### 5. Search type_id filter drops legitimate matches
Dracin `action=search` filters `String(it.type_id) === String(src.type)`.
Coverage loss, not mismatch — but if the wrong category id is passed it can
hide the correct film and surface a similar-titled one.

### 6. Title translation display mismatch (GTX)
`localizeItems` machine-translates Chinese titles to Indonesian. A wrong
translation shows a title that does not match the actual content, even though
the content follows `vod_id` correctly. Mitigation: keep `titleOrig` and show
it as a secondary line, or fall back to original on low confidence. This is a
DISPLAY risk, not a data-mapping bug.

## Audit recipe (run this first)

1. Probe `vod_play_url` structure across stations: scan page-1 records for
   `$$$` (multi-group) and trailer keywords (预告/花絮/片花) — find where group
   selection actually matters.
2. Base-vs-mirror id consistency probe (section 2).
3. For a reported-bad title: fetch detail by id, dump `epList`, then fetch the
   raw m3u8 master and compare the CDN path to the station's normal pattern.
4. For western titles: fetch the modiplay embed page and read its title.
5. Syntax-check + verify local server still parses list/detail after any
   parser patch, then commit author=agenticspring and check GitHub commit
   status for Vercel success.

## Verification after the parseEpisodes fix
- `node --check api/dracin.js`
- `/api/dracin?action=list&source=dytt|uku|subo&page=1` still returns items
  with correct `episodes` count
- `/api/dracin?action=detail&source=uku&id=<id>` picks the 720P/正片 group
  label, not the share page
