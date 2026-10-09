# Multi-source resolver for the watch player (/api/resolve)

Validated 2026-08-05 (SpringMovie). User flow requested: search a title → open
detail → press "Nonton" → the player auto-discovers candidate sources and shows
a server bar so the user picks where to play (modiplay / MacCMS / OK.ru), and
for OK.ru picks between same-title uploads.

## What was actually built

`GET /api/resolve?title=&year=` searches MacCMS short-drama stations
(dytt/ffzy/ikun/uku) by title + year:

- fetch `{base}?ac=detail&wd=<title>` (fall back to `src.mirror` if the base
  errors), parse JSON `list`.
- keep rows where `String(type_id) === String(src.type)` (station's own type),
  `vod_pic` present, `parseEpisodes(vod_play_url).length > 0`.
- year filter: if both candidate year and query year exist, allow ±1.
- cap 2 per station, 6 total; return `{src, id, title, year, remarks, epCount}`.

Frontend (watch player `loadStream`):

- after `/api/stream`, fetch `/api/resolve?title=&year=` (title/year come from
  the TMDB detail fetched in `renderPlayer`).
- append each MacCMS candidate to `_sources` as
  `{ name: 'MacCMS · <short title>', mac: { src, id } }`.
- `_playSource(i)`: if `src.mac` → `navigate('dracinPlayer', {src, id, ep:1})`
  (reuses the Dracin player with its full episode grid); if `src.okru` →
  `_playOkruUrl()`; else iframe/native HLS as normal.
- `renderServerBar()` labels buttons with `s.name` (not "Server N").

## Coverage reality (important expectation-setting)

- MacCMS short-drama stations ONLY index Chinese short-drama titles. English or
  western titles (e.g. "Ma mère", "Spider-Man: No Way Home") return **0 MacCMS
  candidates** — that is expected, not a bug. A Chinese short-drama title like
  `我只想种地，修仙界却奉我为神` resolves to dytt+ffzy matches (53 eps each).
- OK.ru was dropped from server-side auto-search — see okru-hls-source.md
  (search endpoints bot-blocked). OK.ru stays manual: paste link + "Buka
  Pencarian OK.ru" button (`window.open('https://ok.ru/video?st.query=' +
  encodeURIComponent(title))`) that pre-fills the current title.

## Testing

```bash
curl -s 'http://localhost:8911/api/resolve?title=<urlencoded title>&year=2026'
# expect {"success":true,"maccms":[{"src":"dytt","id":...},...]}
```
