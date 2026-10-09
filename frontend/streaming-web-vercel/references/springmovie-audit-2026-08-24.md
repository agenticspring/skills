# SpringMovie full-stack audit — 2026-08-24 (playback, subtitles, UI)

Verified live end-to-end against https://springmovie.vercel.app/. Repo: agenticspring/springmovie,
pure Functions (`api/*.js`) + single-file SPA `src/app.html`, Vercel Hobby 12-fn cap,
open access (`lib/auth.js` requireAuth = true always).

## Playback source matrix (probed live)

| Source | Media CDN | CORS | Datacenter IP | Verdict |
|---|---|---|---|---|
| modiplay servers ×5 (StreamHG, EarnVids, RPMShare, UpnShare, StreamP2P) | vibuxer/dramiyos via proxy.php | ok | CF blocks curl-default UA only; browser UA → 200 m3u8 | PLAYS (readyState 4, currentTime advancing in real browser) |
| Dracin ikun | bfikuncdn.com, kkzycdn.com:65 | open | 200 | PLAYS native |
| Drama ID reelshort | v-mps.crazymaplestudios.com | open | 200 | PLAYS native |
| Dracin dytt | vip.dytt-network.com / -broadcast.com | NO ACAO | 403 even with full Chrome headers, http1.1, referer variants | UNPLAYABLE via Vercel |
| Dracin ffzy | vip.ffzy-play9.com / vod.feifei-online.com | NO ACAO | 403 same | UNPLAYABLE via Vercel |
| Dracin uku | ukzyvod3.ukubf5.com | HAS ACAO + allow-credentials | 403 | plays on residential IPs; DC blocked |
| subo | — | API returns empty list upstream | — | catalog dead |
| SpringStream getPlayInfo (LokLok) | — | returns {"detail":"Success"} but no stream url | — | still broken upstream |

Key lesson: **403-from-datacenter ≠ broken**. Check CORS headers separately
(`curl -D - -o /dev/null <m3u8> -H 'Origin: …'`): a CDN with ACAO but DC-blocked (uku)
still works for residential users; a CDN with no ACAO (dytt/ffzy) is browser-dead everywhere.

## Fix shipped (commit 0362c4f, deploy success)

1. New `/api/hls` route inside the consolidated `api/external.js` (dispatch via `__path=hls`,
   rewrite added to vercel.json): playlist+segment relay with:
   - host allowlist regex covering all observed CDNs per source (dytt/ffzy/uku/ikun families);
   - per-source Referer helper;
   - share-page → embedded m3u8 extraction (stations ship `/share/<id>` HTML pages);
   - existing rewriteToProxy so nested variant playlists re-enter the route.
2. Dracin player dual-path: dytt/ffzy/uku try `/api/hls?url=…` first, then direct URL fallback;
   ikun/reelshort stay native (faster, no Vercel bandwidth). Verified chain:
   resolve 200 → playlist 200 rewritten → segment 200 video/mp2t first bytes 4740 (0x47 sync).

Honest limits: dytt/ffzy remain unplayable through Vercel regardless of relay — their CDNs ban
ALL datacenter IPs including Vercel's. Real fixes would be residential egress or replacement
stations with CORS-open media CDNs. Probed replacements: jisu (connection refused from VPS),
lz/bfzy/mozhua/wolong (dead or share-page-only).

## Subtitles audit — PASS

- `/api/subs` (Stremio OpenSubtitles addon): GoT S1E1 = 63 subs / 29 langs incl Indonesian.
- `/api/sub` SRT→VTT verified byte-level: WEBVTT header prepended, comma→dot ms separator.
- Frontend auto-pick verified live in browser: ind → may → eng, track applied, sel value set.
- Coverage gaps (e.g. Inception has no Indonesian on the addon) are source-side, not app bugs.

## UI audit — PASS

- Desktop 1280×720 vision-checked: hero/rows/nav clean, no overlap or cutoff.
- Mobile CSS present (@media ≤920px: top links hidden, bottomnav + safe-area padding).
  FALSE POSITIVE warning: testing "mobile" from a desktop-sized automation window proves nothing —
  check `matchMedia("(max-width: 920px)").matches` / computed styles before declaring layout broken.
- Repo-wide emoji scan zero; extracted inline `<script>` passes `node --check`.
- All views render (home/trending/anime/springstream/genres/about), search returns results,
  load-more buttons use direct-render onclick (scroll-jump fix intact).

## Tooling pitfalls hit this session

- Camofox CLI: run `camofox server start` (background) before browser tools; tabId is a POSITIONAL
  argument (`camofox eval '<expr>' <tabId>`), not `--tab`. Server idle-exits after ~2h with 0 tabs;
  health probe warns first. If browser_navigate says "Cannot connect", restart the server.
- Blockscout v2 API: token-transfers filter needs COMMA form `type=ERC-20,ERC-721` (pipe fails);
  JSON bodies can contain raw control chars → strip `[\x00-\x1f]` before json.loads.
- Etherscan v1 api endpoint is deprecated — use Blockscout v2 for keyless address probing.
- SPA without URL routing: driving pages requires clicking or calling in-page functions via eval
  (`navigate('player', {type,id})`); hash URLs do nothing.
