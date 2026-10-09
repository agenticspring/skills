# OpenSubtitles keyless subtitle pipeline (verified 2026-08-01)

Fully keyless — no registration, no API key. Used by MovieBox `/api/subtitles`.

## Endpoints (verified working)

### Search (works, no key)
```text
GET https://rest.opensubtitles.org/search/query-{title-slug}[-s{SS}e{EE}]
User-Agent: TemporaryUserAgent
Accept: application/json
```
- Query slug format: lowercase, hyphens. Add `-s01e01` for episodes.
- Response: JSON array; each item carries:
  - `IDSubtitleFile` (download id)
  - `IDSubtitle`
  - `SubLanguageID` / `LanguageName`
  - `SubFileName`, `SubFormat` (srt), `SubHearingImpaired`
  - `SubDownloadsCnt`, `SubRating`
  - **`SubDownloadLink`** (direct `dl.opensubtitles.org` link — THIS is what works)
  - `ZipDownloadLink`
- Verified: "breaking bad" s01e01 → 100 results, 23 english. Dedupe by `IDSubtitleFile`.

### Download (trick: use SubDownloadLink, NOT /download/{id})
```text
GET {SubDownloadLink}      # e.g. https://dl.opensubtitles.org/en/download/src-api/vrf-.../filead/{id}.gz
User-Agent: TemporaryUserAgent
Accept-Encoding: gzip
```
- **`https://rest.opensubtitles.org/download/{id}` returns HTTP 400** ("method not
  specified in /rest.php") — do not use it. The direct `SubDownloadLink` from the
  search response works and returns a **gzip** body (BOM-prefixed UTF-8 srt).
- Decompress with `zlib.gunzipSync`, strip `\uFEFF`, then normalize srt → vtt:
  `00:00:06,000` → `00:00:06.000` (comma → dot) so `<track>` can render it.

## Integration pattern (Next.js App Router)

```text
/api/subtitles?type=os-search&title=...&season=&episode=  -> list of subs
/api/subtitles?type=os&link={SubDownloadLink}             -> converted vtt body
/api/subtitles?type=file&url=&ref=                        -> HLS EXT-X-MEDIA track proxy
```

Watch page UX (final, 2026-08-01):

1. **Auto-search on load** — as soon as `details.title` resolves, hit
   `type=os-search` automatically (no button press). Dedupe by language, keep the
   entry with the most downloads, cap ~20 languages.
2. **"💬 Subtitle" button** in the player bar toggles a dropdown of languages
   (grid of buttons: `langName (HI)` + `downloads`).
3. **Pick → auto-upgrade to direct**: when currently embed, re-request
   `/api/stream?force=` (empty force) first; if the provider now returns a direct
   m3u8, swap to the our `<video>` player with the subtitle as `<track>`. If no
   direct source, fall back to downloading the vtt (blob) + show hint.
4. **Embed mode**: our `<track>` cannot attach to a cross-origin iframe. Surface
   a transient overlay: "💬 Subtitle: klik tombol CC di pojok kanan bawah player".
   Provider CC (vidsrc-to has one) is the real path; also offer "Open Player ↗".
5. Keep `+ Upload .srt/.vtt` for local files (blob URL as `<track>` in direct mode).
6. **Sort Indonesian first** (`lang==='id' || /indonesia/i.test(langName)`), label
   `🇮🇩 Default` + violet highlight; auto-apply in direct mode once stream ready.
   User can switch language or turn off.
7. **Subtitle timing mismatch is expected** (OpenSubtitles subs are release-matched,
   provider video is another rip). Add offset controls (−0.5s/−1s/+1s/+0.5s/reset)
   with a custom overlay synced to `video.currentTime + subOffset`; native `<track>`
   can't be offset. Prefer subs whose filename says WEBDL/BluRay over CAM.

## Failure modes seen

| Symptom | Cause / fix |
|---|---|
| 400 on download | Used `/download/{id}` — must use `SubDownloadLink` from search |
| Cloudflare 401 on www page | Don't scrape HTML; use rest API only |
| No subs for a title | Try title + `-s{SS}e{EE}`; OpenSubtitles coverage varies by language |
