# Bookmark ledger skip (one account · one novel)

**Date:** 2026-07-21  
**User rule:** 1 account can bookmark a novel only once. Re-bookmark needs a different novel. Already-bookmarked accounts must be skipped automatically.

## Why
Old `execute_bookmark` always looped the full pool (or primary). On re-runs of the same `book_id`, accounts already in library still paid:
- sticky session open
- possible CF / mobile bootstrap
- wasted delay between accounts

User asked for the same class of fix as Powerstone ledger-first: **pick only accounts that still need the action**.

## Schema
```sql
CREATE TABLE IF NOT EXISTS book_bookmarks (
  email TEXT NOT NULL,
  book_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ok',  -- ok | already
  updated_at REAL NOT NULL,
  PRIMARY KEY (email, book_id)
);
CREATE INDEX IF NOT EXISTS idx_book_bookmarks_book
  ON book_bookmarks(book_id, status);
```

DB helpers (`/root/webnovel-tg-bot/db.py`):
- `mark_bookmarked(email, book_id, status="ok")`
- `is_bookmarked(email, book_id)`
- `bookmarked_emails(book_id, emails=None) -> set[str]`
- `accounts_not_bookmarked(book_id, emails) -> list[str]` (preserve order)

## Runtime flow (`execute_bookmark`)
```text
pool = primary[:1] | all accounts
already = bookmarked_emails(book_id, pool_emails)
targets = [acc for acc in pool if email not in already]
if not targets → report all already bookmarked, exit
for acc in targets:
  add_library(...)
  code 0 → mark ok
  already/exist/in library → mark already (skip forever for this book)
```

## Seed from history
After first deploy, seed from `action_log` rows with `action='bookmark'`:
- parse result lines like `✅ elizabeth.clark80`
- map local-part → full email via `accounts.txt`
- `mark_bookmarked(email, book_id, "ok")`

Example seed outcome (this session):
- book `36432589108294505` → **97** accounts marked

## API surface (unchanged)
```text
POST /go/pcm/library/addLibraryItemsAjax
  bookIds=<id>&novelType=0&_csrfToken=
```
Needs same sticky mobile PCM session as PS/avatar.

## UX report lines
```text
📋 Skip N akun yang sudah bookmark novel ini · sisa M
📚 Bookmark selesai: K/M
Skip sudah bookmark: N · dicoba: A
```

## Pitfalls
- Status only on **this book_id** — different novel must not inherit skip
- Do not delete accounts that fail CF; only mark when success/already proven
- Soft “already” messages vary by locale — match keywords: already, exist, in library, duplicate, has been added
- Primary mode + already bookmarked first account → 0 targets is correct (tell user to use ALL or another novel)
- After code ship: restart single `webnovel-tg` (unlike create-only `signup.py` child)

## Related
- Powerstone ledger-first: `references/powerstone-ledger-first-vote.md`
- Library endpoint notes: `references/powerstone-library.md`
- Ops umbrella: `webnovel-tg-ops`
