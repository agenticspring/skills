# Nonthon API Map (nonthon.vercel.app)

**Verified:** 2026-08-04  
**Password:** AA130126 (stored in memory, do not write to vault)  
**Stack:** Inline HTML + JS SPA, Vercel serverless functions, hls.js player

---

## Auth

```
POST /api/login
Body: {"password": "..."}
Response: {"ok": true}
Sets cookie: __Host-nonthon_sess (httpOnly, Secure, SameSite=Strict)
```

Subsequent calls require this cookie. Rate-limited on failures.

---

## TMDB (western content — direct browser fetch)

Key exposed in client JS: `8265bd1679663a7ea12ac168da84d2e8`

```
GET https://api.themoviedb.org/3/trending/all/week?api_key=...&language=id-ID&page=1
GET https://api.themoviedb.org/3/movie/popular?api_key=...&language=id-ID&page=1
GET https://api.themoviedb.org/3/tv/popular?api_key=...&language=id-ID&page=1
GET https://api.themoviedb.org/3/discover/movie?api_key=...&language=id-ID&sort_by=primary_release_date.desc&primary_release_date.lte=2026-08-04&vote_count.gte=1
GET https://api.themoviedb.org/3/discover/tv?api_key=...&language=id-ID&sort_by=first_air_date.desc&first_air_date.lte=2026-08-04&vote_count.gte=1
```

Image CDN: `https://image.tmdb.org/t/p/{w500|original|w300|w92}/{poster_path}`

---

## MacCMS Proxy (/api/dracin)

Chinese short drama content. Proxies multiple MacCMS resource sites.

### Sources endpoint
```
GET /api/dracin?action=sources
→ {"success":true,"sources":[
    {"key":"dytt","label":"Utama","short":"UT","note":"...","shape":"episodes"},
    {"key":"ffzy","label":"Katalog Besar","short":"KB","note":"...","shape":"episodes"},
    {"key":"ikun","label":"Vertikal HD","short":"HD","note":"...","shape":"episodes"},
    {"key":"uku","label":"Update Harian","short":"UH","note":"...","shape":"full"},
    {"key":"subo","label":"Arsip Besar","short":"AB","note":"...","shape":"full"}
  ]}
```

### List
```
GET /api/dracin?action=list&source=dytt&page=1
→ {"success":true,"source":"dytt","shape":"episodes","page":1,"pages":1112,"total":22226,"items":[...]}
```

Item shape:
```json
{
  "src": "dytt",
  "id": 83350,
  "title": "Localized title",
  "titleOrig": "原文标题",
  "pic": "https://vod.dyttimage.com/...",
  "remarks": "Tamat",
  "year": "2026",
  "area": "Tiongkok",
  "genre": "Drama Pendek",
  "overview": "...",
  "updated": "2026-07-17 09:21:04",
  "episodes": 53
}
```

### Search
```
GET /api/dracin?action=search&source=dytt&q=keyword
```

### Detail
```
GET /api/dracin?action=detail&source=dytt&id=83350
```

### Episode (lazy m3u8 resolve for DRACIN_ID_SOURCES)
```
GET /api/dracin?action=episode&source=reelshort&id=...&ep=1
→ {"success":true,"url":"https://...m3u8","locked":false}
```

---

## Indonesian-Localized Source Proxy (/api/dracin-id)

Same interface as `/api/dracin` but for `DRACIN_ID_SOURCES` set (currently: `reelshort`).

```
GET /api/dracin-id?action=sources
GET /api/dracin-id?action=list&source=reelshort&page=1
GET /api/dracin-id?action=episode&source=reelshort&id=...&ep=1
```

---

## Image Proxy (/api/dracin-img)

Proxies upstream image CDN to avoid CORS/hotlink issues.

```
GET /api/dracin-img?u=https%3A%2F%2Fvod.dyttimage.com%2F...
```

---

## NetPop Proxy (/api/nxrstream)

iQIYI-based content with multi-language subtitles. Signed upstream — not directly reproducible.

```
GET /api/nxrstream?action=list&type=all&page=1    → 502 "sign error!" (upstream token required)
GET /api/nxrstream?action=search&q=keyword        → works, returns NetPop results
GET /api/nxrstream?action=detail&id=101841&category=0
GET /api/nxrstream?action=media&id=...&episodeId=...&definition=GROOT_FD  → m3u8 URL
```

Detail item shape:
```json
{
  "id": "101841",
  "name": "Man Wanted",
  "enName": "Man Wanted",
  "category": 0,
  "coverVerticalUrl": "https://img.despseek.com/...",
  "coverHorizontalUrl": "https://img.despseek.com/...",
  "score": 6.2,
  "year": 1995,
  "areaList": ["Hongkong"],
  "tagList": ["Action","Crime","Drama"],
  "introduction": "...",
  "episodeCount": 1,
  "episodes": [
    {
      "id": 1024343,
      "label": "Episode 1",
      "seriesNo": 1,
      "totalTime": 5517,
      "definitionList": [
        {"code":"GROOT_LD","description":"540P"},
        {"code":"GROOT_FD","description":"360P"}
      ],
      "subtitlingList": []
    }
  ]
}
```

Definition codes: `GROOT_LD` (540P), `GROOT_FD` (360P), higher tiers likely `GROOT_HD`/`GROOT_BD`

---

## Upstream CDN Mapping

| Nonthon source key | Real backend | Image CDN | Catalog size |
|--------------------|--------------|-----------|--------------|
| dytt | 电影天堂 (dyttimage.com) | vod.dyttimage.com | 22,226 |
| ffzy | 非凡资源 (ffzy5.tv) | tupian.ffeiimg.com | 19,858 |
| ikun | ikun.im | ynztctv.com | 1,507 |
| uku | ukuapi88.com | img.ukuapi88.com | 9,344 |
| subo | unknown | unknown | 35,000+ |
| NXRStream | NetPop (iQIYI-based) | img.netpop.app / img.despseek.com | — |
