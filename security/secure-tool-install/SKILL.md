---
name: secure-tool-install
description: Secure pipeline for installing third-party security/pentest/crypto tooling — isolated staging, backdoor audit, hash verification, then promote to a sandboxed location. Use when the user says "install safely", "make sure no backdoor", "audit before install", or when installing untrusted binaries/tools from GitHub/PyPI/npm.
version: 1.0.0
author: spring
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [security, install, audit, backdoor, isolation, supply-chain]
    related_skills: [oh-my-open-pentest, captcha-manager]
---

# Secure Tool Install

Install third-party tooling without polluting the system or risking a backdoored binary. The user explicitly requires this workflow: **stage → audit → promote**, never install straight to system-wide paths.

## The Pipeline (ALWAYS this order)

```
1. STAGING    → isolated venv + staging dir, download only (no install)
2. AUDIT      → scan source/bin for backdoor indicators
3. VERIFY     → hash/signature check against upstream
4. TEST       → RUN the tool for real in isolation (strace syscall monitor) to
               catch runtime backdoors (dep install / exfil) that static grep misses
5. DECIDE     → if CLEAN: promote to system-wide (drop isolation)
               if DIRTY : keep isolated OR discard, report to user
```

**KEY USER RULE (do not skip):** Isolation is an AUDIT-PHASE measure only. The
user's explicit instruction: "install di tempat aman dulu lalu kau audit, kalau
pas run/install depensi ga ada kode berbahaya → kau baru gak usah install di
isolasi." Translation: stage + audit + runtime-test in isolation; IF clean,
promote to normal system-wide install and REMOVE the isolation layer. Do NOT
leave tools permanently sandboxed/isolated after a clean audit — that is not
what was asked. Permanent isolation is only for tools you could NOT verify.

## Step 1 — Staging (isolated)

```bash
mkdir -p /opt/<tool>-audit/{venv,staging,audit-logs}
python3 -m venv /opt/<tool>-audit/venv
source /opt/<tool>-audit/venv/bin/activate
pip install --upgrade pip
cd /opt/<tool>-audit/staging
# Download ONLY, never install to system:
pip download <pkg> --no-deps -d ./pkg        # python
# OR fetch release binary to staging (verify URL from GitHub API first):
VER=$(curl -s https://api.github.com/repos/<org>/<repo>/releases/latest | grep -oP '"tag_name": "\K[^"]+')
curl -sL "https://github.com/<org>/<repo>/releases/download/${VER}/<asset>" -o tool.tar.gz
```

**Why:** keeps everything off `/usr/local/bin` and out of the system `PATH` until proven clean.

## Step 2 — Audit (backdoor scan)

For Python wheels:
```bash
unzip -o -q pkg/*.whl -d pkg_unzip
grep -rE "eval\(|exec\(|os\.system|subprocess.*shell=True|__import__\('os'\)|socket\.socket|requests\.post|urllib.*request" pkg_unzip/ 2>/dev/null | grep -v "test" | head
```
For binaries: confirm it's a real ELF/Mach-O, check it runs `--version`, and the version matches the release tag.

**False-positive whitelist** (legit, NOT backdoors):
- `urllib.request.urlopen` in a `doctor`/`version-check` module (PyPI version check)
- `socket.socket` in IPC/client code (`web3/providers/ipc.py`)
- `os.system("black ...")` inside a test-only `compile_contracts.py` helper
- Standard library imports that look scary but are normal (`import subprocess` without `shell=True`)

If a hit is outside these patterns AND contacts a remote host with local data exfiltrated → STOP, report to user, do not promote.

## Step 3 — Verify hash/signature

```bash
sha256sum tool.tar.gz
# Compare against upstream-published checksum if available:
curl -sL "https://github.com/<org>/<repo>/releases/download/${VER}/<asset>.sha256"
```
A matching SHA256 = binary is the genuine upstream artifact. For PyPI wheels, re-downloading from `pypi.org` (official) is sufficient provenance.

## Step 4 — Runtime audit (in isolation, BEFORE deciding)

Static grep can miss a backdoor that only triggers at install-time (a transitive
dep's setup.py phones home) or run-time (a tool exfiltrates host files). Run the
tool for real inside the staging venv while watching syscalls:

```bash
source /opt/<tool>-audit/venv/bin/activate
export PATH="/opt/<tool>/bin:$PATH" PYTHONPATH="/opt/<tool>/lib"
# Network + execve + file-write monitor:
timeout 120 strace -f -e trace=network,execve,openat -o /opt/<tool>-audit/audit-logs/run.strace \
  <tool> <real-args>
# Suspicious = connect() to non-DNS/RPC IP, execve of unknown binary, or
# openat O_WRONLY outside /tmp + the tool's own dirs.
grep -E "connect\(" /opt/<tool>-audit/audit-logs/run.strace | grep -vE "127.0.0.1|::1|AF_UNSPEC|AF_UNIX|8.8.8.8|8.8.4.4" | grep -vE "rpc|cloudflare|github|foundry"
```

A clean run shows only: DNS (8.8.8.8), the expected RPC/CDN endpoint, solc/python
subprocesses, and writes limited to the tool's own cache dirs (/tmp,
/root/.local/share/svm, etc.). If it contacts an unknown IP with local data or
writes outside its sandbox → STOP, report, keep isolated or discard.

## Step 5 — Decide & promote (if clean)

If the runtime audit is clean, the isolation served its purpose — DROP it and
install normally:

```bash
# Binaries → system-wide
cp /opt/<tool>/bin/* /usr/local/bin/ && chmod 755 /usr/local/bin/<tool>
# Python → system site-packages (PEP 668 hosts need --break-system-packages OR
# add the staged lib dir via a .pth file):
SP=$(python3 -c "import site; print(site.getsitepackages()[0])")
echo "/opt/<tool>/lib" > "$SP/<tool>.pth"
# Make a CLI wrapper for python modules (so `which <tool>` works):
echo '#!/bin/bash' > /usr/local/bin/slither
echo 'exec python3 -m slither "$@"' >> /usr/local/bin/slither
chmod 755 /usr/local/bin/slither
# Remove the sandbox/isolation layer — no longer needed
rm -f /opt/<tool>/crypto-sandbox.sh
```

**Why promote:** user explicitly does NOT want permanently-isolated tools once
audited clean. System-wide = simpler to use, no wrapper friction. Keep the
staging dir + audit logs at `/opt/<tool>-audit/` for re-audit records only.

## Hermes/omop tool inventory

After installing or promoting a tool, verify it separately from the skill bundle:
`omop-tools` reports executable path and `--version` for the recon, enumeration,
analysis, and Web3 tool groups. A source directory or catalog entry does not
prove the binary is installed. The portable omop installer must not silently
install third-party tools or overwrite existing binaries; missing tools stay
explicitly marked until the secure stage → audit → verify → promote workflow is
completed.

## Catalog-wide installation and verification

When a repository advertises a large tool catalog, never equate the catalog count with installed binaries. First enumerate every catalog entry, then report three separate counts: catalog entries, bundled source projects, and verified executables. A small hardcoded health list is only a smoke test.

Use a read-only inventory before installation. For opt-in installation, allowlist only simple, auditable package-manager recipes; classify compound/manual recipes as pending instead of executing shell strings blindly. Run installers with bounded timeouts, capture per-tool exit status, and re-run the full inventory afterward. Stop or isolate when a dependency tree becomes unexpectedly broad or long-running—do not claim completion from partial output.

For Hermes packages, verify both the root skill and all nested `skills/*/SKILL.md` files were copied into `${HERMES_HOME:-$HOME/.hermes}/skills/<name>/`; fail installation if source and destination counts differ. Verify the installed CLI and adapter from a clean temporary `HERMES_HOME`/prefix before publishing.

## Hermes/omop tool inventory

After installing or promoting a tool, verify it separately from the skill bundle: `omop-tools` reports executable path and `--version` for the recon, enumeration, analysis, and Web3 tool groups. A source directory or catalog entry does not prove the binary is installed. The portable omop installer must not silently install third-party tools or overwrite existing binaries; missing tools stay explicitly marked until the secure stage → audit → verify → promote workflow is completed.

## omop catalog integration (when adding to omop)

When the audited tool goes into `oh-my-open-pentest/tool-catalog.json`:
- Set `"isolated": false` and `"install_path": "/usr/local/bin"` (or
  `"system-python"`) after a clean audit.
- The `check` command must match how the tool is actually invoked:
  - binary → `"check": "test -f /usr/local/bin/forge"`
  - python module → `"check": "python3 -c 'import slither' 2>/dev/null"` and
    `"base": "python3 -m slither"` (NEVER `"which slither"` — modules aren't on PATH).
- `omop` reads catalog from `~/.hermes/skills/oh-my-open-pentest/tool-catalog.json`
  (root) AND `skills/oh-my-open-pentest/tool-catalog.json` (nested). If the skill
  repo is nested (remote has `skills/oh-my-open-pentest/...`), edit BOTH and sync
  `omop.py` to `/usr/local/bin/omop` after every change.
- GitHub push gotcha: if the remote repo has unrelated history (e.g. upstream
  source tree), `git pull --allow-unrelated-histories` is refused — use
  `git reset --hard origin/main` to adopt remote structure, then overlay your
  changes on the correct (nested) paths, then commit+push. Ask the user
  force-push vs merge if histories truly diverge.

## Pitfalls

1. **Audit is a PHASE, not a permanent state** — the user's rule: isolate to
   audit, then promote system-wide and drop isolation if clean. Do NOT leave
   tools permanently sandboxed/isolated after a clean audit. (This directly
   overrides any "always keep isolated" reading — user corrected it 2026-07-08.)

2. **Alias vs function in wrapper** — `alias slither=...` fails in non-interactive
   shells (`bash -c`). Use a shell function. (Hit live: `slither: command not found`.)

3. **Python module tools need a `which`-able wrapper** — `slither` is
   `python3 -m slither`, not a binary. After promoting, write
   `/usr/local/bin/slither` as `#!/bin/bash / exec python3 -m slither "$@"` so
   `omop`'s `check: "which slither"` resolves. Same for any python-module CLI.

4. **PEP 668 hosts** — `pip install` into system python is refused ("externally
   managed"). Either `pip install --break-system-packages` or drop a `.pth` file
   in site-packages pointing at the staged lib dir (`echo "/opt/<tool>/lib" >
   $SP/<tool>.pth`). The `.pth` approach is cleaner and survives pip upgrades.

5. **omop catalog `check` must match real invocation** — binary →
   `test -f /usr/local/bin/forge`; python module →
   `python3 -c 'import slither' 2>/dev/null`. Never `"which slither"` for modules.

6. **omop reads catalog from BOTH root and nested paths** — if the skill repo is
   nested (`skills/oh-my-open-pentest/...`), edit both `tool-catalog.json` copies
   and re-sync `omop.py` → `/usr/local/bin/omop` after each change, or `omop tools`
   shows stale/missing entries.

7. **GitHub push on divergent history** — remote may have upstream source tree
   (unrelated history). `git pull --allow-unrelated-histories` is refused; use
   `git reset --hard origin/main` to adopt remote layout, overlay changes on the
   correct nested paths, commit, push. Ask force-push vs merge if truly divergent.

## Real example (crypto tooling, 2026-07-08)

Installed: slither-analyzer 0.11.5, web3 7.16.0, foundry 1.7.1 (forge/cast/anvil).
1. Staged in `/opt/crypto-audit/venv` + `/opt/crypto-tools/{bin,lib}`.
2. Static grep of 1573 .py files → only legit false-positives.
3. foundry SHA256 `cf7e688e...` matched upstream; `solc` via py-solc-x.
4. **Runtime audit** with `strace`: slither 0 net/0 suspicious execve; web3/cast
   only DNS+RPC publicnode; forge only GitHub/CDN + writes to /root/.local/share/svm.
5. **Promoted system-wide** (`/usr/local/bin`, `.pth` for python), removed sandbox.
   `omop tools crypto` → 5/5 ✅. Audited clean → no isolation retained.

## Support files
- `references/dynamic-contract-audit.md` — how to audit an unverified EVM contract
  with NO source (Blockscout 404): `cast code` + selector scan + storage reads.
- `scripts/sandbox-run.sh` — OPTIONAL runtime sandbox runner (keep ONLY for tools
  you could NOT verify; not needed after a clean audit).
