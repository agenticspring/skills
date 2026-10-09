# HAR playback diagnosis — MovieBox (2026-08-04)

Session: Dez pasted `moviebox.txt.har.json` (745 entries) from `moviebox-xi-seven`.
This file captures the exact analysis pattern + findings.

## Quick recipe (Python)

```python
import json
from collections import Counter
d = json.load(open('moviebox.txt.har.json'))
entries = d['log']['entries']

# 1. status summary
print(Counter(e['response']['status'] for e in entries))
# 2. key requests
for e in entries:
    u = e['request']['url']
    if any(k in u for k in ['/api/stream','/api/details','/api/embed-proxy',
                            '2embed','vidsrc','vsembed','streamsrcs','.m3u8','.mp4']):
        print(e['response']['status'], u[:130])
# 3. ad cloaking timeline (proves provider injection, not app)
for e in entries:
    u = e['request']['url']
    if any(k in u for k in ['.cfd','.rest','cloudnestra','cloudorchestranova']):
        print(e['response']['status'], e.get('startedDateTime','')[11:23], u[:90])
```

## Findings from the real HAR (reference pattern)

| Signal | Meaning |
|---|---|
| `/api/details`, `/api/stream`, `/api/embed-proxy` all 200 | App side healthy |
| 2embed embed-proxy 200, but ZERO `streamsrcs.2embed.cc` requests | 2embed player JS didn't init its stream loader (provider/anti-bot) |
| vidsrc.to → `vsembed.ru` all 16 assets 200 (style.css, jquery-3.7.1.min.js, base64.js, sources.js, reporting.js, sbx.js, rings.svg) | vidsrc player shell DID load |
| **0 requests for .m3u8/.mp4/.ts/.m4s anywhere** | Video never started — user didn't click play or overlay/adblock intercepted |
| `cloudnestra.com/asdf.js` + `cloudorchestranova.com/rcp/<base64>` + `czy.*.cfd` + `u6efe.*.rest` appear ~10ms after vsembed assets | PROVIDER-injected cloaked ads (raw player = no shield) |
| `disable-devtool@0.3.9/misdir.js` from unpkg | vsembed anti-devtool script (harmless, explains console noise) |
| `chrome-extension://lknbpjklcepicgjmdnijccpipkhcinaf/*` ×33 | User's adblock extension — may block player domains (status 0) |
| `/api/subtitles` 502 | OpenSubtitles rate-limit — unrelated to playback |

## Root cause found

vidsrc.to blocks Vercel datacenter IPs → embed-proxy 302-fallback → iframe loads
RAW vidsrc.to → CF challenge → vsembed.ru player → NO shield → cloaked ads +
user's adblock blocks the cloudorchestranova player iframe → dead player.

## Fix shipped (commit 2ba412b)

1. vidsrc-to EMBED_PROVIDERS build now targets `https://vsembed.ru/embed/movie/{id}/`
   and `https://vsembed.ru/embed/tv/{id}/{s}-{e}` (dash, not slash) — vsembed IS
   fetchable from Vercel so the shield applies.
2. `cloudnestra` + `\.cfd\b` + `\.rest\b` added to AD_PATTERNS + shield BAD.
3. `cloudorchestranova` deliberately NOT blocked (player iframe host).
4. Verified embed-proxy(vsembed) = 200, 62KB, cloudnestra script 0, player_iframe 1.
