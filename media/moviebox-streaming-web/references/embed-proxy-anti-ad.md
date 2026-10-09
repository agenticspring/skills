# Embed proxy anti-ad pattern (MovieBox, 2026-08-01)

Why: user reported clicks/seek inside the 2embed iframe redirected to Shopee /
Play Store. First attempt = iframe `sandbox` (block popups + top-navigation).
Local browser test showed 2embed rendering fine, but the USER's real Vercel env
then showed **"Sandbox not allowed — Remove sandbox from the iframe to play"**.
Sandbox on third-party players is NOT reliable across environments → replaced
with server-side HTML cleaning. No sandbox on any iframe now.

## Flow

```text
watch page -> iframe src = /api/embed-proxy?url=<embed>&ref=<embed>
route (nodejs runtime) -> embedProxy(url, ref) -> cleaned HTML (same-origin)
```

## lib/sources.js pieces

- `EMBED_PROVIDERS[]`: 2embed has `proxy: true`; vidsrc-to / vidsrc-me have
  `proxy: false` (direct embed).
- `resolveStream()`: when `provider.proxy`, `embedSrc = /api/embed-proxy?url=...&ref=...`;
  `sandbox` always `''`.
- `AD_PATTERNS` regex list: tagivi.com, blackninja.host, llvpn.com, adsterra,
  popads, popcash, propellerads, taboola, outbrain, ad.sk, doubleclick,
  googlesyndication, `ads.`, adservice, adpushup, revive-adserver.
- `embedProxy()` steps:
  1. `fetchText(url, referer || url)` (UA + referer, 15s timeout).
  2. Remove `<script src=...ad...>` tags (match src against AD_PATTERNS).
  3. Remove inline `<script>` blocks mentioning ad domains.
  4. Remove ad `<iframe>` tags.
  5. Inject shield `<script>` before `</body>`:
     - `window.open = function(){ return null; }` (block popup redirects)
     - capture-phase click handler: preventDefault anchors whose href matches
       `/shopee|play\.google|play\.apple|snapchat|tiktok|whatsapp|telegram|
       blibli|tokopedia|bukalapak|game\.com|apps\.|dl\.shopee/i`
     - wrapped in try/catch.
- Do NOT use `beforeunload` preventDefault — breaks player navigation.
- If the cleaned page has no `</body>`, append shield.

## app/api/embed-proxy/route.js

```js
import { embedProxy } from '../../../lib/sources';
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';
export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const url = searchParams.get('url');
  const ref = searchParams.get('ref') || '';
  if (!url) return new Response('missing url', { status: 400 });
  try {
    const { body, contentType } = await embedProxy(url, ref);
    return new Response(body, {
      headers: {
        'content-type': contentType || 'text/html; charset=utf-8',
        'x-robots-tag': 'noindex',
        'cache-control': 'no-store',
      },
    });
  } catch (e) {
    return new Response(`proxy error: ${e.message}`, { status: 502 });
  }
}
```

## Verification (run before push)

```bash
node --input-type=module -e "
import { embedProxy, resolveStream } from './lib/sources.js';
const r = await embedProxy('https://www.2embed.cc/embed/969681');
console.log('tagivi removed:', !/tagivi/i.test(r.body));
console.log('blackninja removed:', !/blackninja/i.test(r.body));
console.log('shield injected:', /window.open/.test(r.body));
console.log('has player refs:', /video|swish|streamsrcs|iframe/i.test(r.body));
const s = await resolveStream('969681','movie','1','1',{imdb:'tt22084616',tmdb:'969681',force:'embed',providerIdx:0});
console.log('stream embed:', s.embed.slice(0,80)); // expect /api/embed-proxy?..."
```

Expect: tagivi false, blackninja false, shield true, player refs true, embed URL
starts with `/api/embed-proxy`.

Note: `blackninja.host` may appear in plain text/comments (not an active script)
— a false-positive on the grep is fine; the important check is that the ad
NETWORK script (tagivi) is gone.

Also verify the route live: `curl "localhost:3001/api/embed-proxy?url=<encoded>" |
grep -c tagivi` → 0.

## Known limits

- Only strips HTML-level ad scripts. Ads injected later by the player's own JS
  (nested iframe to streamsrcs/vsembed) are not reachable from the proxy.
- If a provider changes ad networks, extend AD_PATTERNS.
- vidsrc-to/vidsrc-me not proxied → some ad risk remains when user switches to
  them.
