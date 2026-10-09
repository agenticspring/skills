---
name: private-source-repository-release
description: Safely initialize and publish an existing local application as a new private Git repository while excluding secrets, runtime state, databases, logs, and binaries.
version: 1.0.0
author: spring
license: Private
platforms: [linux, macos]
metadata:
  hermes:
    tags: [git, github, private-repository, secret-scanning, release]
---

# Private Source Repository Release

Use this skill when turning an existing local project or deployment directory into a new private GitHub repository without modifying a legacy production checkout.

## Isolation rule

Treat the requested source directory and any legacy/production directory as separate systems. Never initialize Git, copy files into, stop, restart, or otherwise modify the legacy directory unless the user explicitly asks. Record the protected path/process before starting.

## Workflow

1. **Inspect authentication before asking for credentials.** Check the standard secret store (for this environment, `~/.hermes/.env`) and current CLI auth. Never print token values.
2. **Audit repository boundaries.** Check whether the source is already a Git repository and whether the intended remote already exists. Do not inherit unrelated Git metadata.
3. **Harden `.gitignore` before staging.** At minimum exclude:
   - `.env`, `*.env`, credential files;
   - runtime `data/`, SQLite DB/WAL/SHM;
   - logs, coverage, temporary output;
   - compiled binaries and local build directories;
   - local agent/editor artifacts such as `.hermes/`, `.idea/`, `.vscode/` unless intentionally versioned.
4. **Initialize and stage locally.** Review `git diff --cached --name-only`; do not rely on `.gitignore` alone.
5. **Run two secret checks:**
   - pattern scan for likely hardcoded credentials;
   - exact-value scan using non-empty secret values loaded from local `.env` files, comparing them against staged text blobs without printing the values.
   **Script files are the common leak, not just `.env`.** Python/bash automation often hardcodes proxy creds (`host:port:user:pass`), IMAP user/app-passwords, API keys, and operational identifiers (farm/catch-all domains, account emails) directly in source. A regex pattern scan misses most of these (they look like ordinary strings). Before staging, run `sed -i` across `*.py`/`*.sh` replacing every known `.env` value with a placeholder (`sed -i 's/REAL_VALUE/PLACEHOLDER/g' *.py`), then re-run the exact-value scan until clean. Also scrub operational identifiers (domains, email addresses) even when they are not credentials — they are still sensitive surface for a private account farm. Iterate: pattern scan → scrub → exact scan → repeat; the exact scan against `.env` values is the source of truth.
6. **Run the project's quality gate** before the initial commit (tests, vet/lint, build).
7. **Commit and create the remote private repository.** Use the authenticated account, explicit private visibility, a stable default branch, and push with upstream tracking.
8. **Verify the remote, not just the push command:**
   - repository visibility is `PRIVATE`;
   - remote branch SHA equals local HEAD;
   - recursively inspect remote blob paths for prohibited files;
   - local working tree is clean.
9. **Record durable project state** in the project's notes, including repo URL, private visibility, exclusion audit, and confirmation that legacy production remained untouched.

## Remote-tree audit pitfall

Audit only blob/file paths when searching for prohibited binaries. A naive regex for `bot` can falsely match a legitimate source directory such as `cmd/bot`. Anchor binary checks to exact file paths (for example root `/bot`), while allowing source directories.

## GitHub API cache staleness (verify via raw.githubusercontent, not the trees API)

Right after a push, `GET /git/trees/{ref}?recursive=1` and blob-content fetches can serve a **stale tree** (the API lags the push by seconds/minutes). Symptom seen 2026-08-08: `git push` succeeded and `commits/main` SHA matched local HEAD, but the trees/blob scan still showed an old file content; `raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}` returned the corrected bytes. Verification order:
1. `commits/{branch}` SHA == local HEAD (fast, reliable).
2. For content scans, fetch **raw.githubusercontent.com** blobs (authenticated with the token works too) — treat that as source of truth, not `git/trees` blob contents.
3. Re-run the scan after a few seconds if the trees API disagrees with raw before concluding a secret leaked.

## Secret-scan value list must include domains and path strings

Beyond API keys/tokens, also scan for: farm domains (e.g. `<REDACTED>`, `<REDACTED>`), IMAP user/host strings (`<REDACTED>`, `imap.gmail.com`), and **embedded path names** — a test file named `noproxy_<DOMAIN_REDACTED>.json` or a literal local path `/root/grok-register/data/noproxy_<DOMAIN_REDACTED>.json` in a script carries the domain `<DOMAIN_REDACTED>` and would trip an exact-value scan on the domain alone. Scrub those path strings too (rename to a neutral slug like `noproxy_result.json`) and add the domain list to the pattern set.

## Making an existing repo PUBLIC safely

When the user asks to flip a repo from private → public, run the full audit BEFORE changing visibility, and treat history as part of the surface:

1. **Scan all files that will ship** (walk the tree, skipping `.git`, `accounts/`, `__pycache__`; ignore `.env`/`.pyc`). Pattern-scan for: 87-88 char base58 (Solana private keys), `eyJ` JWTs, `0x`+64-hex EVM keys, 32-hex API keys. Exact-value scan against `.env` values AND runtime state files (e.g. `accounts/*.json` containing access tokens/private keys).
2. **Scan git history, not just the working tree**: `git rev-list --all` then `git ls-tree -r <sha>` per commit — confirm no sensitive file was ever committed (a deleted secret still lives in history forever). If the local repo has a single squashed commit, history audit is cheap; a force-push replaces remote history but verify the remote branch SHA equals local HEAD after.
3. **Verify `.env`/state dirs are gitignored** and never staged (`git diff --cached --name-only` must not list them).
   **Audit runtime-generated secret files too**: encryption master keys, JWT secrets, tunnel credentials, and app-specific runtime keys often live next to data (e.g. `master.key`, `jwt-secret`, `machine-id`) and are NOT in `.gitignore` by default — they are not in tracked history yet, but a careless `git add -A` before a public push ships them. Add them to `.gitignore` explicitly during the audit (and commit the .gitignore change BEFORE flipping visibility).
4. **Flip visibility via API** (`PATCH /repos/{owner}/{repo}` `{"private":false}`), then **verify anonymously** — fetch the repo API without any auth token and confirm `private:false` + expected file tree. A push after publicizing means the new commit is immediately world-readable; re-run the tree listing after push.
5. Report: remote tree (file paths only), visibility, anonymous-access check, and which sensitive paths are confirmed absent (`.env`, accounts, tokens, keys).

## Handing a sanitized copy to a third party ("temenku minta scriptnya")

A different brief from "publish my app". The artifact is a **portable copy of scripts that already
work on the user's machine**, and the recipient must be able to run them without receiving any of
the user's private infrastructure. Credential scrubbing alone is not enough — three extra classes
must go, none of which live in `.env`:

1. **The user's private upstream endpoint.** When the scripts depend on a private / leaked /
   signed API base URL or RPC path, that URL **is the user's edge**. Publishing it burns the
   endpoint (rate-limit, ban) and hands over their access. It is usually a hardcoded default in a
   helper module, not an env var. Replace it with an **empty env placeholder** and say so in the
   README, then confirm the script still runs with it empty — make the dependent feature
   *optional* and degrade with a printed skip, never a crash.
2. **Identifiers tied to assets the user keeps using.** An on-chain address or account id is
   public, but it still labels the user's live operation. If the user says the wallet/account will
   keep being used, keep `address.txt` (and similar) **out of the repo and in `.gitignore`** even
   though it holds no secret.
3. **Anything that makes the recipient depend on the user's accounts.** Default every config to a
   public / no-auth endpoint and require env or CLI override for anything personal.

Design rule: **every personal value is a parameter.** Private key (env var + optional file path),
RPC URL (env with a public default), destination (CLI arg defaulting to the sender). Ship
`.env.example` with the values blank, and a README section listing what is deliberately absent and
why. A script handed to someone else must also front-load the risk in the README — caveats buried
in code comments are not read.

Then run the two-layer scan below **and** a functional check (`--dry-run`, `--help`, or a
read-only invocation) to prove sanitisation did not break execution.

Worked case, file layout and exclusion table: `references/sanitized-share-artifact.md`.

## Two-layer secret verification (local staged tree AND the bytes GitHub serves)

Layer 1 is the pre-commit scan. Layer 2 scans **what the remote actually serves** — the only check
that catches a `.gitignore` mistake, a partially-staged tree, or a file staged before the ignore
rule existed:

1. Enumerate remote blobs: `GET /repos/{o}/{r}/git/trees/{ref}?recursive=1`.
2. Fetch each with `GET /repos/{o}/{r}/contents/{path}?ref={ref}`, base64-decode `content`, and
   concatenate into one text blob. (The contents API is also the reliable read when the trees API
   serves a stale tree right after a push.)
3. Run the **same** exact-value secret list against that concatenated remote text.

Report it as *"scanned N files served by GitHub"* — that is the claim you can defend. Include value
classes a regex will never find: the real private key, the live API key, the private endpoint host
**and its path token**, the user's wallet address, every PAT in the store, and webhook URLs. Also
run the cheap generic patterns (`\b[0-9a-fA-F]{64}\b`, `0x[0-9a-fA-F]{64}`, `ghp_…`,
`g.alchemy.com/v2/…`) — but treat the exact-value list as the source of truth, and expect
false-positive 64-hex hits from SHA-256 digests recorded in notes.

## On-request second pass: "pastikan lagi ga ada data sensitif"

A user who asks to re-verify means the first answer did not convince them. Re-running the same scan
is the wrong response — widen it to surfaces the first pass never touched, and make the *evidence*
visible per surface rather than restating a verdict.

1. **Scan every reachable Git object, not just the working tree.**
   `git rev-list --objects --all` → `git cat-file -t/-p` each SHA; compare the blob set against the
   working tree and assert **"no ghost blobs — history == working tree"**. Add
   `git fsck --unreachable --dangling --no-progress` (0 is the expected answer),
   `git stash list`, `git tag`, `git branch -a`, and `git reflog`. A blob that exists in history but
   not on disk is exactly what a "deleted secret" looks like.
2. **Scan the Git *config* for embedded credentials.** `git config --list --local` and check every
   key containing `url` / `token` / `password` / `credential` / `extraheader` — `remote.origin.url`
   carrying a PAT is the classic residue. Assert `grep -c 'ghp_\|x-access-token' .git/config` → `0`.
   Also read the commit author (`git log -1 --format='%an <%ae>'`) and confirm it is a
   `users.noreply.github.com` identity, not a personal address.
3. **Sweep *every* value in the secret store, not just credential-shaped ones.** Load all pairs from
   `~/.hermes/.env`, skip values under ~8 chars (pure noise), and check each against the concatenated
   repo text. Reporting "checked 43 stored values" is a far stronger claim than "checked for API
   keys". Then cross-check identifiers harvested from the notes vault as a second corpus.
4. **Re-scan the bytes GitHub serves** (see the two-layer section) and repeat 3 against that text, so
   the claim covers what a recipient would actually clone.
5. **Enumerate every `0x`-address in the repo and classify each one.** The output should read as a
   list of known-public contracts; anything unclassified is a question you answer *before* shipping,
   not a footnote. Predeploys (`0x4200…0006`), the zero address, and protocol constants like the
   OP Stack alias base `0x1111…1111` are all fine — but say so explicitly.
6. **Grade the findings before reporting them.** Run the broad regexes *and* triage their hits:

   | flagged | truth to check |
   |---|---|
   | `private[_\s-]?key\s*[:=]\s*\S+` | matched `BRIDGE_PRIVATE_KEY=` in `.env.example` — **assert the value length is `0`** |
   | 12+ lowercase words (BIP39) | matched an Indonesian warning sentence in a docstring — quote it |
   | `\b[0-9a-fA-F]{64}\b` | usually SHA-256 digests recorded in notes, not keys — say which |
   | "unknown address" | a public contract missing from your own whitelist, not a leak |

   **The rule: a broad regex produces candidates, never conclusions.** For each hit, print the
   matched context and the decisive measurement (value length, surrounding prose, what the address
   actually is). An unconvicted flag self-reported as `❌ ADA 2 pola` forces the user to ask again —
   which is what happened here, and the honest answer was "0 real leaks, 2 of my own regexes fired".
   Over-reporting erodes the same trust as under-reporting.

7. Leave environment-housekeeping findings out of the repo verdict, and report them separately —
   e.g. `~/.git-credentials` still holding a revoked PAT lives on the machine, not in the artifact.

## Push without persisting the credential

`git remote add origin https://<token>@github.com/...` writes the PAT into `.git/config` in
plaintext and leaves it there. Instead:

1. Push once to an explicit one-shot URL:
   `git push "https://x-access-token:$TOK@github.com/<owner>/<repo>.git" main`
2. `git remote remove origin`, then re-add the clean URL:
   `git remote add origin https://github.com/<owner>/<repo>.git`
3. **Assert it, don't assume it**: `grep -c 'ghp_\|x-access-token' .git/config` must print `0`.
   Put that assertion in the verification report — a clean `git remote -v` alone does not prove
   the token is gone from the config file.

## Create-repo 401 is an auth failure, not a permissions failure

When `POST /user/repos` (or any repo operation) returns `401`, do **not** read it as "this account
lacks repo-creation rights". Validate every stored token with `GET /user` first: a revoked/expired
PAT returns 401 for reads *and* writes alike, and `X-Oauth-Scopes` comes back empty for
fine-grained tokens, so scope output alone cannot tell the two apart. Probe in order — each PAT in
the secret store, then `~/.git-credentials` — and if all fail, ask the user for a fresh token and
store it under the **existing** key name (replace the dead entry; do not invent a second key).

Also: `GET /orgs/{name}` returning 404 usually means the target is a **user account**, not an
organisation — create repos with `POST /user/repos`, and expect `affiliation=owner,organization_member`
in the repo listing to surface them.

## One-line installer with GitHub Release binaries (curl | bash, no build on target)

When a project ships a single static binary, the 9Router-style install (`npm i -g` or `curl | bash`) downloads a prebuilt asset instead of cloning+building. Pattern proven 2026-08-09 (spring-router):

1. **Build static per-arch**: `CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags "-s -w" -o spring-router-linux-amd64 .` (repeat arm64).
2. **Create release**: `POST /repos/{owner}/{repo}/releases` `{tag_name, body}` → returns release `id`.
3. **Upload assets**: `POST https://uploads.github.com/repos/{owner}/{repo}/releases/{id}/assets?name=spring-router-linux-amd64` with `Content-Type: application/octet-stream` and the binary as body.
4. **Installer script** (in repo, fetched via raw.githubusercontent.com): detect arch (`uname -m` → amd64/aarch64), `curl -fsSL {base}/download/{tag}/{file} -o bin.tmp`, **verify ELF magic before trusting** — `head -c 4 "$tmp" | grep -q $'\x7fELF'` (a literal `\x7f` pattern does NOT work in bash), then chmod + install.
5. **REBUILD + RE-UPLOAD after every source change** — the installer fetches the release asset, not the repo source. Update assets by `GET /releases/{id}/assets` → `DELETE /releases/assets/{asset_id}` → re-POST. Bump the version constant in install.sh.
6. **raw.githubusercontent.com CDN lags** after push — verify install.sh freshness via `api.github.com/repos/.../contents/install.sh?ref=<sha>` (contents API is fresher than raw).

## Safety pitfalls

- **An over-broad secret glob can silently swallow the very files you intend to ship.**
  A `.gitignore` of
  ```
  config.env
  config.env.*
  !config.env.example
  ```
  left `config.env.example` **untracked** — `git check-ignore -v config.env.example` pointed
  straight at the `config.env.*` line, so the negation did not win and the published repo was
  missing its own config template. Nothing errored; the push simply shipped 10 files instead
  of 11. Fix that worked: drop the overlapping glob and name the secret exactly
  (`config.env` + `!config.env.example`).
  **Assert it, don't eyeball the push output:** after `git add -A`, diff the intended file
  list against `git diff --cached --name-only`, and for every `.example`/template/README you
  mean to ship, run `git check-ignore -v <path>` and confirm it reports nothing.
- **Template/example files must carry documentation values, never the user's real
  infrastructure.** A `proxy.txt.example` written from the live config leaks the user's
  actual proxy endpoints even though it holds no credential — and the user will say so
  (`"domain gua Jangan ada di Repo"`). Use reserved documentation ranges
  (`203.0.113.0/24`, `198.51.100.0/24`) and obvious placeholders (`domainkamu.com`,
  `kamu@gmail.com`, the `4111 1111 1111 1111` test card), then re-scan the pushed bytes for
  the user's real domains/IPs/emails/wallet addresses — not just for keys. Grep the domains
  as **substrings** (`<DOMAIN_REDACTED>`, `<DOMAIN_REDACTED>`, `<DOMAIN_REDACTED>`, `<HANDLE_REDACTED>`) so a value embedded in a
  filename, path, or slug is caught too.
- A successful `git push` does not prove visibility is private.
- A clean pattern scan does not prove secrets are absent; exact-value scanning catches unusual token formats.
- Do not stage first and assume later `.gitignore` changes remove existing index entries; explicitly `git rm --cached` ignored artifacts.
- Do not include local preview images/plans merely because they are harmless; keep source repos focused unless the user wants design artifacts versioned.
- Never expose auth tokens in command output, commit messages, remotes, or final reports.

## Stop, archive, then publish gate

When the source directory is also a runnable bot or service, treat publication as a release boundary rather than a normal Git push:

1. **Stop first.** Stop only task-owned review/production processes and verify they are exited or absent before archiving. Do not leave a polling bot running while publishing its source. Preserve unrelated legacy directories and services.
2. **Create a sanitized archive before Git initialization.** Archive the source tree to a separate timestamped archive directory with a SHA-256 and file count. Exclude Git metadata, all `node_modules` at every workspace depth, build output, binaries, coverage/cache, `.env` files, secrets, wallet/account/runtime state, databases, logs, keys/certificates, local agent state, and nested archives. Use global/basename tar exclusions (`--exclude='node_modules'`), not only `./node_modules`; workspace dependencies may exist below package directories.
3. **Verify the archive.** Inspect archive paths and fail on forbidden artifacts. Run pattern and exact-value scans against non-empty values loaded from local credential stores without printing values. Documented placeholders such as `.env.example` may remain; real values may not. Record archive path/hash in the durable project note.
4. **Harden and stage explicitly.** Add ignore rules for local Hermes state, archives, runtime files, and nested workspace artifacts. Initialize Git only in the requested source directory, stage, and inspect `git diff --cached --name-only`; a clean pre-staging tree is not evidence that the staged tree is safe.
5. **Create the remote with explicit private visibility.** Check authenticated identity and probe the requested owner/repository name before creation. Use the credential dedicated to that owner/account from the local secret store. Create with `private: true`, then verify the API response before pushing.
6. **Push without embedding credentials in the remote URL.** Use an ephemeral askpass/helper or secure configured helper. Remove temporary helper files after the push. Never place a PAT in a remote URL, output, commit message, or durable note.
7. **Verify the remote separately.** Confirm visibility, default branch, local HEAD == remote branch SHA, and remote blob paths. Audit exact prohibited paths and confirm `.env.example` is the only environment file if intended. If content APIs are stale after push, verify commit SHA first and use raw remote blobs or a fresh clone for content checks.
8. **Record completion and boundaries.** Update the project note with archive hash, repository URL/visibility, commit SHA, remote-tree result, and explicit confirmation that legacy production paths were untouched. Leave the source tree clean. If the user asked to stop/only archive, do not restart a bot after publishing.

The proven archive/publish checklist is also available at `references/archive-before-private-publish.md`.

## Verification evidence

Report the private repository URL, visibility, default branch, local/remote SHA equality, remote prohibited-file result, quality-gate status, and legacy-production untouched status. Avoid dumping credential names or values beyond saying authentication was available.