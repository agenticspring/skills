# Sanitized share artifact — worked case (2026-09-27)

Brief: *"buatkan repo private di agenticspring untuk script bridge ke giwa. Yg kita gunakan
temanku mau minta scriptnya. Pastikan ga ada data sensitif kita disana karena wallet yg kau buat
untuk tes giwa akan terus gua gunakan kedepannya."*

Three constraints in one sentence, and only the first is a normal secret-hygiene job:

1. publish a **copy** of working scripts for a third party;
2. zero sensitive data;
3. **a specific asset will stay in use** — the test wallet must not be exposed.

## Outcome

`agenticspring/giwa-bridge` (private, branch `main`, 10 files, MIT).

```
README.md               risk-first: one-way bridge, risk table, usage, tech detail, 6 pitfalls
bridge.py               bridge ETH L1 -> L2 + preflight + receipt verification
watch_and_bridge.py     wait for funding, fire the broadcaster on arrival
verify_bridge.py        end-to-end verification (L1 receipt + L2 balance)
giwa_status.py          chain status, portal escrow, withdrawal liveness, admin
giwa_common.py          helpers, public on-chain constants, tiny .env loader
.env.example            template, all values blank
.gitignore              .env, pk.txt, *.key, address.txt, keystore*.json, plan.json …
requirements.txt        requests, eth-account, pycryptodome
LICENSE                 MIT + one-way warning
```

## Exclusion table (the part a generic scan misses)

| excluded | why | how |
|---|---|---|
| bridge wallet private key | obvious | env `BRIDGE_PRIVATE_KEY` **or** `--pk-file` (default `./pk.txt`, gitignored) |
| `address.txt` (the wallet address) | **user will keep using the wallet** — public on-chain, but it labels their live operation | gitignored; nothing in the repo references it |
| LLM/RPC provider API key | credential | env `L1_RPC_URL`, default a public endpoint |
| **leaked private RPC (host + path token)** | **the user's edge.** The path token is an access credential; sharing it burns the endpoint | replaced with empty `GIWA_L2_RPC=` + README line explaining the recipient supplies their own; the dependent feature degrades with a printed skip |
| recon scripts that hardcode that RPC | same, plus they are a different brief | offered separately after sanitisation |
| PATs, webhook URLs | credentials | never in the tree |

Make the endpoint-dependent feature **optional**: `bridge.py` runs fully with `GIWA_L2_RPC` empty
and only skips the L2 balance poll. A share artifact that crashes without the private dependency is
not actually shareable.

## Layer-1 scan (local staged tree)

Load real secret values from the local store and confirm each is absent from every file in the repo
dir; add generic patterns. Print a per-value `✅ bersih` / `❌ BOCOR di <file>` line.

```python
SECRETS = {
  "PK dompet bridge": pk_file_contents,
  "PK 12 char":       pk[:12],            # catch partial leaks too
  "provider API key": ENV["ALCHEMY_API_KEY"],
  "private RPC path": "exHgkb748URTmq3FBHi8fCWoJnsg9uWf",
  "private RPC host": "giwa-mainnet.everblocks.io",
  "user wallet":      "0x0D1164F0…",      # both cases
  "GITHUB_TOKEN":     ENV.get("GITHUB_TOKEN",""),
  "Discord webhook":  ENV.get("GC_DISCORD_WEBHOOK",""),
  "Telegram token":   ENV.get("TELEGRAM_BOT_TOKEN",""),
}
PATTERNS = {"64hex": r"\b[0-9a-fA-F]{64}\b", "0x+64hex": r"0x[0-9a-fA-F]{64}",
            "provider url": r"g\.alchemy\.com/v2/[A-Za-z0-9_-]{15,}",
            "pat": r"ghp_[A-Za-z0-9]{30,}"}
```

Result: 11 values + 4 patterns, **all clean**.

Stage-inspection gate before committing — this is what actually catches `.gitignore` mistakes:

```bash
git add -A
git diff --cached --name-only | grep -iE '\.env$|pk\.txt|\.key|secret|credential|address\.txt' \
  && echo '!!! STOP' || echo 'clean'
```

## Layer-2 scan (bytes GitHub actually serves)

```python
tree = GET /repos/{o}/{r}/git/trees/main?recursive=1      # blob paths
text = ""
for p in blobs:
    d = GET /repos/{o}/{r}/contents/{p}?ref=main          # base64 "content"
    text += base64.b64decode(d["content"]).decode()
# then run the SAME SECRETS/PATTERNS dict against `text`
```

Result: 10 files fetched, **zero sensitive values**, zero pattern hits.

## Push without persisting the token

```bash
git config user.name  "agenticspring"
git config user.email "agenticspring@users.noreply.github.com"
git branch -M main
TOK=$(grep '^GITHUB_TOKEN_2=' ~/.hermes/.env | cut -d= -f2)
git push -q "https://x-access-token:$TOK@github.com/agenticspring/giwa-bridge.git" main
git remote remove origin
git remote add origin https://github.com/agenticspring/giwa-bridge.git
grep -c 'ghp_\|x-access-token' .git/config      # must be 0
```

`git remote -v` showing the clean URL is not proof — assert the config file directly.

## Functional check after sanitisation

Both scripts were exercised with a **throwaway key** (never the real one) and a normal RPC:

```
bridge.py 0.001 --dry-run   ->  preflight passed via eth_call state-override, no broadcast
giwa_status.py              ->  ran fully; printed escrow, gameCount()==0, admin threshold/owners
```

Proving execution after sanitisation is the step that distinguishes "sanitised" from "broken".

## Auth state found, and the fix

All three credential sources (`GITHUB_TOKEN`, `GITHUB_TOKEN_2`/`GH_TOKEN_2`, `~/.git-credentials`)
returned **401** on `GET /user`, and `gh auth status` agreed ("The token in GITHUB_TOKEN is
invalid"). A fresh PAT was requested from the user and written over the **existing** key
(`GITHUB_TOKEN_2` + `GH_TOKEN_2`) — same key names, no new ones. `GET /orgs/agenticspring` returned
404, which identified it as a **user account**, so creation used `POST /user/repos`.

Lesson: a 401 on create-repo is an authentication failure. Do not report it as a permission
problem, and do not spawn a new env key for the replacement token.

## Report shape the user got

Repo URL + visibility, per-file table, the two scan results verbatim, the exclusion table with
reasons, the functional-test output, confirmation the original `pk.txt` is untouched
(`-rw-------`, address still matching), plus the two follow-ups: PAT rotation advice for the token
pasted into chat, and the still-dead primary PAT.
