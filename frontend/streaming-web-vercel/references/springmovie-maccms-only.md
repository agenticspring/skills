# SpringMovie MacCMS-only architecture notes

> **SUPERSEDED 2026-08-04**: `/root/springmovie` was fully replaced with the
> `nonthon-main.zip` frontend (pure Vercel Functions: `api/*.js` + `src/app.html`
> SPA — no Next.js). Global search = TMDB (MovieBox key), tabs Dracin=MacCMS and
> SpringStream=LokLok. Open access, no gate. Sakura palette `#e692af`.
> Vercel deploy gotcha: project was locked to Next.js preset; fix is
> `vercel.json` `"buildCommand": "npm run vercel-build"` + package.json
> `vercel-build` script (syntax checks). Keep commit author/committer
> `agenticspring`. The station/category mapping below still applies to the
> Dracin/MacCMS tab.

Use when Dez asks to rebuild SpringMovie/Nonthon-style streaming around Chinese resource-station APIs instead of TMDB/provider embeds.

## Durable user expectation

- Dez expects SpringMovie to behave like Nonthon for playback/subtitles: direct HLS/video first, native `<video>`/hls.js where possible, and a visible CC dropdown only when SpringMovie controls a local `<video>`.
- If the UI shows `2embed`, `vidsrc`, or `CC via player`, say clearly that this is iframe/provider mode and cannot be made 1:1 with Nonthon native subtitle controls.
- If Dez asks to “tanya dulu”, answer the architectural state and trade-off first; do not continue large rewrites until he confirms direction.

## MacCMS-only target shape

Primary UI/catalog should come from MacCMS/苹果CMS resource stations (`/api.php/provide/vod`) rather than TMDB rows or provider iframe catalogs.

Verified core station set used for SpringMovie:

| key | name | API | note |
|---|---|---|---|
| `ffzy` | 非凡 | `https://api.ffzyapi.com/api.php/provide/vod` | default/latest, broad genre pages work |
| `dytt` | 电影天堂 | `http://caiji.dyttzyapi.com/api.php/provide/vod` | film-heavy fallback |
| `ikun` | iKun | `https://ikunzyapi.com/api.php/provide/vod` | search often returns western titles |
| `uku` | U酷 | `https://api.ukuapi88.com/api.php/provide/vod` | mixed catalog |
| `bfzy` | 暴风 | `https://bfzyapi.com/api.php/provide/vod` | largest catalog, type ids differ |
| `zuida` | 最大 | `https://api.zuidapi.com/api.php/provide/vod` | large catalog |
| `hongniu` | 红牛 | `https://www.hongniuzy2.com/api.php/provide/vod` | film categories work |
| `douban` | 豆瓣 | `https://caiji.dbzy5.com/api.php/provide/vod` | film/category rich |

## Category mapping pitfalls

Do not assume umbrella `t=1` or `t=2` works everywhere. Several stations return empty or tiny umbrella categories. Prefer concrete verified categories:

- `ffzy`: action `t=6`, comedy `7`, romance `8`, sci-fi `9`, horror `10`, drama movie `11`, war `12`, domestic series `13`, HK `14`, KR `15`, western series `16`, anime `4`, variety `3`.
- `dytt`: film genre ids mostly mirror ffzy (`6..16`), umbrella `t=2` is tiny.
- `bfzy`: film `20`, action `21`, comedy `22`, horror `23`, sci-fi `24`, romance `25`, drama `26`, series `30..34`.
- `hongniu`: action `5`, comedy `6`, romance `7`, sci-fi `8`, horror `9`, drama `10`, series `12..15`; umbrella film `1` can be tiny.
- `douban`: documentary `5`, action `6`, romance `7`, comedy `8`, sci-fi `9`, horror `10`, drama `11`, war `12`, series `13..14`.

For a general “Film” row, aggregate concrete film categories such as action/comedy/romance/sci-fi/horror/drama/war instead of one umbrella category.

## Implementation pattern

- Centralize station/category registry in a single server module (e.g. `lib/maccms.js`) and have `/api/home`, `/api/search`, `/api/browse`, and `/api/explore` call it.
- Normalize every card to include `{ dracin: true, src, vodId, media_type, isTv }`.
- Route primary cards to `/dracin/${encodeURIComponent(src)}/${vodId}` so playback uses MacCMS direct HLS/player.
- Keep TMDB/provider iframe routes only as legacy/fallback; they should not power the primary home/search/browse UI in MacCMS-only mode.
- Search results must only return station APIs that the Dracin/detail route allowlists; otherwise search cards link to unplayable/rejected routes.
- Preserve SSRF protections: arbitrary custom station URLs should not be accepted by server routes that fetch URLs.

## Verification checklist

- `npm run build` passes.
- `/api/home` returns only MacCMS rows (e.g. MacCMS Terbaru, Film, Action, Horror, Sci-Fi, Romance, Series, Anime) with non-empty items.
- `/api/browse?type=movie&page=1` returns MacCMS `Film` items.
- `/api/browse?type=tv&page=1` returns MacCMS `Series` items.
- `/api/explore` returns MacCMS station ids and MacCMS genre ids, not TMDB platform/country metadata.
- `/api/search?q=<known Chinese title>` returns MacCMS items with `src` and `vodId`.
- Browser home cards and hero play links point to `/dracin/...`, not `/watch/...` or TMDB detail routes.
- One sample `/api/dracin?action=detail` and `action=episode` resolves a playable HLS/mp4 URL and proxied stream URL.
- Before pushing to Vercel-linked `agenticspring/springmovie`, ensure both commit author and committer are `agenticspring <307995144+agenticspring@users.noreply.github.com>`; Vercel may reject commits authored by DezXBT for this project.
