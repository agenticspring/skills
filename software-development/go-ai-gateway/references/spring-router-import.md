# Importing 9Router connections into your Go router

Migrating existing connections (accounts) from a running 9Router avoids re-auth.
Verified with 31 grok-cli connections → spring-router 2026-08-09.

## Source: 9Router SQLite

Tables live in `~/.9router/db/data.sqlite` (WAL mode — open read-only to avoid
locking a live 9router process: `sql.Open("sqlite", path+"?_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)")`).

```sql
SELECT data FROM providerConnections WHERE provider='grok-cli';
```

Each row's `data` is a JSON blob with fields:

```
displayName, email, accessToken, refreshToken, expiresAt (RFC3339), expiresIn,
scope, testStatus, priority, providerSpecificData: {authMethod, idToken, ...}
```

Mapping to your Connection struct:
- `AccessToken` = plaintext JWT (ES256 for grok-cli, kid `oauth2-production-2026-02-19`)
- `RefreshToken` = opaque string, part of form-encoded refresh body
- `ExpiresAt` — keep, refresh scheduler recomputes from `expires_in` on next refresh
- `IsActive=true`, `ConsecutiveErrors=0` on import (fresh start)

## Target store schema (modernc.org/sqlite)

```sql
CREATE TABLE IF NOT EXISTS connections (
  id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  data TEXT NOT NULL,          -- JSON blob: Name/Email/AuthType/Priority/IsActive/ExpiresAt/ExpiresIn + encrypted tokens
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

Encrypted at rest (AES-256-GCM). Atomic crypto helper pattern:

```go
func NewCrypto(masterKey string) *Crypto // sha256→32B key
func (c *Crypto) Encrypt(plain string) (string, error) // gcm.Seal, base64
func (c *Crypto) Decrypt(enc string) (string, error)
```

Master key: from env `SPRING_MASTER_KEY`, else generate 32 random bytes →
base64 → persist `master.key` chmod 600 in the store dir.

## Import flow (proven)

```
cmd/import-9router <9router-db-path> [provider-filter]
→ read providerConnections.data
→ provider.NewConnection() per row, id = 9router connection id (fallback imp-N)
→ store.SaveConnection() upsert (ON CONFLICT(id) DO UPDATE)
```

Balancer pools reload from store at startup; after admin OAuth adds a
connection, call `balancer.SetConnections(store.Connections(providerID))`.

## Migration checklist

1. Copy DB read-only — never write into ~/.9router while 9router runs.
2. Preserve original connection IDs (used as foreign keys by usage/pooling).
3. Resolve `expiresAt` zero (expired) connections via the refresh scheduler —
   do not hard-fail the pool, `Refresh(isActive)` on demand.
4. Verify with `GET /v1/models` + one real chat round-trip, not just import count.