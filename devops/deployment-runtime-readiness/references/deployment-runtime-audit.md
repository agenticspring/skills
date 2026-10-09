# Deployment/runtime audit reference

Use this reference as an evidence worksheet. Keep the audit read-only and record observed results, not assumptions.

## Service inventory table

| Service | Exact launcher | Expected role | Actual role | Long-running? | Healthcheck | Dependencies | Result |
|---|---|---|---|---|---|---|---|
| control plane | `Dockerfile`, Compose, or systemd command | bot/API/control loop | doctor/test/placeholder/real loop | yes/no | command + exit status | DB/RPC/Telegram/etc. | PASS/BLOCKED |
| worker | exact `ExecStart`/`command` | scheduler/consumer/reconciler | same classification | yes/no | command + exit status | DB/queue/RPC | PASS/BLOCKED |
| executor | exact binary command | broadcaster/optional daemon | disabled reference/real daemon | yes/no | command + exit status | socket/signers/RPC | PASS/BLOCKED |

A healthcheck is an observation command, not evidence that the service command is correct. If a service and its healthcheck both run a one-shot doctor, record that separately from the missing long-running process.

## Evidence probes

Use the appropriate Hermes tools rather than guessing:

- `search_files` for `ExecStart`, `ENTRYPOINT`, `CMD`, Compose `command`, package `start`, `main`, `index`, `bot.start`, polling/webhook, worker loops, DB drivers, `Pool`, and migration runners.
- `read_file` for the complete launcher, entrypoint, config, doctor, and adapter files.
- `terminal` for exact runtime checks, using a sanitized environment where safe:
  - typecheck/test/build/secret-scan;
  - `node --check` on emitted JavaScript;
  - exact compiled entrypoint invocation;
  - `bash -n` for shell deployment scripts;
  - `systemd-analyze verify` for service units;
  - `docker compose config` and an image smoke test only when Docker is available and the user permits it.

Never print secret values. A structure-only environment check may report `set`/`empty` and file mode.

## Runtime classification

- **Factory:** constructs and returns a client/bot. No lifecycle proof.
- **One-shot doctor:** checks configuration and exits. Useful for readiness, not a service.
- **Disabled reference binary:** prints identity/mode or returns a disabled status. Not a worker/executor.
- **Lifecycle entrypoint:** starts polling, webhook serving, queue consumption, scheduling, or a durable worker loop and stays alive.
- **Adapter boundary:** accepts an abstract SQL/RPC interface. Not proof of a concrete network/database implementation.

## Common contradiction patterns

1. Compose/systemd launches `doctor.js` for every service; no bot/worker process can run.
2. A package `start` script points to `apps/foo/dist/main.js`, but the monorepo emits `dist/apps/foo/src/main.js`.
3. A bot factory has `startPolling()` exported, but no deployed entrypoint invokes it.
4. Migrations exist under source but no runner applies them, or the Docker runtime stage does not copy them.
5. The doctor only checks whether `DATABASE_URL` is non-empty; there is no driver, pool, connection query, or migration check.
6. An intentionally disabled optional executor is reported as a fatal doctor failure, making the primary service permanently unhealthy.
7. Tests exercise injected SQL/RPC fakes while production has no concrete adapter.

## Final verdict rules

- **Production-ready:** every declared long-running service has a reachable lifecycle entrypoint, exact artifact path works, required adapters/dependencies are wired, health semantics are coherent, and a real or controlled local boot was exercised.
- **Partially ready:** source/build quality is good but one or more runtime dependencies or host-level checks remain unverified; do not call this production-ready.
- **Not ready:** a declared service launches a one-shot/placeholder, a lifecycle entrypoint is absent, or a critical adapter/migration path is missing.

Always separate source-level blockers (wrong command, absent runtime, missing adapter) from host-only blockers (Docker unavailable, credentials absent, database not reachable).