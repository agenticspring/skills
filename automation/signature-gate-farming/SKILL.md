---
name: signature-gate-farming
description: Farm personal_sign whitelist gates browserlessly.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Whitelist, Signature, SIWE, Proxy-Rotation, Web3]
---

# Signature-Gate Whitelist Farming

Farms allowlist/whitelist sites whose ONLY wallet interaction is
`eth_requestAccounts` + `personal_sign` — no gas, no transaction, fully
scriptable without a browser (e.g. WAGIES "DORIS HR" chat interviews). Does NOT
handle paid mints or tx broadcasting (`web3-farmer-bot`, `evm-mint-preflight`
cover those), and does NOT do drainer analysis itself (defers to
`js-bundle-scam-forensics` before any signing). Stdlib + `eth-account` only.

## When to Use

- "Apply whitelist buat semua set" on a site asking only for a signature
- Site shows "Connect Wallet" but the flow turns out to be sign-a-message
- Adaptive chat-bot gate ("interview") before allowlisting wallets
- Rate-limited per IP/household and needs proxy rotation across many wallets

## Prerequisites

- `pip install eth-account` (Account.from_mnemonic needs
  `Account.enable_unaudited_hdwallet_features()` first)
- Wallet source: mnemonic sets or PKs, mode 600, never committed
- HTTP proxy pool, one per wallet, format `http://user:pass@host:port`
- ALWAYS run `js-bundle-scam-forensics` on the site BEFORE signing anything:
  verdict must be zero `eth_sendTransaction` / `signTypedData` / `approve`

## How to Run

Invoke through the `terminal` tool. Canonical invocation (config constants at
top of script: API base, endpoints, answer map):

```bash
python3 <skill_dir>/scripts/signature_gate_apply.py \
  --wallet-file /root/.hermes/.credintial/.springwallet \
  --sets 12-100 --ref <ref_code> --proxy-file .proxies
```

A proven site-specific implementation lives at
`/root/projects/wagies-bot/apply2.py` (WAGIES) — prefer adapting that when the
target matches the worked example.

## Quick Reference

```text
POST /api/session {wallet, ref}   -> app_id + message_to_sign (fresh)
personal_sign (EIP-191 off-chain) -> sig, free, no gas
POST /api/verify {app_id, sig}    -> ok:true + first question
POST /api/message {app_id, text}  -> next question | final verdict object
GET  /api/stats                   -> capacity/acceptance counters
```

## Procedure

1. **Safety audit** the frontend bundle (`js-bundle-scam-forensics`). Sign
   nothing until the bundle proves signature-only interaction.
2. **Map the API** from the widget JS: find every fetch call, the session /
   verify / message endpoints, and whether sessions resume server-side.
3. **Probe once manually** (one wallet, execute_code): session -> sign ->
   verify -> read the actual questions. Record every question variant.
4. **Build an adaptive answer map**: keyword-match each question variant
   (position, employment history, tokenomics quiz, sign-paperwork...) to a
   prepared answer. Empty wallets get DIFFERENT questions than active ones.
5. **Batch with rotation**: one dedicated proxy per wallet; validate proxies
   against a cheap GET endpoint first; fall back to other proxies on network
   errors; sleep 1-2s between wallets.
6. **Handle broken states**: resumed sessions arrive without
   `message_to_sign`; half-verified sessions (server 500 mid-verify) show
   `{resumed:true, history:[]}` — probe `/api/message` to recover them.
7. **Persist results** to JSONL/JSON after each wallet (verdict, title,
   ref_code, letter_url, app_id) so re-runs skip completed sets.

## Pitfalls

- `cast wallet sign <file>` signs the LITERAL PATH STRING, not file contents.
  Pipe via stdin (`printf %s "$MSG" | cast wallet sign --private-key $PK -`)
  or use `eth_account` `encode_defunct(text=msg)` — the reliable path.
- Per-IP limits are enforced as "household" errors even with different
  wallets — wallet-level uniqueness does NOT bypass them; proxies do.
- Separate per-WALLET cooldowns usually exist too ("one application per 24
  hours") — schedule retries, do not hammer.
- Verdicts may be activity-weighted or plain random regardless of answer
  quality; expect ~20% acceptance and treat rejection as retryable, not fatal.
- Server-side 500s mid-verify poison the session state; catch URLError AND
  HTTPError separately — tunnel/proxy failures are not HTTPError.
- urllib ProxyHandler needs the full URL including scheme; `ip:port` strings
  silently fail on HTTPS tunneling.
- Referral codes from early HIRED wallets compound queue position; pass the
  same ref on every subsequent application.

## Verification

```bash
# Smoke test: one wallet, dry shape check (no batch):
python3 -c "import sys; sys.path.insert(0, '<skill_dir>/scripts'); import signature_gate_apply as m; print(sorted(k for k in dir(m) if not k.startswith('_')))"
# Expect: ['ANSWERS', 'apply_one', 'load_wallets', 'post', ...] — imports clean
```

Worked example (WAGIES DORIS HR): load `references/wagies-doris-interview.md`
via `skill_view(name='signature-gate-farming',
file_path='references/wagies-doris-interview.md')`.
