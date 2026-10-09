# Book detail CF / paste-link failures

## Symptom
Paste novel URL in TG bot:
```
❌ Gagal ambil detail: CF blocked (Just a moment / 403)
```

## Root cause
`show_book` used to call `get_book_detail(accs[0])` (+ maybe 3 more sequential).
If leading accounts are **cold** (no session) or CF-hit after mass relogin, whole UX fails even when other warm accounts would succeed.

## Fix pattern
```python
svc.get_book_detail_any(book_id, accs, max_tries=15)
```
Order:
1. in-memory usable sessions
2. disk `sessions/<email>.json` present
3. cold accounts last

On CF / no csrf / login fail:
- invalidate that email session
- try next account

## Verification
Warm path should return title in <1s when cookies exist.
After relogin storms, still OK if any of ~90 warm sessions work.

## Related
- Soft TTL 24h + live validate
- `/sync` residual `-51037` / no csrf does not mean pool is dead
