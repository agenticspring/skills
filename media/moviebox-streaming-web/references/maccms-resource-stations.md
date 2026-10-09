# MacCMS resource stations (Chinese 采集 API) — captured 2026-08-01

Source: NodeLoc thread 83312 (MoonTVPlus recommendation, 169-source config) via
Discourse API `https://www.nodeloc.com/t/83312.json`. Station list ages fast
(domains rotate) — re-harvest from that thread when coverage drops. Non-adult
stations are wired into `lib/resources.js` (56 active since commit 116fe4e);
adult/🔞 entries live in a separate `ADULT_STATIONS` const (22 active since
commit 827a2cb). Full list below for reference/harvesting.

## API pattern (all MacCMS stations)

```
search:  GET {api}?ac=detail&wd=<urlencoded query>
detail:  GET {api}?ac=detail&ids=<vod_id>
play:    vod_play_url = "正片$https://host/path/index.m3u8"   (multiple sources '#'-joined)
search forbidden on some: {"code":1002,"msg":"Current API forbids keyword search."}
```

## Verified live 2026-08-01

| Station | API | Search | Result |
|---|---|---|---|
| 猫眼 | https://api.maoyanapi.top/api.php/provide/vod | OK | "蜘蛛侠2 Spider-Man 2" → m3u8 |
| 暴风 | https://bfzyapi.com/api.php/provide/vod | OK | "蜘蛛侠：英雄无归" → v.fengbao11.com m3u8 |
| 量子 | https://cj.lzcaiji.com/api.php/provide/vod | OK | Spider-Man hits |
| 爱奇艺 | https://iqiyizyapi.com/api.php/provide/vod | OK (returns empty for many) | |
| iKun | https://ikunzyapi.com/api.php/provide/vod | OK (empty) | |
| 豆瓣 | https://caiji.dbzy5.com/api.php/provide/vod | FORBIDDEN 1002 | |
| 茅台 | https://caiji.maotaizy.cc/api.php/provide/vod | FORBIDDEN 1002 | |
| 卧龙 | https://wolongzyw.com/api.php/provide/vod | HTML trap page | skip |

m3u8 verified end-to-end: master playlist → variant `index.m3u8` (AES-128,
`EXT-X-KEY URI="/20250927/92AyAknq/510kb/hls/key.key"`) → 4117 segments; key
proxy returns 16 bytes; segment proxy returns ts bytes. Ad-strip rewrite works.

## Full station list (name → api) — harvest source

```
iqiyizyapi.com     https://iqiyizyapi.com/api.php/provide/vod        (🎬爱奇艺)
dbzy.tv            https://caiji.dbzy5.com/api.php/provide/vod       (豆瓣资源)
mtzy.me            https://caiji.maotaizy.cc/api.php/provide/vod     (茅台资源)
wolongzyw.com      https://wolongzyw.com/api.php/provide/vod         (卧龙资源)
ikunzy.com         https://ikunzyapi.com/api.php/provide/vod         (iKun资源)
dyttzyapi.com      http://caiji.dyttzyapi.com/api.php/provide/vod    (电影天堂)
maoyanzy.com       https://api.maoyanapi.top/api.php/provide/vod     (猫眼资源)
cj.lzcaiji.com     https://cj.lzcaiji.com/api.php/provide/vod        (量子资源)
360zy.com          https://360zyzz.com/api.php/provide/vod           (360资源)
jszyapi.com        https://jszyapi.com/api.php/provide/vod           (极速资源)
moduzy.net         https://www.mdzyapi.com/api.php/provide/vod       (魔都资源)
ffzyapi.com        https://api.ffzyapi.com/api.php/provide/vod       (非凡资源)
bfzyapi.com        https://bfzyapi.com/api.php/provide/vod           (暴风资源)
zuidapi.com        https://api.zuidapi.com/api.php/provide/vod       (最大资源)
wujinapi.me        https://api.wujinapi.me/api.php/provide/vod       (无尽资源)
xinlangapi.com     https://api.xinlangapi.com/xinlangapi.php/provide/vod (新浪资源)
wwzy.tv            https://api.wwzy.tv/api.php/provide/vod           (旺旺资源)
subocaiji.com      https://subocaiji.com/api.php/provide/vod         (速播资源)
jinyingzy.com      https://jinyingzy.com/api.php/provide/vod         (金鹰点播)
p2100.net          https://p2100.net/api.php/provide/vod             (飘零资源)
ukuapi88.com       https://api.ukuapi88.com/api.php/provide/vod      (U酷影视)
guangsuapi.com     https://api.guangsuapi.com/api.php/provide/vod    (光速资源)
hongniuzy2.com     https://www.hongniuzy2.com/api.php/provide/vod    (红牛资源)
moduapi.cc         https://caiji.moduapi.cc/api.php/provide/vod      (魔都动漫)
rycjapi.com        https://cj.rycjapi.com/api.php/provide/vod        (如意资源)
hhzyapi.com        https://hhzyapi.com/api.php/provide/vod           (豪华资源)
apibdzy.com        https://api.apibdzy.com/api.php/provide/vod       (百度云zy)
lovedan.net        https://lovedan.net/api.php/provide/vod           (艾旦影视)
jinchancaiji.com   https://zy.jinchancaiji.com/api.php/provide/vod   (金蝉影视)
lziapi.com         https://cj.lziapi.com/api.php/provide/vod         (量子影视)
zuidazy.me         https://zuidazy.me/api.php/provide/vod            (最大点播)
wujinapi.com       https://api.wujinapi.com/api.php/provide/vod      (无尽影视)
wwzy.tv            https://wwzy.tv/api.php/provide/vod               (旺旺短剧)
yzzy-api.com       https://api.yzzy-api.com/inc/apijson.php          (优质资源)
huyaapi.com        https://www.huyaapi.com/api.php/provide/vod       (虎牙资源)
yayazy.net         https://cj.yayazy.net/api.php/provide/vod         (鸭鸭资源)
suoniapi.com       https://suoniapi.com/api.php/provide/vod          (索尼资源)
kuaichezy.org      https://caiji.kuaichezy.org/api.php/provide/vod   (快车资源)
sdzyapi.com        https://xsd.sdzyapi.com/api.php/provide/vod       (闪电资源)
apiyhzy.com        https://m3u8.apiyhzy.com/api.php/provide/vod      (樱花资源)
1080zyku.com       https://api.1080zyku.com/inc/api_mac10.php        (1080资源)
ukuapi.com         https://api.ukuapi.com/api.php/provide/vod        (U酷资源)
wujinapi.cc        https://api.wujinapi.cc/api.php/provide/vod       (无尽TV)
collect.wolongzyw.com https://collect.wolongzyw.com/api.php/provide/vod (卧龙点播)
collect.wolongzy.cc https://collect.wolongzy.cc/api.php/provide/vod  (卧龙资源TV)
tyyszy.com         https://tyyszy.com/api.php/provide/vod            (天涯资源)
xmm.hk             https://zy.xmm.hk/api.php/provide/vod             (小猫咪资源)
wujinapi.net       https://api.wujinapi.net/api.php/provide/vod      (无尽资源TV)
yparse.com         https://api.yparse.com/api/json                    (步步高资源)
niuniuzy.me        https://api.niuniuzy.me/api.php/provide/vod       (牛牛点播)
dbzy.tv (2)        https://caiji.dbzy.tv/api.php/provide/vod         (豆瓣资源TV)
jyzyapi.com        https://jyzyapi.com/api.php/provide/vod           (金鹰资源)
sdzyapi.com (2)    https://sdzyapi.com/api.php/provide/vod           (闪电资源TV)
cj.ffzyapi.com     https://cj.ffzyapi.com/api.php/provide/vod        (非凡资源TV)
mozhuazy.com       https://mozhuazy.com/api.php/provide/vod          (魔爪资源)
heimuer.xyz        https://json.heimuer.xyz/api.php/provide/vod      (黑木耳)
fczy888.me         https://api.fczy888.me/api.php/provide/vod        (蜂巢片库)
jmzy.com           https://api.jmzy.com/api.php/provide/vod          (金马资源网)
dadiapi.com        https://dadiapi.com/api.php/provide/vod           (大地资源网络)
huawei8.live       https://huawei8.live/api.php/provide/vod          (华为吧资源)
taopianapi.com     https://taopianapi.com/cjapi/sda/vod              (淘片资源)
hongniuzy3.com     https://www.hongniuzy3.com/api.php/provide/vod    (红牛资源)
qiqidys.com        https://www.qiqidys.com/api.php/provide/vod       (七七影视)
iqiyizyapi.com (2) https://www.iqiyizyapi.com/api.php/provide/vod    (iqiyi资源)
```

Adult/🔞 entries are wired in SEPARATELY since commit 827a2cb (2026-08-01) —
Dez asked to enable 18+/smut. They live in `ADULT_STATIONS` in lib/resources.js
(22 stations, never mixed into the main resolve chain) and are served only via
`/api/resource?adult=1` + `/play/adult` (confirm gate + hls.js). Verified live:
麻豆 (91md.me) browse returned 30 items, resolve returned t0.97img.com/a.m3u8.

Adult station list (name → api) as wired:
麻豆 https://91md.me/api.php/provide/vod | 番号 http://fhapi9.com/api.php/provide/vod
优优 https://www.yytv4.cc/api.php/provide/vod | 小鸡 https://api.xiaojizy.live/provide/vod
乐播 https://lbapi9.com/api.php/provide/vod | 奶香 https://Naixxzy.com/api.php/provide/vod
辣椒 https://apilj.com/api.php/provide/vod | 鲨鱼 https://shayuapi.com/api.php/provide/vod
豆豆 https://api.douapi.cc/api.php/provide/vod | 滴滴 https://api.ddapi.cc/api.php/provide/vod
黑料 https://www.heiliaozyapi.com/api.php/provide/vod | 百万 https://api.bwzyz.com/api.php/provide/vod
桃花 https://thzy1.me/api.php/provide/vod | 精品 https://www.jingpinx.com/api.php/provide/vod
CK https://ckzy.me/api.php/provide/vod | souav https://api.souavzyw.net/api.php/provide/vod
细胞 https://www.xxibaozyw.com/api.php/provide/vod | 香蕉 https://www.xiangjiaozyw.com/api.php/provide/vod
杏吧 https://xingba222.com/api.php/provide/vod | 色猫 https://caiji.semaozy.net/inc/apijson_vod.php/provide/vod
奥斯卡 https://aosikazy.com/api.php/provide/vod | 丝袜 https://siwazyw.tv/api.php/provide/vod

Fuller adult harvest (from the MoonTVPlus 121-entry config, not all wired):
91md, lbapiby, 155api, apiyutu, fhapi9, apilsbzy1, yytv4, xiaojizy, hsckzy,
apidanaizi, jkunzyapi, lbapi9, Naixxzy, slapibf, apilj, shayuapi, douapi,
ddapi, heiliaozyapi, bwzyz, thzy1, jingpinx, ckzy, souavzyw, xxibaozyw,
xiangjiaozyw, msnii, pgxdy, kxgav, xingba222, dadiapi/feifei, semaozy, aosikazy,
siwazyw, xrbsp, sexnguon, maozyapi, gdlsp, gayapi, xingba111, hsckzy888,
kuaichezy, yzzy-api. Domains rotate fast — treat adult coverage as best-effort.

## PHP ad-strip pattern (nodeloc topic 31379, 量子非凡暴风快看去广告)

Resolve resource m3u8 → split segment list → drop ad segments → re-serve cached
clean m3u8 (with cache dir per source: ffzy→F, lz-cdn/cdnlz→L, bfeng→B). In
MovieBox this is done by `rewriteM3u8` in lib/sources.js: regex-drops ad segments
(`AD_SEGMENT_RE`) and injects `#EXT-X-DISCONTINUITY`; caches not implemented
(per-request fetch; fine for personal use).
