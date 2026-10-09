# Auditing a handed-over signing tool before it touches a funded wallet

Trigger: the user drops a zip/script/toolkit (*"ini apa ya?"*, *"coba cek ini"*) that will sign,
transfer, or move funds. Delivers a verdict, not an impression — and never runs it.

Two separate questions, and a tool can pass the first perfectly while failing the second:

1. **Is the destination real?** (provenance — cheap and decisive)
2. **What does it sign, and who decides the contents?** (the only part that can drain you)

Genuine infrastructure is the *normal* setting for a drain vector: the endpoint is real, and the
transaction it hands back is the attack surface.

## 1. Provenance — evidence, not vibes

```bash
# a) who owns the host? reject on a mismatched apex
curl -sv --max-time 15 https://<api-host>/ 2>&1 | grep -iE "subject|issuer|SSL certificate verify"
#    expect subject: CN=<apex> and a SAN matching the host actually called

# b) is the endpoint REAL? 404 vs 400-with-a-semantic-error is the whole test
curl -s -o /dev/null -w "HTTP %{http_code}\n" "https://<api-host>/<path>?param=<dummy>"
#    real + validating -> 400 {"error":"Insufficient SOL for fee"} / {"error":"Invite not found"}
#    fabricated        -> 404, or a generic 200 HTML shell
curl -s -o /dev/null -w "HTTP %{http_code}\n" "https://<feature-site>/<page>"

# c) did the user re-send the same archive? prove it, don't re-review it
sha256sum old.zip new.zip        # equal hash => same bytes, say so plainly
```

A marketing page returning 200 proves nothing. (a) and (b) are what turn "I think this is X's
feature" into a fact you can state.

## 2. Static scan — exfiltration and obfuscation

```bash
grep -cE "eval\(|Buffer.from\(['\"][A-Za-z0-9+/=]{40,}" tool.js      # expect 0
grep -noE "https?://[^'\"\` ]+" tool.js | sort -u                    # enumerate EVERY destination
```

A third unknown host is the finding. Clean here is necessary but **not sufficient** — a tool can
be readable, honest about its purpose, contact only legitimate services, and still be dangerous
to run.

## 3. The signing path — where money is actually lost

Look for the deserialize → sign → broadcast sequence:

```js
const vtx = VersionedTransaction.deserialize(Buffer.from(craft.transaction, "base64"));
vtx.sign([fundedKeypair, ephemeralKeypair]);       // <- what is IN here?
await conn.sendRawTransaction(vtx.serialize());
```

If the transaction body comes from a **server response** and there is

- no `connection.simulateTransaction(vtx)` before signing,
- no instruction decode,
- no assertion on recipient / amount / mint,

then the tool signs whatever the server says, every time. That is a drain vector **even when the
server is genuine** — DNS spoofing, MITM, upstream compromise and a malicious update all reduce
to the same outcome, and the signer is the wallet holding the capital.

Minimum hardening before pointing it at a funded wallet: simulate unsigned → decode the
instructions → assert recipient + amount + mint against what the user asked for → add a `--dry`
that prints the decoded instruction set → only then permit a live send.

This is the pattern the rest of this library already standardises on: the HONKERS join flow does
`eth_call` simulation *before* `sendRaw`, and the fleet's capital-rotation tool runs
`simulateTransaction` pre-flight on every hop, verifying by balance effect rather than RPC status.
A tool that skips simulation is an outlier, not an acceptable variant.

## 4. Secret-handling observations worth reporting

- **Plaintext key sidecars.** A toolkit that appends an ephemeral secret key into a JSONL log makes
  that log a bearer instrument — whoever holds the file can claim the funds before the intended
  recipient. Report it; require mode 600 and purge after redemption.
- **A shareable code derived from a secret's prefix.** Quantify before calling it fatal: 20 of ~88
  base58 characters ≈ 117 bits revealed against a 256-bit seed ⇒ ~139 bits remain, unbruteable in
  practice but a sloppy design. State the number. "Sloppy but not exploitable" and "catastrophic"
  are different verdicts and the user needs the true one.
- **Defaults that lie:** a public RPC default, status-based (rather than balance-effect)
  confirmation, or a missing `--dry`. Reportable, ranked *below* the signing issue.

## 5. Report shape

Verdict first, in one line — *"bukan malware, tapi bukan sesuatu yang gue saranin dipakai apa
adanya"*. Then: what it is / what it does → provenance table with the raw evidence → risks ranked
with the signing one on top → relevance to the current project → one concrete offer (harden it, or
leave it). No hedging in both directions: pick the verdict the evidence supports and name which
check produced it.

## Case study — Jupiter "Magic Link" / gift toolkit (2026-09-26)

Claimed: build a claimable SOL/token link with no browser and no wallet extension.

| Check | Result |
|---|---|
| `ultra-api.jup.ag` cert | `CN=jup.ag`, Google Trust Services, SAN matched — real |
| `GET /invite/craft-invite` (dummy params) | `400 {"error":"Insufficient SOL for fee"}` — real and validating |
| `GET /invite/craft-claim` (dummy params) | `400 {"error":"Invite not found"}` — real |
| `https://jup.ag/gift` | 200 — the feature exists |
| Obfuscation / embedded blobs | 0 |
| Network destinations | exactly two: Jupiter Ultra + Solana RPC. No exfiltration |
| Signing path | **`deserialize(server tx)` → `sign([senderKp, ephKp])` → broadcast. No simulate, no decode** |

Verdict: a genuine Jupiter feature (not a drainer, nothing stolen) — **but** it signs a
server-authored transaction with the funded key and no verification, and the ephemeral secret ends
up in plaintext in `jup_links.jsonl`.

Genuinely useful property: the claim is signed by the ephemeral key **only** and Jupiter's gas tank
pays the fee, so a receiver address needs **zero SOL**. That matters when the downstream action is
also gasless — e.g. game crate opens cost no gas, so a fresh identity can be funded with the token
alone.

Honest limit to state in the same breath: this does **not** unlink the sender on-chain. The funding
transaction still originates from the sender into escrow. Do not present it as a mixer without
on-chain proof.
