# Porting a vendor operator package onto this host

For packages built by someone else, for *their* box, often on a newer runtime. The goal is a
verified, runnable deployment with no vendor credentials baked in and no funded wallet or
production state orphaned by the port.

Worked example: a multi-wallet bot fleet (Node runner + Python orchestrator, 30+ files) ported
from a vendor's WSL box to this VPS.

---

## 1. Recon the config surface before touching anything

```bash
grep -rn "/home/<their-user>\|ROOT *=\|HOST *=\|USER *=\|TTL *=\|/root/" \
  --include=*.py --include=*.mjs --include=*.cjs --include=*.json .
```

Portable roots (`os.path.dirname(os.path.abspath(__file__))`) need no work; everything else
does. Rewrite in bulk, then **assert zero remain** — one missed path resurfaces later as a
mystery "file not found":

```bash
grep -rl "/home/<their-user>" . --include=*.py --include=*.mjs | while read -r f; do
  sed -i 's|/home/<their-user>/<their-dir>|/root/<our-dir>|g' "$f"; done
grep -rn "/home/<their-user>" . --include=*.py --include=*.mjs | wc -l   # must print 0
```

## 2. Syntax gates BEFORE trusting any of it

```bash
for f in *.mjs *.cjs; do node --check "$f" >/dev/null 2>&1 || echo "FAIL $f"; done
for f in *.py;  do python3 -m py_compile "$f"  || echo "FAIL $f"; done
```

Nothing in a vendor package is proven until it compiles on *this* interpreter.

### Python version trap that bit us

A backslash inside an f-string **expression** is legal only on Python ≥3.12 (PEP 701). On
3.11 it fails with `SyntaxError: f-string expression part cannot include a backslash`.
Vendors on 3.12 never see it. Fix by hoisting the expression above the f-string:

```python
# breaks on 3.11:
send(f"{'\u2705' if ok else '\u26A0\uFE0F'} done (pid {rec.get('pid')})")
# works everywhere:
mark = "\u2705" if ok else "\u26A0\uFE0F"
send(f"{mark} done (pid {rec.get('pid')})")
```

`py_compile` reports one at a time; find them all at once by flagging any brace group inside
an f-string that contains a backslash:

```python
import re
for i, line in enumerate(open("target.py", encoding="utf-8").read().split("\n"), 1):
    if not re.search(r'''f["']''', line):
        continue
    for m in re.finditer(r"\{([^{}]*)\}", line):
        if "\\" in m.group(1):
            print(i, line.strip()[:130])
            break
```

## 3. De-hardcode the vendor's providers and accounts

Vendor packages routinely bake in *their* proxy provider, host, pool label and TTL. Strip it:
read the provider from a config file with an environment override, ship a committed `.example`
template, and **fail with a clear message when unconfigured** rather than silently using
someone else's account.

```python
def provider() -> dict:
    c = {"host": "", "user_prefix": "", "ttl": 3600}
    if os.path.exists(CFG):
        c.update(json.load(open(CFG)))
    c["host"] = os.environ.get("GC_PROXY_HOST", c["host"])
    c["user_prefix"] = os.environ.get("GC_PROXY_USER", c["user_prefix"])
    return c
```

## 4. Add a mode that runs without the optional dependency

If every operation tunnels through a proxy, add a direct mode (omit the proxy arguments when
the slot has none) or you cannot smoke-test a single unit before buying proxy capacity. Pair
it with an explicit warning above a small threshold, because running many identities from one
IP is the detection axis:

```python
direct = [e["slot"] for e in slots if not e.get("proxy")]
if len(direct) > 2:
    print(f"  !! WARNING: {len(direct)} slots have no proxy. One identity per IP is the rule.")
```

## 5. Generate the state files the vendor expected you to hand-write

"Create your own `fleet_map.jsonl`" is where inconsistency creeps in (address typed wrong,
keyfile pointing at another slot's key). Write a generator and make it **cross-check keyfile →
address offline**, so a mismatch is caught before it costs anything:

```python
addr = str(Keypair.from_bytes(base58.b58decode(open(r["keyfile"]).read().strip())).pubkey())
if addr != r["address"]:
    print(f"MISMATCH {r['wallet']}: {addr} != {r['address']}")
```

**Reuse an already-funded identity as the first slot** rather than generating a fresh set —
never orphan something that already holds a gate balance or live state. Add a `verify`
subcommand so the check is one command, not a remembered snippet.

## 6. Permissions: enforce on EVERY write, not just on create

Regression that bit us: the library's save path chmod'd `600` **on create**, but an ad-hoc
probe script wrote the same JSON with a plain `open(path, "w")` and the file came back
**644 (world-readable) with a private key inside**. Any second writer defeats a create-time
chmod. Bake the mode into the open and re-assert it:

```python
fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as fh:
    json.dump(state, fh, indent=1)
os.replace(tmp, path)
os.chmod(path, 0o600)     # enforce on every write
```

Layout that works: `keys/` and `run/` at `700`, every key and state file `600`, all of it in
`.gitignore`. After the port, verify with `stat -c '%a %n'`, and grep the tree for long
base58-looking literals to prove no secret leaked into a non-key file.

## 7. Read-only dry run before anything live

Most packages ship a recon flag (`--dry`) that logs in, prints identity/geo, and lists targets
without spending quota. Run it. It validates the whole transport + auth path for free and
gives the real `[me]` line (quota left, gate state) needed before committing funds.

---

# How a working multi-identity fleet is shaped

Useful when the thing being ported is a fleet, and as a checklist for what the vendor got
right (or didn't).

| Piece | Design that works |
|---|---|
| Runner | single-file, direct API, no browser; `fetch` with a `curl -x` fallback for SOCKS5 |
| Transport | **one sticky residential session = one IP per identity**, TTL ~1h; rotate the session id if the tunnel drops mid-run |
| Orchestrator | `map` / `precheck` (fail-closed gate check) / `start` / `stop` / `status` / `balances` |
| Supervision | watcher that restarts dead or stale runners, heals a stale pid map, rotates capital, alerts |
| Liveness truth | **log mtime**, never a pid file — stale pid maps cause both false death reports and duplicate runners |
| Heartbeat | an `[hb]` line every ~20 s so the supervisor can tell "hung" from "quietly working for 4 minutes" |
| Process model | transient systemd units (`systemd-run --user --unit <name>`), **not** children of the watcher, or restarting the watcher kills every runner via cgroup inheritance |
| Gate cache | daily memo per slot so the supervisor can restart without a live check |
| Guards | per-slot daily restart budget + cooldown; skip slots out of quota (that is the rotator's job) |

## Capital rotation between identities

When the gate is a **hold** (not a spend) and the daily cap is per identity, fresh identities
need existing capital moved to them. Pattern: N intermediary ("washer") wallets and a
`source → W[a] → W[b] → target` route with randomised hops, amounts and delays.

- Washers must be seeded with gas from an **external** source, never from the source wallet —
  otherwise the hop recreates the exact link it is meant to break.
- Forward the source's whole remaining gas float so the next generation can pay fees.
- Every hop: preflight `simulateTransaction`, then verify by **balance effect**; ambiguous
  status ⇒ **stop**, never resend.
- Stop the source runner before a live move, or the gate drops mid-run.
- Mark a rotation "handled" **only after a verified live success**. Marking before execution
  while dry-run was still on stranded capital on a drained wallet and the target never got
  funded — measured: 10.5k tokens stuck, fleet silently running 9 of 10.
- Honest limit the vendor states themselves: hop mixing only breaks the **direct** link;
  transitive clustering still connects source and target.

## Payout rail

Payouts may not be in the native token. One such platform pays out in **USDC on-chain minus a
2% fee** while the native token barely moves (rent refund only) — an audit checking
`getBalance` reports "nothing arrived" while the money is sitting there. Always check the token
the platform actually pays in, and treat per-identity token balance as the cheapest detector.
Assets that are gone are usually **sold**, not stolen — check the destination against your own
address list before suspecting anything.

## Triage order for "it produced nothing"

Never debug the pipeline before classifying which layer failed:

1. **Runner layer** — alive and actually acting? (count the work lines *after* the last run
   marker, or you are reading a previous run)
2. **Anti-abuse layer** — explicit rejection codes on the action ⇒ payload/signal gap
3. **Capital layer** — did the money actually reach the identity you started?
4. **Luck** — only then compute the expectation

Pull the odds fresh (`GET /v1/store`, `GET /v1/stats`) and do the arithmetic before calling
anything broken:

```
EV per action  = chance x mean realised value
capacity/day   = identities x actions_per_identity_per_day
sanity check   = P(zero over N) = (1 - chance)^N
```

Worked example: chance 1.099% (≈1 in 91), mean realised value $13–18, 10 identities × 24/day
⇒ ~2.6 wins/day, and P(zero) ≈ 72% over a 30-action sample. A small sample of zeros is **not**
evidence of a broken pipeline.

## Reporting the port: prove provenance, don't assure it

The user asked *"did you edit it?"* — twice, having also asked whether the slow runtime came from
the vendor's design or from your changes. Answer with a categorised diff, not a promise.

Measured shape of one such port (30+ vendor files):

```
zip hash      24552647…821b5   identical across both copies the user sent
engine        runner.mjs       c130b8cb…413dc  byte-identical to vendor
12 files differ: 9 = path rewrite ONLY, 3 = real patches (fleet.py 22 lines,
                watch_cards.py 18, fix_proxy.py 31 — all config/mode, zero logic)
```

Method: `sha256sum` the claimed-untouched files; for the rest, normalise your own rewrite and
diff again so path churn does not hide real edits:

```bash
sed 's|/root/<ours>|/home/<vendor>|g' deployed/x.py | diff - vendor/x.py | grep -c '^[<>]'
```

Zero means "path rewrite only". Then state the classification in the reply, with each real patch
listed and justified. Keep the engine byte-identical: patch the wrappers, orchestrator, and
config — never the file that performs the action.

## Alerting that a human will actually read

- **Transport.** The vendor's notifier was Telegram-only (token + chat read from the shared env
  file). Adding Discord: read the webhook from the same shared secrets file as a variable, never
  inline it in code, README, or notes; prefer Discord when configured and keep Telegram as
  fallback. `204 No Content` is success — check the status code, since the empty body makes
  body-sniffing report a false failure:

  ```python
  r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-m", "25",
                      "-X", "POST", WEBHOOK, "-H", "Content-Type: application/json",
                      "-d", json.dumps({"content": text[:1900], "username": "<fleet>"})],
                     capture_output=True, text=True)
  ok = r.stdout.strip() == "204"
  ```

- **Shape.** Alert on: a win, a denied review, a worker death, run completion, threshold
  crossing. **Not** per action — 24 notifications per worker per day trains the user to mute the
  channel. State the trigger list back to the user so expectations match.
- **Say out loud which alerts are noise.** With a ~1-in-91 chance and a 24-action daily budget,
  P(zero wins) ≈ 77% per identity per day, so silence is the *expected* state and only explicit
  error codes or a dead process are alarms. Tell the user this before they ask why the channel is
  quiet.

## Capital-moving automation defaults

`GC_AUTOROTATE=1` in vendor code is a live-money action on a timer. Keep it **off** until the
washer/relay wallets are funded with gas from an external source and the source worker has been
stopped; the vendor's own incident log shows a rotation that was marked "handled" before execution
while dry-run was still on, stranding ~10.5k tokens on a drained wallet and leaving the fleet
silently running 9 of 10 identities. Disabling it should still report the threshold crossing
("daily cap reached — auto-rotate disabled") rather than going quiet.

Restarting a position-carrying worker resets it to the IP-derived origin, which reads as a
teleport in the trail. Quota is server-side and survives; local walk progress does not. Do not
restart mid-run to "tidy up", and prefer an idempotent start (refuse when the slot is already
alive) so a supervisor cannot spawn duplicates.

---

## Judgment

- **If the user hands you a proven package, port it rather than continuing to hand-roll.** Two
  independent implementations of the same protocol logic is wasted effort; the vendor's version
  already carries the fixes, and a working fleet's own field notes beat another round of guessing.
- **Split a third-party review into adopt / reject explicitly.** Adopt: engineering mechanisms
  (payload shape, pacing, retry ladders, supervision discipline, balance-effect verification).
  Reject or flag: anything that moves real money by default, hardcoded vendor credentials, and
  evasion designs whose stated limitations the vendor already admits.
- **A vendor's documentation is evidence, not gospel** — but when it contradicts your own
  measurement, reconcile before acting, and record which one won and why.
