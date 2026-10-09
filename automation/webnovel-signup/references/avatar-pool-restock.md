# Avatar pool restock — free internet sources

When `pool_*` avatars exhausted, restock from free CDN/API sources.
**Never use AI image generation** — wasteful tokens, user preference.

## Quick restock (Python)

```python
import io, time, random
from pathlib import Path
from urllib.parse import quote
from curl_cffi import requests
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageOps

AV = Path('/root/webnovel-tg-bot/avatars')
session = requests.Session(impersonate='chrome124')

# ── Configuration ──

THEMES = ['anime', 'mainan', 'gunung', 'game', 'pemandangan']
STYLES = ['2d', 'cartoon', '3d', 'realistis']

# Unsplash photo IDs per landscape theme
UNSPLASH = {
    'gunung': ['1506905925346-21bda4d32df4', '1464822759023-fed622ff2c3b',
               '1486870591958-9b9d0d1dda99', '1519681393784-d120267933ba',
               '1454496522488-7a8e488e8606'],
    'pemandangan': ['1507525428034-b723cf961d3e', '1476514525535-07fb3b4ae5f1',
                    '1441974231531-c6227db76b6e', '1501785888041-af3ef285b470',
                    '1470071459604-3b5ec3a7fe05'],
}

# Dicebear style maps
DICE = {
    'anime': {'2d': 'adventurer', 'cartoon': 'fun-emoji', '3d': 'bottts', 'realistis': 'avataaars'},
    'game':  {'2d': 'pixel-art', 'cartoon': 'fun-emoji', '3d': 'bottts', 'realistis': 'notionists'},
    # mainan uses Robohash set3 for all styles
}

def source_urls(theme, style, i, seed):
    urls = []
    if theme in ('gunung', 'pemandangan'):
        ids = UNSPLASH[theme]
        pid = ids[(i + {'2d':0,'cartoon':1,'3d':2,'realistis':3}[style]*5) % len(ids)]
        urls += [f'https://images.unsplash.com/photo-{pid}?w=512&h=512&fit=crop&q=80']
    elif theme == 'mainan':
        urls += [f'https://robohash.org/{quote(seed)}.png?set=set3&size=512x512&bgset=bg1']
    elif theme == 'anime':
        style_name = DICE['anime'].get(style, 'adventurer')
        urls += [f'https://api.dicebear.com/9.x/{style_name}/png?seed={quote(seed)}&size=512']
    elif theme == 'game':
        style_name = DICE['game'].get(style, 'pixel-art')
        urls += [f'https://api.dicebear.com/9.x/{style_name}/png?seed={quote(seed)}&size=512']
    urls.append(f'https://picsum.photos/seed/{quote(seed)}/512/512')
    return urls

def style_filter(im, style):
    if style == '2d':
        im = ImageEnhance.Color(im).enhance(1.35)
        im = ImageEnhance.Contrast(im).enhance(1.15)
        im = im.filter(ImageFilter.SMOOTH_MORE)
    elif style == 'cartoon':
        im = ImageEnhance.Color(im).enhance(1.6)
        im = ImageEnhance.Contrast(im).enhance(1.35)
        im = im.filter(ImageFilter.EDGE_ENHANCE)
    elif style == '3d':
        im = ImageEnhance.Contrast(im).enhance(1.1)
        im = ImageEnhance.Brightness(im).enhance(1.05)
        im = ImageOps.expand(im, border=8, fill=(30, 30, 40))
        im = im.resize((512, 512), Image.Resampling.LANCZOS)
    else:  # realistis
        im = ImageEnhance.Contrast(im).enhance(1.08)
        im = ImageEnhance.Sharpness(im).enhance(1.2)
    return im

def write_avatar(im, path, theme, style, i):
    draw = ImageDraw.Draw(im)
    draw.rectangle([0, 484, 512, 512], fill=(15, 15, 20))
    draw.text((10, 490), f'{theme}/{style}/{i:02d}', fill=(235, 235, 240))
    im.save(path, format='PNG', optimize=True)

# ── Generate all 100 ──

for theme in THEMES:
    for style in STYLES:
        for i in range(5):
            name = f'pool_{theme}_{style}_{i:02d}.png'
            seed = f'{theme}-{style}-{i}-restock'
            path = AV / name
            success = False
            for url in source_urls(theme, style, i, seed):
                try:
                    r = session.get(url, timeout=40, allow_redirects=True)
                    if r.status_code == 200 and len(r.content) > 800:
                        im = Image.open(io.BytesIO(r.content)).convert('RGB').resize((512, 512))
                        im = style_filter(im, style)
                        write_avatar(im, path, theme, style, i)
                        success = True
                        break
                except Exception:
                    continue
            if not success:
                print(f'FAILED: {name}')
            time.sleep(0.15)

print(f'Done: {len(list(AV.glob("pool_*")))} avatars')
```

## Naming convention

```
pool_{theme}_{style}_{00-04}.png
pool_anime_2d_03.png
pool_mainan_3d_01.png
pool_gunung_realistis_04.png
pool_game_cartoon_00.png
pool_pemandangan_2d_02.png
```

## Used tracking

`avatars_used.txt` records `local:{filename}` per used avatar.
`fetch_unique_avatar` in signup code checks this set before picking from pool.
Reset for a fresh pool: clear `avatars_used.txt`.

## Pitfalls

- Pollinations/Stable Diffusion/HuggingFace AI gen = **wasteful**, user prefers free CDN
- Some Dicebear styles may produce minimal/abstract images — rotate through alternative styles if quality is low
- Unsplash photos for `gunung`/`pemandangan` themes may not fill all 5 variants — reuse IDs with different crop/seed parameters
- PIL `ImageFilter` tweaks are optional — the raw CDN image is acceptable
- Style strip label at bottom helps inventory but is not required by the code — `fetch_unique_avatar` selects any `pool_*` file regardless of content
