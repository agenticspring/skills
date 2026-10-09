# Chinese forum mining for stream sources — nodeloc / nodeseek (2026-08-01)

Dez: "Apakah kau ga ada source lain yg bisa cari film dari forum ini
https://www.nodeloc.com/ https://www.nodeseek.com/ — kalo kena cloudflare
bypass pake api solver."

## nodeloc.com — Discourse, no Cloudflare, fully accessible

Verified live (curl, plain UA):

```bash
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0'
# search (works; /search.json?q= gives 400 — use query.json)
curl "https://www.nodeloc.com/search/query.json?term=%E7%94%B5%E5%BD%B1"
# topic detail
curl "https://www.nodeloc.com/t/31379.json"   # -> post_stream.posts[].cooked
```

Discourse `cooked` is HTML; extract URLs with regex `https?://[^\s"<>]+`.
Search is keyword-based but broad single terms work; multi-term searches
sometimes return 0 (use one strong term).

Relevant threads found:
- `t/31379` — 量子非凡暴风快看去广告代码: full PHP source stripping m3u8 ad
  segments (regex on `#EXTINF` blocks), caches per-provider dirs
  (ffzy→F/, lz-cdn+cdnlz→L/, bfeng→B/), JSON out `{code:200,type:m3u8,url:...}`.
- `t/47670` / `t/37897` — 量子非凡暴风 m3u8 去广告 json 解析接口源码
  (demo `cachem3u8.2s0.cn:8899/Demo/LZ_FF_BF/?url=...` — 404 as of 2026-08-01).
- `t/18507` — MacCMS10 `github.com/magicblack/maccms10` (open-source video CMS,
  ecosystem of 采集/API stations).
- `t/55732` — 扶风解析计费系统 (paid multi-parser billing system; demo
  `nav.ucdn.us`; API `viposs-vipcacheuserline-ffsirapi-llqsource.byteamone.cn/go.php?url=`
  returns `{code:200,url:...}` — but just echoes the URL, NOT a resolver).
- `t/37270` — 神马影院 SMHub `smhub.cc` (password-gated, unusable).
- `t/67522` — MyFlixer alternative (free streaming, frequent URL changes).

## nodeseek.com — Cloudflare managed challenge

curl → 403 "Just a moment…"; headless browser → bot_detection_warning with
`error 1005`-style Cloudflare page. Bypass with Capsolver AntiCloudflareTask:

```bash
# createTask
{"clientKey":"<KEY>","task":{"type":"AntiCloudflareTask",
 "websiteURL":"https://www.nodeseek.com/",
 "proxy":"IP:PORT:USER:PASS",           # sticky proxy REQUIRED
 "userAgent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}}
# poll getTaskResult -> solution.cookies.cf_clearance (426 chars)
```

**cf_clearance is IP-bound.** curl through the SAME proxy + Cookie header still
returned 403 on every path (/, /api, /api/boards, /search, /topic). Injecting the
cookie into a browser session also failed because the headless browser egresses
from a different IP. Lesson: AntiCloudflareTask tokens only work when the client
request originates from the exact proxy IP used at solve time. Don't iterate curl
header variations — either drive the whole session through that proxy with the
cookie, or accept the mirror domain instead. Balance burn note: CAP-BD487656…
(~$95) and CAP-742B0F… (~$12) were funded; CAP-FE3471CF… (~$0.07) nearly drained.

## nodeseek.cc — mirror domain, NO Cloudflare

- `https://nodeseek.cc/` returns 200 with Discourse-shaped HTML (title NodeSeek).
- `https://nodeseek.cc/posts.rss` — latest 50 items (recent only).
- `https://nodeseek.cc/search.json?q=<single term>` — works but SHALLOW index
  (old threads like post-99995 return 404 via /t/<id> and /t/topic/<id>).
- Use for freshness checks, not archive mining.

## Archive mining via web search (worked well)

`web_search("site:nodeseek.com 影视 采集 API")` surfaced thread URLs + snippets:
- `post-99995` — 大家分享一下自己影视站采集的api接口啊
- `post-108133` — 各位大佬，分享点影视采集站的api啊
- `post-87539` — 求影视站资源采集接口地址 (best taxonomy explanation:
  官采 = iQiyi/Youku/Tencent official API, often paid + needs resolver;
  切片 = self-sliced m3u8 CDN, free but has ads, domain gets blocked)
- `post-232558` — 免费在线视频解析 (YouTube/B站/VIP download tools)
- `post-215700` — 买了影视解析API接口怎么用

web_extract was unavailable (ddgs search-only backend) and r.jina.ai 403'd on
nodeseek; the search snippets themselves were the usable payload.

## Integration status / next steps (as of 2026-08-01)

Not yet integrated into MovieBox. The candidate that matches the existing stack
(vidlink-style direct m3u8) is the **切片 resolver pattern**: a small server-side
route that fetches an ffzy/量子/暴风/快看 m3u8, strips ad segments (thread 31379
logic), re-serves it through /api/stream-proxy. Requires a live resource URL
list — the forum links were either dead demos or paywalled sources, so obtaining
live slice station URLs is the remaining work.
