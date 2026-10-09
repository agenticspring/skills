# Webnovel TG avatar pool inventory

## Paths
- Pool dir: `/root/webnovel-tg-bot/avatars/`
- Used ledger: `/root/webnovel-tg-bot/avatars_used.txt`
- Selection code: `/root/webnovel-autoreg/signup.py` → `fetch_unique_avatar`
- Env wiring: `WEBNOVEL_AVATAR_DIR` / `WEBNOVEL_AVATAR_USED_FILE` (bot injects from `config.py`)

## Used-key formats
| Key | Meaning |
|---|---|
| `local:pool_foo.png` | local pool file consumed |
| `style:fun-emoji:seed` | Dicebear fun-emoji fallback |
| `style:bottts:seed` | Dicebear bottts |
| `style:pixel-art:seed` | Dicebear pixel-art |
| `style:animal:seed` | robohash animal set |

`used_*.png` files are **copies for accounts**, not the selectable pool. Selectable stock is only unused `pool_*`.

## Quick count recipe
```python
from pathlib import Path
avatars = Path('/root/webnovel-tg-bot/avatars')
used = {ln.strip() for ln in Path('/root/webnovel-tg-bot/avatars_used.txt').read_text().splitlines() if ln.strip()}
pool = [p for p in avatars.iterdir() if p.is_file() and p.name.startswith('pool_')]
available = [p for p in pool if f'local:{p.name}' not in used]
print('pool', len(pool), 'available', len(available))
```

## Preference
- New: 2D/animal/game/cyber/pixel — **not** real-face photos
- Keep existing `used_*` when restocking
