# SpringMovie / Nonthon-style streaming audit notes (2026-08-04)

Use this reference when auditing or extending a Next.js streaming site with MacCMS/Dracin resource stations, HLS stream/subtitle proxies, provider embed fallback (`2embed`, `vidsrc`, `vsembed`, etc.), and Nonthon-style subtitle dropdowns.

## Bugs found and fixed

- **Embed fallback rendered as video**: `/api/stream` can return `{ mode: 'embed', url: ... }`. The watch page must render an `<iframe>` for this mode. Passing an embed HTML URL to `<video>` silently breaks western movies.
- **Same-origin embed-proxy risk**: serving third-party provider HTML from `/api/embed-proxy` lets provider scripts execute as the app origin. Safer default is external provider iframe URL; keep proxy only as allowlisted/fenced fallback.
- **Open URL/SSRF risk**: routes taking `url=` (`stream-proxy`, `sub`, `embed-proxy`, HLS subtitle parsing) must reject private/internal DNS and validate redirects manually.
- **Dracin episode SSRF**: `/api/dracin?action=episode` must not trust client `url=`. Resolve stream URL server-side from allowlisted station key + `id` + `ep`; reject custom station URLs unless they exactly match known station entries.
- **Invalid VTT**: SRT timestamp conversion alone is not enough. `/api/sub` must return a document beginning with `WEBVTT`, otherwise native `<track>` may not parse it.
- **HLS subtitle playlists**: `#EXT-X-MEDIA:TYPE=SUBTITLES` can point to `.m3u8` subtitle playlists, not a single VTT/SRT file. Fetch segment URLs, cap segment count, validate every segment URL, and combine into one VTT response.
- **Movie subtitle search polluted by TV params**: Do not send `s/e` or `S01E01` suffixes to OpenSubtitles for movies. It can hide Indonesian matches. Send season/episode only for TV/series.
- **Iframe subtitles are provider-controlled**: in embed mode there is no local `<video>`, so app-native `<track>` cannot apply. Show `CC via player`; use the native dropdown only for direct-video/HLS pages.
- **Cosmetic tabs are not enough**: Nonthon-like top navigation must be functional. Test `Terbaru`, `Dracin`, `NXRStream`, `Trending`, and `Platform` with API + browser/headless checks.
- **Password-gate leftovers**: For open access, remove active password behavior and auth-cookie dependency. `/login` may remain only as a compatibility redirect/open-access page; `/api/login` may return `{ok:true, open:true}`.

## URL safety checklist

For every server-side fetch of user-influenced URLs:

- Accept only `http:`/`https:`.
- Reject URL credentials (`https://user:pass@host`).
- Resolve DNS before fetch.
- Reject localhost, loopback, link-local, RFC1918, carrier NAT, multicast/reserved IPv4, private/link-local IPv6.
- Use manual redirect handling and validate every redirect target before following it.
- For provider HTML proxying, require host allowlist and CSP; do not 302 to arbitrary user-supplied URLs.
- For HLS playlists, validate segment/key/subtitle URLs before proxying or fetching.

## Verification pattern

1. `npm run build` must pass.
2. API matrix should include:
   - `/api/home`
   - `/api/browse?type=movie&sort=latest&page=1`
   - `/api/explore?sort=trending&page=1`
   - `/api/explore?source=nxrstream&page=1`
   - `/api/explore?source=dracin&station=<station>&page=1`
   - `/api/dracin?action=sources|list|detail|episode`
   - `/api/stream?...` for a western movie that likely falls back to embed
   - `/api/subs?...` with Indonesian expected
   - `/api/sub?url=<real-download>` returns `text/vtt` and starts with `WEBVTT`
3. Security regression matrix:
   - `/api/stream-proxy?url=http://127.0.0.1:<port>/` rejects private IPv4.
   - `/api/sub?url=http://127.0.0.1:<port>/` rejects private IPv4.
   - `/api/embed-proxy?url=http://127.0.0.1:<port>/` rejects host/private target.
   - `/api/embed-proxy?url=https://example.com/` rejects disallowed public host.
   - `/api/embed-proxy?url=https://www.2embed.cc/embed/<id>` returns 200 and CSP headers.
   - `/api/dracin?action=episode&source=ffzy&id=<id>&ep=1&url=http://127.0.0.1:<port>/` returns the known station CDN URL, not the evil URL.
4. Browser/CDP checks:
   - Western watch page: iframe exists, provider text shows embed provider, UI shows `CC via player`.
   - Dracin page: video exists, `readyState=4`, episode grid renders.
   - Direct-video pages: subtitle dropdown exists and auto-picks Indonesian when available.
5. If browser snapshots show stale SPA state, use headless Chromium with `--dump-dom` or CDP instead of trusting the stale browser snapshot.
6. Clean up audit servers only via tracked session IDs/PIDs/ports known to belong to the audit run. Never use broad `pkill -f next-server`.
