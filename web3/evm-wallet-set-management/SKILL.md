---
name: evm-wallet-set-management
description: Generate, back up, and format EVM mnemonic wallet sets.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Wallet, Mnemonic, EVM, Backup, Formatting]
    related_skills: [osnm-z-mint, evm-mint-preflight]
---

# EVM Wallet Set Management

Manage a mnemonic wallet-set file used by Hermes signer tools (OSNM-Z wrapper,
`cast`, batch airdrop/WL workflows). Covers safe expansion from N to M sets,
labeled `Set <N>` formatting, backup before mutation, and post-write
verification. Never prints or persists private keys; all derivation happens
through `cast` subprocesses with ephemeral temp files.

## When to Use

- User asks to add/generate more wallets to reach a target count (e.g. "bikin 50 baru biar total 100").
- The wallet file format is inconsistent (unlabeled mnemonic lines appended to a labeled file).
- Need a backup before expanding or rewriting the wallet source.
- Mapping wallets (Set N -> address) must stay consistent with previously used mappings.

## Prerequisites

- `cast` (Foundry) — `command -v cast || curl -L https://foundry.paradigm.xyz | bash`
- Wallet source file (default): `/root/.hermes/.credintial/.springwallet` — must stay mode `600`.
- Backup directory: `/root/archives/`

## How to Run

Invoke through `execute_code` (Python + `cast` subprocesses). Use
`tempfile.NamedTemporaryFile(dir='/dev/shm')` for mnemonic inputs, never a
persistent file. Keep output to metadata only (counts, labels, addresses,
statuses) — never print mnemonic words or private keys.

## Quick Reference

```text
cast wallet new-mnemonic --words 12 --json   # generate one set (stdout JSON)
cast wallet private-key --mnemonic <tmpfile> # validate a mnemonic, prints 0x64-hex key
cast wallet address --private-key <pk>       # derive address from key
```

## Procedure

1. **Backup first.** Copy the wallet file to
   `/root/archives/spring-wallet-<UTC-ts>.springwallet.bak`, `chmod 600`.
2. **Extract current valid sets** in file order: for each line whose word count
   is in `{12,15,18,21,24}`, write it to a temp file, run
   `cast wallet private-key --mnemonic <tmp>`, and keep it only when stdout
   matches `0x[0-9a-fA-F]{64}`. Remove temp file in every path.
3. **Generate the delta.** Loop `cast wallet new-mnemonic --words 12 --json`,
   parse `mnemonic` (or join `words`), skip duplicates, until N new unique
   sets exist.
4. **Append atomically.** Build the new content with labeled format:

   ```text
   # header comment lines
   Set 1
   <mnemonic>
   Set 2
   <mnemonic>
   ...
   ```

   Write to a `.tmp` sibling, `chmod 600`, then `os.replace` over the target.
5. **Verify after write.** Re-extract valid sets, assert count == expected and
   all unique; re-derive addresses for the first and last mapped set and
   confirm they match the existing mapping JSON (when one exists).
6. **Check the signer wrapper still works.** For OSNM-Z run
   `SPRING_OSNM_VALIDATE_ONLY=1 SPRING_OSNM_CHAIN=<chain> osnm-z doctor`
   (single-set and all-sets modes) and confirm the reported `wallet_sets`.

## Pitfalls

- Header/comment lines can look like mnemonics (12+ words) but fail the
  checksum — always validate with `cast wallet private-key`, never count by
  word count alone.
- Direct shell heredocs/quotes with mnemonic content break; use Python
  subprocess list form or `shlex.quote`.
- A mapping created before expansion stays valid only if the set ORDER is
  preserved (new sets appended at the end, labeled after extraction in file
  order). Verify addresses against the mapping, not just counts.
- Never `chmod` the wallet file above 600; never write mnemonic/private key
  material into repos, logs, Obsidian, or the session.
- Backups live in `/root/archives/`; keep at least the pre-mutation backup
  until the new file is verified twice.

## Verification

```bash
stat -c '%a' /root/.hermes/.credintial/.springwallet   # expect 600
# plus: valid-set count == target, unique == target, and
# first/last mapped address matches the mapping JSON used downstream.
```
