# Custodial Bot Security Audit Checklist

Use for invite-only chat bots that hold encrypted wallet keys and persist operational state.

## Trust boundaries

- Bind authorization to both the authenticated user and the interaction surface. A user authorized for private chat must not inherit sensitive capabilities in groups.
- For callbacks, verify callback sender, message chat type, and message-chat ownership before dispatch.
- Re-check admin authorization in callback and pending-input handlers; never rely only on button visibility.
- Scope wallet reads and mutations by `user_id` plus wallet identifier.

## Secret lifecycle

- Validate imported keys before encryption and bind ciphertext to owner/address with AEAD AAD.
- Treat generation and reveal identically: send secret material separately from durable menu content and enroll it in a restart-safe deletion queue.
- Delete imported-key messages best-effort immediately; never log update bodies or key-bearing errors.
- Verify legacy decryption fallback cannot bypass current ownership queries.

## Persistence and runtime

- SQLite DB, WAL, and SHM all contain sensitive data. Enforce `0600` on every file and fail startup if permissions cannot be tightened.
- Set service-launcher `umask 077`; logs commonly contain user IDs and operational metadata even when keys are redacted.
- Make invite redemption atomic and test concurrent exhaustion.
- Review migrations for idempotence, partial-application behavior, and concurrent startup.
- Bound polling setup/API calls with context timeouts; polling itself must shut down from the parent context.

## Verification discipline

1. Add a focused regression test and observe RED before patching.
2. Test private/group/callback-owner mismatch cases at the routing boundary.
3. Test SQLite under a deliberately permissive umask and assert DB/WAL/SHM modes.
4. Run focused tests with the race detector.
5. If no canonical command is discoverable, create an OS-safe `mktemp /tmp/hermes-verify-...` script, run formatting/tests/shell syntax/diff checks, remove it, and report the result explicitly as **targeted ad-hoc verification**, not whole-suite green.
6. Preserve unrelated concurrent workspace changes; inspect scoped diffs and never overwrite sibling edits.

Never use live transactions or print secret fixtures during verification.
