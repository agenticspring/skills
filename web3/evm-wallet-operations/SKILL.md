---
name: evm-wallet-operations
description: Manage EVM addresses, vanity wallets, and key-safe outputs.
version: 0.1.0
author: Hermes
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [EVM, Wallet, Vanity, Hex, Security]
    related_skills: [evm-wallet-set-management, wallet-fund-sweep]
---

# EVM Wallet Operations

Handle EVM address format, vanity generation, and wallet output safely. This
skill explains why an address cannot literally contain arbitrary alphabetic
words, and how to generate a readable hexadecimal prefix or suffix. It does
not fund, mint, or broadcast transactions; use `wallet-fund-sweep` or a
transaction skill for those actions.

## When to Use

- User asks for an address like `0xspring` or `0xdez`
- Generate a vanity prefix/suffix wallet
- Explain EVM hexadecimal address constraints
- Review wallet-generator output before use

## Prerequisites

- Python 3.10+
- `eth-account` installed in the execution environment
- `cast` for optional address/key verification
- Private outputs must stay local with mode `600`

## How to Run

Invoke the project generator through the `terminal` tool:

```bash
cd /root/projects/wallet-cantik-bot
python3 vanity.py --prefix dead --count 1 --threads 8
python3 vanity.py --suffix beef --count 1 --threads 8
```

Use `read_file` for README/source review and `terminal` for the executable
verification. Never print or commit private-key output.

## Quick Reference

```text
EVM address       = 0x + 40 hexadecimal characters
Hex alphabet      = 0-9 a-f
ASCII spring      = 737072696e67
Readable prefix   = 0x7370... ("sp" encoded)
Literal 0xspring  = impossible
ENS alias         = spring.eth (separate naming layer)
Generator         = vanity.py --prefix <hex> --suffix <hex>
Secret output     = mode 600; never commit/share
```

## Procedure

1. **Validate the requested text.** Remove an optional `0x` and check every
   requested character against `0123456789abcdef`. Reject arbitrary letters;
   EVM address text is hexadecimal, not base-36 or ASCII.
2. **Offer the right representation.** For a word containing non-hex letters,
   explain the ASCII-hex encoding. `spring` encodes to `737072696e67`, but
   grinding a 12-hex-character prefix needs `16^12` expected attempts, so use
   a shorter prefix such as `7370`, or use an ENS name/address-book label.
3. **Estimate before grinding.** A k-character exact hex prefix has about
   `16^k` expected attempts. A suffix has the same search cost. Four hex
   characters is practical; five or six may take substantially longer.
4. **Generate with the project.** Run `vanity.py` through the `terminal` tool
   using `--prefix` or `--suffix`, `--count`, `--threads`, and `--case`.
5. **Verify the result.** Check the address has exactly 40 hex characters after
   `0x`, matches the requested prefix/suffix, and the secret JSON is mode 600.
6. **Protect the output.** Keep the JSON local. The `.addresses.txt` file may
   contain public addresses, but the JSON contains the private key and must
   never enter Git, chat, notes, or logs.

## Pitfalls

- `0xspring`, `0xhello`, and `0xdez` are invalid because letters outside `a-f`
  are not hexadecimal.
- ASCII-hex is an encoding, not a shorter address: full `spring` is
  `0x737072696e67...`, still followed by enough random hex to reach 40 digits.
- Vanity grinding creates a new key; it does not rename an existing wallet or
  preserve an existing mnemonic.
- A generator that claims to output a mnemonic must actually populate one.
  Verify the field before relying on it; a private-key-only wallet should be
  documented as such and backed up accordingly.
- Never place generated wallet JSON in a repository. Add output patterns to
  `.gitignore` before running the generator.
- Case-insensitive matching is the normal readable-prefix mode; checksum case
  is presentation, not extra address entropy.

## Verification

```bash
cd /root/projects/wallet-cantik-bot
python3 vanity.py --prefix dead --count 1 --threads 8 --out /dev/shm/vanity-check.json
python3 - <<'PY'
import json, re, os
p='/dev/shm/vanity-check.json'
w=json.load(open(p))[0]
assert re.fullmatch(r'0x[0-9a-fA-F]{40}', w['address'])
assert w['address'].lower().startswith('0xdead')
assert (os.stat(p).st_mode & 0o777) == 0o600
print('vanity address and secret-file checks passed')
PY
```

Load `references/vanity-addresses.md` with `skill_view(file_path=...)` for the
validated session-specific search estimates and output caveats.
