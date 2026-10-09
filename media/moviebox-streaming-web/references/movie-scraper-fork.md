# agenticspring/movie-scraper — private vidlink-only fork (2026-08-01)

Dez wanted a private deployable copy of `4texas4/movie-scraper` ("Zenith Movies")
to compare on Vercel. Created `agenticspring/movie-scraper` (PRIVATE, main).

## Repo layout (as forked + customized)

```text
index.html      -> single-file UI (browse mode + player mode), TMDB key swapped
api/index.js    -> Vercel serverless: ?url= (HLS proxy w/ rewrite) or ?id=&s=&e= (vidlink resolve)
api/script.js   -> Go WASM runtime shim (eval'd) — from upstream
api/fu.wasm     -> 2.4MB WASM token generator — from upstream
package.json    -> libsodium-wrappers only
vercel.json     -> rewrites: /api -> /api/index.js, /api/(.*) -> /api/index.js
example.gif     -> upstream demo (kept)
```

Deploy: import in Vercel, no config. Use: `https://<app>.vercel.app/?id=550`
(movie) or `?id=456&s=1&e=1` (TV episode).

## Git pitfalls when forking a public repo to private (both hit for real)

1. **Shallow clone (`git clone --depth 1`) can't push.** `git push` fails with
   `remote: fatal: did not receive expected object <sha>` / `remote unpack failed:
   index-pack failed` because the local repo lacks the full object graph. **Fix:
   re-init instead** — `rm -rf .git && git init -b main && git add -A && git
   commit && git push -u origin main`. Do this instead of deepening the clone.
2. **`gh repo create --source . --push` leaves origin pointing at upstream.**
   It creates the repo but errors `Unable to add remote "origin"` when a remote
   already exists (the clone's origin = 4texas4). **Fix:** `git remote remove
   origin`, then `git remote add origin
   https://x-access-token:${GITHUB_TOKEN}@github.com/agenticspring/movie-scraper.git`,
   then push. The repo's default branch on GitHub is `main` — use `git init -b main`.

## Frontend: single-file two-mode UI (index.html)

When Dez says "buatin UI kayak moviebox" for this repo, the pattern is one
`index.html`, no build step:

- **No `?id` param → browse mode**: sticky header (logo + search input),
  TMDB rows (trending/all/day, movie/popular, movie/now_playing, tv/popular,
  movie/top_rated) rendered as horizontal scroll rows of poster cards, plus a
  search grid (`/search/multi` filtered to movie|tv, 400ms debounce).
- **`?id` param → player mode**: fullscreen `<video>` + hls.js; loader with
  blurred TMDB backdrop (via `wsrv.nl/?url=<encoded tmdb image>&bg=black&blur=3`);
  Back button `‹` uses `history.back()`.
- Cards: `mediaCard(m)` derives title/type from `title|name`, `first_air_date`
  for TV, `poster_path` from `https://image.tmdb.org/t/p/w500`; clicking a movie
  goes `?id=<tmdb>`, a TV show goes `?id=<tmdb>&s=1&e=1`.
- **TMDB key**: upstream hardcodes someone else's key in index.html — always
  replace with Dez's key (`56ebc0698d0662c798faf8dc529305ab`) before pushing to
  a repo Dez owns. Key is client-side-safe, repo is private.
- Player: upstream `play()` only used hls.js for EVERYTHING; for `.mp4` URLs set
  `video.src` directly (or hls.js will fail on non-m3u8). Use `Hls.isSupported()
  && /m3u8/i.test(rawUrl)` to branch.
- `vercel.json` rewrite is required or `/api?...` 404s: both `/api` and
  `/api/(.*)` → `/api/index.js`.

## Verification after push

```bash
gh api repos/agenticspring/movie-scraper/git/trees/main?recursive=1 --jq '.tree[].path'
gh api repos/agenticspring/movie-scraper/contents/index.html --jq '.size'   # expect ~13.5k
git ls-remote https://github.com/agenticspring/movie-scraper.git HEAD
```

Vercel needs the GitHub account connected to see the private repo; user deploys
it themselves. Redeploy after each push (`8d53884` → `af37e75` added the UI).
