# Money rail, win verification, and long-lived ops

Session-verified detail for the geolocation-farming class. Companion to
`references/gocollect-verified-2026-09.md` (endpoints, odds table, region-swap timeline).

---

## 1. Who pays at each stage (audited on-chain, four real winners)

Winning is not the end of the pipeline. **Delivery and cash-out are separate stages with
different payers.** Operators budget for the wrong thing unless you say the payer out loud.

### Audit method — two reads per winner

1. Take the recent-winner list from the public stats endpoint (`/v1/stats` → `recent[]`,
   each entry carries the full winner `profile` address and the `mint`).
2. Per winner: `getSignaturesForAddress(address, {limit: ~15})`, then `getTransaction` for
   each. From each transaction read:
   - **fee payer** = `transaction.message.accountKeys[0].pubkey`
   - **the winner's own SOL delta** = `postBalances[i] - preBalances[i]` at the winner's index
   - which programs were invoked (ATA program, marketplace program, treasury presence)
3. Count, per winner: txs the *winner* paid for vs txs the *operator* paid for.

Run it as `scripts/audit_prize_fees.py` — do not hand-type this per session.

### Measured result

| stage | who pays | evidence |
|---|---|---|
| the action itself (crate open) | **nobody** | gate is a token **hold**, a balance check, and it fires before the range check |
| prize delivered to the wallet | **the operator's treasury** | `feePayer == treasury`; winner's SOL delta **`+0.000000`**; the treasury's tx also invoked the ATA program, i.e. the operator paid the new asset's rent |
| cashing the prize out | **the winner** | client-signed (`…/prizes/{id}/cashout` → `…/cashouts/{id}/sent {signedTx}`); observed **0.000005–0.000145 SOL** per tx |
| physical redemption | shipping only | UI copy: "redeem the real card and have it shipped" |

Cross-check on a real cash-out: one winner received **USDC +19.63** and paid **0.000081 SOL**
as fee payer — so the payout arrived in USDC and the winner's gas was dust.

### What this means for the economics

- **"Hold the token, not gas."** The farming loop needs **no** native gas at all. A dust
  float (~10⁻⁴) covers hundreds of cash-outs, so gas is not a constraint and must not be
  presented as one.
- Because the gate is a **hold**, the stake is **recoverable**: a slot's real cost is
  *price exposure on the held token* + *the platform payout fee*, not a sunk spend.
- **Check the payout asset, not the native balance.** A `getBalance` audit reports "nothing
  arrived" while the money is actually there — payouts land in a stablecoin. Audit the
  stablecoin mint, and expect the payout to be **net of a platform fee** (~2% measured).
- Cards are typically **MPL Core**-style assets; "sold" vs "listed" vs "held" is
  distinguishable from the marketplace instruction invoked (`ListCore` = still yours,
  `BuyCore`/`BuyPnft` = sold, treasury inventory receives the sold ones).

---

## 2. Verify a win end-to-end — and prefer the game's own API over raw RPC

A win is **not** confirmed by the runner's log line, and not by a `getAsset` call either.

Order of checks, cheapest first:

1. **Runner's own profile call** → `review={"checking":N,"denied":[]}`.
   Non-empty `denied` is a **hard stop** — halt the runner (the prize went back to stock).
   `checking>0` means still under review; a win can be adjudicated minutes after it lands.
2. **`GET /v1/players/{address}`** → `stats.cardsPulled`, `badges` (e.g. `first_pull`,
   `og_launch`), and the pull record with its `cashedOut` flag and `valueUsd`.
3. **`GET /v1/players/{address}/wallet`** → `stillHeld: [mint]` — this is the proof the asset
   actually reached the wallet. Also returns `listed` and `cards`.
4. `GET /v1/cards/{mint}` → `history: [{kind:"pulled", day, who}]` — attribution.

**Prefer 2–4 over raw RPC.** A hosted RPC's DAS endpoint (`getAsset`) returned **503**, while
the game's own wallet endpoint answered instantly and is authoritative about its own
definition of "held". Fighting RPC costs time and proves less than asking the platform.

Worked example of a first win (single card, ~1.2% hit rate over ~80 opens — dead on the
game's own published lifetime average of 1.278%, i.e. no bug, just odds):

```
[open 7/24] <crateId> -> ★ common (pity=0, u=0.009)
[★ CARD] {"tier":"common","u":0.008731576005942099,"hour":497343,
          "item":{"name":"... Mega Charizard Y EX CGC 9 ...","grade":"CGC MINT 9",
                  "insuredValueUsd":15},"prizeId":4787,"openId":253613}
review={"checking":0,"denied":[]}          -> not denied
stillHeld:["HXjTuK1j..."]                  -> delivered, cashedOut:false
```

Note `u = 0.0087` against a `< 0.011` band: the win band is narrow, so "close calls"
(`u ≈ 0.013`, `0.054`) are normal and are **not** evidence of a near-miss bug.

---

## 3. Long-lived ops: a service manager, not `screen`

**Observed failure:** two `screen`-hosted processes (a per-action notifier and an
anti-cheat guard) both disappeared silently — no traceback, no OOM in `dmesg`, no reboot
(uptime 26 days), empty stdout. Nothing detected it for ~19 minutes; the runner kept going
unprotected. `screen` is fine for a live debug session and unfit for the thing that must be
running unattended.

**Fix — `systemd --user` units with `Restart=always`:**

```ini
# ~/.config/systemd/user/<proj>-notify.service
[Unit]
Description=<proj> notifier
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/root/<proj>
Environment=NOTIFY_WATCHDOG=0
ExecStart=/usr/bin/python3 -u /root/<proj>/watch.py
Restart=always
RestartSec=15
StandardOutput=append:/root/<proj>/logs/watch_stdout.log
StandardError=append:/root/<proj>/logs/watch_stdout.log

[Install]
WantedBy=default.target
```

- `loginctl enable-linger <user>` so the user manager survives logout/reboot.
- `systemctl --user daemon-reload && systemctl --user enable --now <unit>`.
- Verify with `systemctl --user is-active` **and** `is-enabled` **and** a PID listing — the
  same "verify across every layer" discipline as stopping.

**Template units make per-slot onboarding a one-liner.** Use `<proj>-guard@.service` with
`ExecStart=… guard.py --slot %i …`; then a new slot is
`systemctl --user enable --now <proj>-guard@4`. Avoids a bespoke unit file per slot.

**Guard and auto-restart watchdog must not both be armed.** A watchdog-enabled watcher will
resurrect the runner the guard just killed for an anti-cheat flag — straight back into the
same rejection, burning quota for nothing. Choose:
- **guard ON + watchdog OFF** (notify-only watcher) — correct when the failure is a *history
  contradiction* that retry cannot fix;
- **watchdog ON, no guard** — only for crashes/network deaths with no anti-cheat component.
Verify which is live by reading the **flags in the actual process command line**, not the
launcher script — a watchdog restart shows *default* flags where you tuned yours.

---

## 4. The odds data is a REGIME, not a timetable

The same 60-bucket history, re-cut per calendar day (local WIB, UTC+7), destroys the naive
"best hours" reading:

```
             0    1    2    3    4    5    6    7    8    9   10   11   12   13   14   15   16   17   18   19   20   21   22   23
Thu      .    .    .    .  2.26 2.26 2.28 2.28 2.28 2.28 2.28 2.28 2.28 2.28 2.28 2.28 2.28 2.28 2.28 2.28 2.28 2.28 0.01 0.01
Fri     0.01 0.01  .    .   0.01 0.01 0.01 15.8 15.8 18.6 18.2 14.9 10.4 7.56 9.50 7.89 5.71 4.40 3.26 2.20 2.30 1.95 2.15 1.70
Sat     1.64 1.43 1.16 1.06 0.63 0.70 0.68 0.63 0.79 0.90 1.28 1.36 1.10 0.97 0.99 1.10 1.28 1.01 0.94   .    .    .    .    .
```

- Every `≥5%` bucket sits on **Friday** only. Hour 09 local: **18.57%** on Friday vs
  **0.90%** on Saturday — a **20×** same-hour difference.
- The level drifts on a **multi-day** scale (flat 2.28 → collapse to 0.01 → an 18% event →
  settle 0.6–1.6). Averaging across days therefore invents a "golden morning" that is really
  one day's event smeared over the table.
- The shape *within* the event day builds and decays smoothly over ~6–10 hours — consistent
  with vault stock being drained/restocked, **not** with a clock.
- Plateable hypothesis to pre-register rather than assert: if the spike is a weekly
  restock/promo, it should reappear at roughly the same local window next week. Test it;
  do not schedule against it.

**Parking has a price.** Daily quota normally resets and does **not** roll over, so compare
in plain numbers: always-on (quota × current p × expected prize) vs. holding for a spike
(spike p × expected prize × observed spike frequency). With 2–3 days of history, label the
conclusion **indicative**. The trigger should be the **live published bucket**, polled, with
a threshold alert — never a hardcoded hour.

---

## 5. Misc measured facts worth keeping

- **The reward grid rolls on a fixed sub-hour cadence** (observed 15 min: `expiresAt` moved
  900000 ms and the bucket/round id incremented). Consequence: a target that "vanishes
  mid-walk" is usually a **rollover**, not a competitor taking it — and one hot odds window
  contains several fresh grids to farm.
- **Wallet rotation overwrites the keyfile** (`import --force`). The displaced wallet keeps
  its own balance, remaining daily quota and flag state, and needs its own cooldown before
  reuse. Replacing a wallet is not a reset of the *account's* history.
- **Proxy pools can look rotating but are not.** Verify by requesting the exit IP several
  times in a row before rewriting anything — a stable IP rules that theory out.
- **Onboarding sequence that worked** (repeat per slot): `chmod 600` the key file → pick the
  region **while idle** → import bound to that proxy → refresh the live eligibility probe →
  arm the guard → start with tuned flags → verify proxy line, `[me]` gate/quota, `[geo]` city,
  and the **first successful action** in the log before walking away.
