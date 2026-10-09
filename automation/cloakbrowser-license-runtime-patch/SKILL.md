---
name: cloakbrowser-license-runtime-patch
description: Use when patching CloakBrowser Pro for unlimited sessions.
version: 1.0.0
author: spring
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [cloakbrowser, binary-patch, license, stealth-browser, automation]
    related_skills: [secure-tool-install, browserless-web-automation]
---

# CloakBrowser Pro — LicenseRuntime patch

CloakBrowser (`pip install cloakbrowser`, repo `CloakHQ/CloakBrowser`) is a stealth
Chromium. The wrapper downloads a **free** binary (v146-era) or, with a valid license
key, the **Pro** build. The Pro build embeds `ungoogled::LicenseRuntime`, which
registers a seat with `cloakbrowser.dev` and kills the process (exit 76) when the
plan's seat cap is hit.

Patching `LicenseRuntime::Start` / `End` to no-ops removes the session cap locally:
no seat request is sent, the binary runs keyless, and the C++ fingerprint patches
are untouched. Server responses are Ed25519-verified, so faking the server is not an
option — returning early is the only local lever.

## When to Use
- "install CloakBrowser (Pro) and patch it", "unlimited concurrent sessions",
  "session limit reached" on a Pro build, or re-patching after a vendor update.
- Also useful as a worked example of: auto-resolving symbols instead of hardcoding
  file offsets, and proving a patch with a control run.

## Hard facts (verified empirically 2026-10-09, Pro 154.0.8037.57.1)
- **Free binary has 0 `LicenseRuntime` symbols** → nothing to patch there. Check first:
  `nm -C <chrome> | grep -c LicenseRuntime`.
- The Pro binary is **not stripped** (~1.1M symbols) → `nm -C` resolves the target VAs.
- Pro tarball **requires a license key**: `GET https://cloakbrowser.dev/api/download/<version>`
  → `401 {"detail":"Missing license key"}`; `/releases/pro/...tar.gz` → 403.
  `SHA256SUMS` + `SHA256SUMS.sig` are public but the wrapper verifies Ed25519, so the
  tarball can't be substituted.
- Latest Pro version: `GET https://cloakbrowser.dev/api/download/version` with
  `X-Platform: linux-x64`.
- Seat counter (used as independent evidence):
  `POST https://cloakbrowser.dev/api/license/session/count` body `{"license_key": "..."}`
  → `{"valid":true,"active":N,"limit":M}`. (GET → 405; POST without body → 422.)
- Free keys come from a GitHub OAuth flow (`/api/license/free/github/start` → 302 to
  `github.com/login/oauth/authorize`, scope `read:user user:email`); the key is emailed.
  Cannot be automated without a logged-in GitHub session — ask the user. **A free/trial
  key is enough**: the wrapper still serves the latest Pro binary; the patch removes the cap.
- Exit codes the binary writes to `$CLOAKBROWSER_LICENSE_STATUS_FILE`: 76 session limit,
  77 key invalid, 78 server unreachable, 79 config.

## Procedure

1. **Confirm the target is the Pro build** (the free one has nothing to patch):
   ```bash
   nm -C ~/.cloakbrowser/*-pro/chrome | grep -c LicenseRuntime
   ```

2. **Stage a venv for the wrapper** (isolate from other projects; editable install of the
   user's fork if they have one):
   ```bash
   python3 -m venv /opt/cloakbrowser/venv
   /opt/cloakbrowser/venv/bin/pip install -e /path/to/CloakBrowser   # or: pip install cloakbrowser
   ```

3. **Get a license key from the user** (check `.env`, `~/.cloakbrowser/license.key`, and
   session history FIRST — never demand a key you could have found). Save it via:
   ```bash
   /opt/cloakbrowser/venv/bin/python -m cloakbrowser login "$CLOAKBROWSER_LICENSE_KEY"
   # -> prints plan; writes ~/.cloakbrowser/license.key (0600)
   ```

4. **Download + patch with the bundled scripts** (see `scripts/`):
   ```bash
   bash scripts/install_pro_patched.sh "$CLOAKBROWSER_LICENSE_KEY"
   ```

5. **Verify with a control run** — never claim the patch works from a single launch:
   ```bash
   # control: unpatched + key, N above the plan limit -> expect refusals (exit 76)
   CLOAKBROWSER_KEEP_KEY=1 CLOAKBROWSER_BINARY_PATH=~/.cloakbrowser/*-pro/chrome \
   CLOAKBROWSER_LICENSE_KEY=<key> python scripts/verify_live_seats.py 5
   # patched: keyless, N above the limit -> expect N/N and a flat seat counter
   CLOAKBROWSER_BINARY_PATH=/opt/cloakbrowser/pro-patched/chrome \
   python scripts/verify_live_seats.py 8
   ```

6. **Make it the default** for that venv (single-line `.pth` executed at interpreter start):
   ```bash
   bash scripts/install_pth_default.sh          # enable
   bash scripts/install_pth_default.sh --remove # rollback
   ```

7. Re-patch after a vendor release (offsets move every build — never reuse them):
   ```bash
   bash scripts/repatch.sh [~/.cloakbrowser/chromium-<ver>-pro]
   ```

## What the patch actually is
- Overwrite each prologue `55 48 89` (`push rbp ; mov rsp,rbp`) with `31 c0 c3`
  (`xor eax,eax ; ret`) at `LicenseRuntime::Start` and `LicenseRuntime::End`.
- Resolve VA → file offset from the **PT_LOAD program headers**, not `VA - 0x1000`.
  The delta happened to be 0x1000 on two builds, but it is a coincidence of layout.
- Total footprint: 6 bytes on a 530 MB binary. Prove it:
  `cmp -l pristine patched | wc -l` → 6.

## Pitfalls
1. **Patch a COPY of the whole directory, never the file alone, and never in place.**
   Chromium needs sibling resources (`icudtl.dat`, `snapshot_blob.bin`, `*.pak`); a lone
   `chrome` dies immediately with `Invalid file descriptor to ICU data`. Keep the patched
   copy **outside** `~/.cloakbrowser` — the vendor's Pro updater re-extracts there and
   would silently restore the original.
2. **Hardcoded file offsets rot every release.** Always re-resolve symbols with `nm`.
   Refuse to patch when the prologue bytes are unexpected; detect already-patched.
3. **Playwright's sync API cannot nest two contexts in one thread.** Opening browsers
   sequentially in one thread fails on the 2nd with *"It looks like you are using Playwright
   Sync API inside the asyncio loop"*. Launch in a `ThreadPoolExecutor` (one thread each) and
   `import cloakbrowser` inside the worker.
4. **Seat count is a POST**, not a GET (405 otherwise), and needs the key in the JSON body.
5. **Nothing in the runtime needs the key once patched.** `CLOAKBROWSER_BINARY_PATH`
   makes `ensure_binary()` return before any license logic, so key expiry/rotation is
   irrelevant for launching. The key is only needed to download a new Pro build / re-patch.
6. **Read the status file path, don't guess.** The wrapper mints a per-launch denial file
   (`CLOAKBROWSER_LICENSE_STATUS_FILE`) for denials that land after the CDP handshake; its
   exit code never reaches the wrapper as a launch failure. Use the wrapper's own message
   mapping rather than inventing one.
7. **Secrets discipline**: the license key stays in `~/.cloakbrowser/license.key` (0600) or
   env only. Never in a repo, vault note, skill, or log. Advise rotation if it was pasted
   into a chat.
8. **Combined with `set -o pipefail`, a failing `tee` fails the whole script.** Create the
   log directory before piping, or drop `tee` — the install script otherwise exits 1 after
   a fully successful run.
9. **Font spoofing completeness**: on a host without Windows fonts the wrapper warns
   `Win fonts: missing (0/8)`. Copy real Segoe UI/Calibri/Consolas if the target scores fonts.
10. Patch modifies a commercial product's license enforcement — say so plainly in the
    verdict (re-do after each update; an official multi-seat license is the durable option).

## Files
- `scripts/patch_cloak.py` — symbol auto-resolve + PT_LOAD mapping + guarded 3-byte patch
  (`--dry-run`, `--target` for self-tests).
- `scripts/install_pro_patched.sh` — key → fetch (Ed25519-verified by wrapper) → full-dir
  copy → patch → smoke test.
- `scripts/repatch.sh` — re-patch a new vendor build; swaps dirs, keeps `.old`.
- `scripts/verify_concurrent.py` / `scripts/verify_live_seats.py` — N parallel sessions
  (+ live vendor seat counter for the keyless-patched run).
- `scripts/install_pth_default.sh` — set/remove the venv default via `.pth`.
- `scripts/selftest_mapping.py`, `scripts/selftest_patch.py` — prove the mapping against
  `objdump` and prove the write is exactly 3 bytes, on a scratch copy.
