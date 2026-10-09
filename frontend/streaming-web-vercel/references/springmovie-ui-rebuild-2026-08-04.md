# SpringMovie UI Rebuild 2026-08-04

Session detail for the full UI rebuild of the SpringMovie pure-Functions SPA
(`/root/springmovie`, `agenticspring/springmovie`, served from `src/app.html`
by `api/index.js`). Complements `vercel-functions-rebrand.md`.

## What happened

- User asked to redesign the UI so it no longer looks like NXR/Nonthon:
  "modern clean, not AI slop, no emoji 🔥, buat logo sendiri" and to add a
  "Fitur tab anime".
- The rewrite was delegated to a leaf subagent; the delegation later reported
  "outcome unknown" (owner exited before recording a terminal result), but the
  child HAD already written the 2918-line `src/app.html` (146 KB) and verified
  syntax + local 200. Lesson: check file mtime/size + live transcript before
  assuming failure.

## Anime tab recipe (validated live)

```js
const ja = { with_original_language: 'ja' };
tmdb('/discover/tv', { page: 1, with_genres: 16, sort_by: 'first_air_date.desc', 'first_air_date.lte': todayISO(), 'vote_count.gte': 5, ...ja });
tmdb('/discover/tv', { page: 1, with_genres: 16, sort_by: 'popularity.desc', ...ja });
tmdb('/discover/tv', { page: 1, with_genres: 16, sort_by: 'vote_average.desc', 'vote_count.gte': 100, ...ja });
```

Rows: Baru Rilis (12), Populer (20), Rating Tinggi (20). Stamp
`media_type = 'tv'` on results so `renderCards`/`renderDetail`/player reuse
works. Wire-up: desktop nav link `id="nav-anime"` with
`data-nav='{"view":"anime"}'`, mobile sheet item, `case 'anime'` in the
navigate switch, and `anime: 'nav-anime'` in NAV_MAP.

## CDP stale-HTML trap (cost ~3 false-failure cycles)

`api/index.js` serves the SPA with `Cache-Control: public, max-age=60` (from
the zip). After a rewrite, Chromium kept serving the OLD app from HTTP cache:
"🔊 Drama ID" and other old strings appeared in DOM even though grep/curl of
the on-disk + served file showed they were gone. Fixes that worked:

- `Network.setCacheDisabled` + `Page.navigate` to `/?v=<unix-ts>`.
- Ground-truth check with `curl -s 'http://host/?nocache=1'` and grep for the
  old/new markers (the server itself was correct the whole time).

## Emoji scan (whole repo)

The only emoji in the final codebase was `🔊` in an API label:
`api/dracin-id.js` source label `'🔊 Drama ID'`. A rewrite that only cleans
HTML misses emoji in the data layer. Scan all text files:

```python
emoji_re = re.compile(r'[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]')
```

(Arrows `→` in comments are acceptable; real emoji in UI strings/labels are not.)

## Design language Dez approved

- Custom inline-SVG logo: geometric sakura petal mark (5 rotated ellipses +
  center dot) + wordmark `Spring<span class="wm-accent">Movie</span>`.
- Tokens: `--bg:#0a0a0e --surface:#16161d --border:#24242e --primary:#e692af
  --text:#f4f4f6 --dim:#9a9aa8`; system font stack; hairline borders; subtle
  hover lift; cards radius 10-14px; poster aspect 2/3; SVG star rating.
- No emoji anywhere; Indonesian labels (Beranda, Terbaru, Film, Series,
  Anime, Dracin, SpringStream, Trending, Platform, About).

## Verification evidence (final)

- Local: home 78 cards, movie 72, trending 60, search 40, dracin 47 cards
  (label clean), anime 12/20/20, about OK.
- `node --check` on extracted inline `<script>`: OK.
- Repo-wide emoji scan: NONE.
- Live Vercel: deploy success (GitHub status API), `nav-anime` present,
  `#e692af` present, no emoji, no Nonthon/NXR strings.
- Commit: `0408fe9 Redesign SpringMovie UI: modern clean SPA + Anime tab`
  (author+committer `agenticspring`).
