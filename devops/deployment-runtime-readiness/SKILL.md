---
name: deployment-runtime-readiness
description: "Audit whether deployed services can boot and stay healthy."
version: 0.1.0
author: Hermes Agent, based on session findings
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [deployment, runtime, readiness, entrypoints, compose, systemd, workers, databases]
    related_skills: [go-binary-daemon, requesting-code-review]
---

# Deployment/Runtime Readiness Skill

Use this skill to determine whether a real production process can boot, remain healthy, and perform its advertised role. It audits launch artifacts and runtime wiring; it does not treat a green unit suite, a typecheck, or a library factory as proof of deployability.

## When to Use

- User asks whether a repository is production-ready or can boot in deployment.
- Audit Docker/Compose, systemd, supervisor, package start scripts, workers, bots, database adapters, migrations, or doctor commands.
- Verify a release artifact before rollout without making edits or external changes.
- Reconcile README/runtime claims with actual entrypoints.

Don't use this for implementing fixes; report findings first and keep the audit read-only unless the user separately requests changes.

## Prerequisites

- Exact repository path and permission to inspect it.
- Read-only access to source, generated artifacts, deployment manifests, and scripts.
- Local runtime tools when available: language compiler/runtime, package manager, test runner, container CLI, and service-file validator.
- Never read or print secret values. Inspect secret structure only through redacted status checks.

## Core Model

A deployable service must satisfy all of these independently:

1. **Launcher correctness:** the service manager invokes the intended process, not a doctor, test, or placeholder.
2. **Artifact correctness:** the exact compiled file exists at the path the launcher uses and resolves its runtime dependencies.
3. **Lifecycle correctness:** the process actually starts polling/serving/consuming work, handles errors, and remains alive.
4. **Dependency correctness:** required databases, migrations, APIs, RPCs, credentials, sockets, and directories are wired.
5. **Health correctness:** readiness checks reflect service health and do not permanently fail because an intentionally disabled optional component is reported as fatal.
6. **Release correctness:** image/build/runtime contents contain everything needed, while secret material stays outside artifacts.

## Procedure

1. **Inventory launch surfaces.** Read package `start` scripts, Dockerfile `ENTRYPOINT`/`CMD`, Compose `command`, healthchecks, systemd `ExecStart`, deploy/rollback scripts, and documented commands. Build a service table with: service, command, expected role, long-running/one-shot, health probe, dependencies, and writable paths.
   - Completion criterion: every declared service has one identified launch command and role.

2. **Find concrete entrypoints.** Search for executable `main`/`index` files, `bot.start()`, polling/webhook registration, worker loops/schedulers, signal handlers, and HTTP/queue listeners. Factories that return a client are not lifecycle entrypoints. Confirm the normal launcher invokes the lifecycle function.
   - Completion criterion: each long-running service has a reachable lifecycle call, or is explicitly marked as a stub/blocker.

3. **Trace build output to launch paths.** Inspect compiler `outDir`, package workspace layout, emitted files, and package start scripts. Execute the exact compiled path used by each launcher. Check workspace imports/path aliases from the emitted artifact's runtime location. Never infer runtime success from typecheck alone.
   - Completion criterion: the exact artifact exists and starts far enough to produce a meaningful, sanitized result.

4. **Audit persistence boundaries.** Distinguish a real database adapter (driver dependency, pool/client creation, connection lifecycle, transactions, error handling) from SQL repository interfaces or test doubles. Locate migration files, migration tooling, migration ordering, and how migrations reach the deployed database. Check that the container image or provisioning flow includes the migrations.
   - Completion criterion: connection, transaction, and schema provisioning paths are all identified; missing pieces are blockers, not assumptions.

5. **Audit Telegram/external-client setup.** Verify token/config loading, allowlists and authorization, callback/webhook secrets, polling versus webhook mode, command registration, retry/error handling, and graceful shutdown. Confirm the deployed service starts the bot rather than only importing its factory.
   - Completion criterion: the configured mode and the actual start path agree, with no open authorization default.

6. **Audit worker/executor semantics.** Verify a worker main exists, schedules or consumes jobs, and has durable state/reconciliation paths. Treat a disabled reference executor as a disabled feature, not as a production worker. Ensure an optional disabled executor does not make the primary read-only service unhealthy unless that is intentional and documented.
   - Completion criterion: every worker service is either runnable with an identified loop or explicitly reported as not implemented/disabled.

7. **Run read-only gates.** Run typecheck, tests, build, secret scan, language vet/lint, shell syntax validation, and exact artifact smoke checks. Run doctor with a sanitized environment and record exit status/output. Run Compose config validation or systemd validation when tools are installed; do not install or contact external services unless asked.
   - Completion criterion: results are separated into code-quality PASS, runtime PASS, dependency status, and host-tooling blockers.

8. **Reconcile documentation.** Compare README claims, deployment manifests, generated artifacts, and source. Flag contradictions such as a documented worker with no runtime main, a package `start` path absent after build, or a Compose service that launches doctor.js.
   - Completion criterion: every material claim in the final report cites a file and line/range or a concrete command result.

## Reporting Format

Return a concise readiness verdict followed by:

- **Can boot:** yes/no/partial, with the exact process tested.
- **Critical blockers:** launch path, missing lifecycle, persistence, dependency, health, and artifact issues.
- **Required environment/dependencies:** names only; never values.
- **Verified gates:** exact commands and real outcomes.
- **Files inspected; files modified:** for a read-only audit, explicitly say none modified.
- **Host limitations:** missing Docker, unavailable database, or absent credentials are evidence about this environment, not universal product defects. Separate them from source-level blockers.

## Pitfalls

- A healthcheck or doctor command is not a production entrypoint.
- `createBot()` or `createClient()` proves construction only; it does not prove polling, webhook serving, or shutdown behavior.
- SQL repositories with injected `query()` interfaces are not a database adapter.
- Migration SQL without a runner or provisioning contract is not schema readiness.
- TypeScript `tsc` success does not prove compiled Node path aliases/workspace imports resolve at runtime.
- A package-level `start` script may point to `apps/foo/dist/...` while a monorepo build emits `dist/apps/foo/src/...`; run the exact command.
- A doctor that reports an intentionally disabled optional component as `FAIL` can keep Compose healthchecks and systemd services in a permanent failure loop.
- A disabled reference binary that prints identity/mode is not an executor daemon.
- Do not turn missing local binaries, credentials, or Docker into durable claims that the tool or architecture cannot work; report them as observed host blockers.
- Do not claim production readiness from tests alone when no real process was launched.

## Verification Checklist

- [ ] All Compose/systemd/package launch commands inventoried.
- [ ] Every long-running service has a concrete lifecycle entrypoint.
- [ ] Exact compiled artifacts exist at launcher paths.
- [ ] Runtime dependency resolution was checked from emitted output.
- [ ] Database adapter, connection probe, transaction wiring, and migration delivery were distinguished.
- [ ] Telegram polling/webhook and authorization setup were traced.
- [ ] Worker scheduling/consumption and executor enabled/disabled state were traced.
- [ ] Doctor/health exit semantics were checked.
- [ ] Tests/build/typecheck/secret scan results were run and reported honestly.
- [ ] Source-level blockers are separated from environment-only blockers.
- [ ] No files or external systems were changed during a read-only audit.

## Supporting Detail

See `references/deployment-runtime-audit.md` for the reusable evidence table, command probes, and examples of common readiness contradictions.
