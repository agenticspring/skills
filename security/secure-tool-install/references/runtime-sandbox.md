# Runtime Sandbox — Technique & Verification

## Why (threat model)
Install-time isolation (staging → audit → promote to `/opt/<tool>`) only addresses *supply-chain* risk. The user's explicit requirement: malicious code can also appear at **dependency-install time** (a transitive dep pulls a payload) or **run-time** (the target contract/tool executes harmful logic — reads `/root/.hermes/.env`, writes host files, phones home). Both must be contained.

## Mechanism
Linux namespaces via `unshare`:
- `--user --map-root-user` → inside the NS, UID 0 maps to the *real* unprivileged user. No host privileges, no escape.
- `--mount` → private mount namespace. Bind host dirs read-only; put `/tmp` on tmpfs (ephemeral).
- `--net` (or not) → separate network namespace (no routes) vs inherit host net.

Result: a compromised/tool-targeted process inside the NS can read host files only if they were bind-mounted (and those are ro), cannot write anywhere persistent, and (default) cannot reach the network.

## Network-mode inversion (the gotcha)
`unshare --net` = NEW network namespace = **air-gapped** (no default route). So:
- To AIR-GAP a run: pass `--net` to unshare.
- To allow RPC/fork (host net): OMIT `--net` so the NS inherits the host network stack.

In the wrapper, the user-facing `--net` flag must therefore *remove* `--net` from the unshare args. Reversing this makes outbound calls fail with `error sending request for url (...)`.

## Verification recipe (proves isolation works)
```bash
# 1. Prereq: user namespaces available
unshare --user --map-root-user echo ok     # must print: ok

# 2. Air-gap: slither runs, no egress
sandbox-run.sh slither /path/Test.sol      # works offline

# 3. Host-net: RPC read works only with --net
sandbox-run.sh --net cast block-number --rpc-url https://ethereum-rpc.publicnode.com
# -> prints a block number (e.g. 25485643)

# 4. FS isolation: cannot read host secrets from inside NS
sandbox-run.sh --net bash -c 'cat /root/.hermes/.env'   # must FAIL / be blocked
```

## Real deployment (2026-07-08, crypto tooling)
- Tools: slither 0.11.5, web3 7.16.0, foundry 1.7.1 (forge/cast/anvil) at `/opt/crypto-tools`.
- Sandbox: `/opt/crypto-tools/crypto-sandbox.sh` (copy of `scripts/sandbox-run.sh` with `<tool>`→`crypto`).
- Deep audit: 1573 `.py` files grepped for `eval/exec/os.system/subprocess-shell/socket/network` → 0 real backdoors (false positives: `ast.literal_eval`, `attr` class generator, `aiohttp` socket internals).
- solc: installed via `py-solc-x` → `/opt/crypto-tools/lib/bin/solc`, linked into `/opt/crypto-tools/bin`, added to sandbox PATH.
- Audit logs: `/opt/crypto-audit/audit-logs/install-2026-07-08.md`, `sandbox-2026-07-08.md`.
