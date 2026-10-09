# Streaming App Code Review Security Notes

Session source: SpringMovie audit-fix review of Next.js App Router, stream player, subtitle handling, routing, and open-access removal.

Use this as a focused checklist when reviewing streaming-site diffs; it is not a narrative of one repo.

## Blocking security concerns to look for

### SSRF / open fetch via media URLs

Routes in streaming apps commonly accept `url=` and then server-fetch it for:

- stream proxying (`/api/stream-proxy?url=...`)
- subtitle proxying (`/api/sub?url=...`)
- embed proxying (`/api/embed-proxy?url=...`)
- optional HLS subtitle-track parsing (`parseSubtitleTracks(url, ref)`)

A change is risky when it starts fetching a URL supplied by the client or by an untrusted route parameter before validation. Even if the URL normally came from a provider, an attacker can call the route directly.

Review expectation:

- Prefer deriving episode/playlist URLs server-side from trusted station/provider metadata instead of accepting raw client URLs.
- Enforce provider/station allowlists for any endpoint that must accept external URLs.
- Reject loopback, private RFC1918, link-local, multicast, and cloud metadata hosts before fetching.
- Apply the same validation to "optional" probes/parsers; subtitle parsing can be an SSRF sink too.

### Third-party HTML on the app origin

An embed proxy that returns provider HTML from `/api/embed-proxy` and is rendered in an unsandboxed iframe makes provider scripts execute as the app origin. In many streaming apps sandboxing breaks playback, so the safe review bar is not simply "add sandbox".

Review expectation:

- Restrict proxyable hosts to known embed providers.
- Add a restrictive CSP where compatible.
- Prefer serving proxied provider HTML from an isolated subdomain/origin.
- Keep the decision explicit: unsandboxed iframe + same-origin third-party HTML is a security tradeoff, not a neutral implementation detail.

## Blocking / high-confidence logic errors

### Blind playlist/subtitle parsing of direct video URLs

`parseSubtitleTracks(playlistUrl)` should only read HLS playlists. If a direct provider returns `.mp4` or another binary video URL, blindly `await res.text()` can waste memory/time until abort and make `/api/stream` hit its direct-chain timeout, forcing unnecessary embed fallback.

Review expectation:

- Only parse when URL extension or response content-type indicates HLS (`.m3u8`, `mpegurl`, `application/vnd.apple.mpegurl`).
- Avoid full-body text reads for video content-types.
- Bound parser time separately from the main stream resolver budget.

### Subtitle UI does not apply in embed mode

Native `<track>` elements only affect the app-owned `<video>` element. They cannot attach to cross-origin/provider iframes.

Review expectation:

- Hide or disable OpenSubtitles/native subtitle controls while rendering an embed iframe.
- Or label them clearly as unavailable and instruct users to use the provider CC menu.

### Stale embedded subtitle state on episode changes

If embedded subtitle tracks are parsed asynchronously per episode, clear `embeddedSubs`, `subList`, and selected subtitle state when the episode or stream URL changes. Otherwise the UI can briefly auto-select a stale subtitle from the previous episode.

## Open-access removal review

After removing a password gate, grep source (not generated `.next` output) for:

- password constants and defaults
- auth cookie names
- login redirects
- middleware matchers that still gate pages
- UI copy/metadata that still says private or password-required

A no-op login route/page can be acceptable for backward compatibility, but call it out and prefer removal once clients are migrated.
