---
name: location-game-farming
description: Use when farming GPS/location games; odds + anti-cheat.
version: 1.0.0
author: spring
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Web3, Farmer, Bot, GPS, AntiCheat, Solana, Proxies, Odds]
    related_skills: [web3-farmer-bot, watchdog-monitoring]
---

# Location-Game Farming (client-asserted GPS)

Games that score a **client-reported GPS trail** against placed loot (crates, spawns,
geofenced drops). You control two independent things — the **exit IP** and the **claimed
coordinates** — and the server cross-checks both against the wallet's own history.

Use this when the target has any of: `suspicious_movement`, `short_trail`,
`motion_required`, `gate_failed`, per-hour odds, a crate/tile grid, or a token-hold gate.

> Worked example with all endpoint names and measured numbers:
> `references/gocollect-hourly-odds-and-region.md`

## Model the server before writing the bot

1. **Read the client bundle.** `grep -oE '.{300}keyword.{300}' app.js` for the exact
   payload the real client builds. Numbers in a bot's docstring are usually guesses.
2. **Rebuild the error ladder and the CHECK ORDER.** Which predicate fires first — gate,
   distance, trail freshness, anti-cheat? This decides what you can test for free.
3. **Find the win probability and ask whether it varies by TIME or PLACE.** It is usually
   published, and it is usually the whole game (see R3).
4. **Measure the tolerances** with a throwaway, unfunded wallet — the cheapest harness
   you will ever have (see R4).

## Golden rules

**R1 — A wallet's region is chosen BEFORE its first walk and never changed.**
Region == which proxy a slot is bound to, because the runner walks in the city its exit IP
resolves to (`GET /v1/geo`). Repointing a wallet with movement history creates a position
discontinuity (thousands of km between two sessions) that the server scores as a teleport.
Observed: it did **not** clear on IP revert and did **not** clear in 5 minutes; every
subsequent open on that wallet was rejected until it cooled down. A **fresh, never-walked
wallet placed in the new region opened cleanly on its first try.** Corollary: region
changes are safe on *idle* slots and unsafe on *lived* ones — so re-point every idle slot
before you fund it, and never repoint a slot whose runner is alive.

**R2 — Exit-IP geo and claimed GPS must agree.** Derive your walk coordinates from the
proxy's own geo, not from a hardcoded city. A claimed city 1,000 km from the exit IP is a
standing red flag even when the trail itself is perfect.

**R3 — The lever is usually WHEN, not WHERE.** Do not accept "play in a quiet region for
better luck" without measuring. Placing the loot grid is global and time-driven far more
often than it is regional. On the worked example: crates in four different countries shared
an **identical round id and identical `expiresAt`** (one global grid, one global roll), and
the public stats endpoint published the per-open win probability **per hour** — spread over
60 hours was **0.015% → 18.57% (≈1,248×)**, with the top-decile hours averaging **4.6×**
the mean and ~$9.7/open vs a $0.50 lifetime average on identical in-game actions. Region
still matters for *competition* (how likely someone else takes the target first), never for
the roll. Pick regions for *availability*, and pick the **hour** for odds.

**R4 — Use the gate's check order as a free test harness.** On the worked example the
hold-token gate sat **before** the distance check (an open issued 1.2 km away returned
`gate_failed`, never a range error), so an unfunded wallet could log in, read the gate,
discover loot, push a full trail — everything except the open. That means: you can warm,
position and pre-walk every wallet with **zero capital**, and the capital is only needed at
the instant of the open. If the gate is a **hold** (not a spend), one bag can be rotated
wallet-to-wallet, turning "N × threshold" exposure into "threshold in flight". Costs:
opens serialize behind the bag, 2 transfers per wallet, and a visible on-chain cluster.

**R5 — Cap your retries; guard the runner.** Many runners retry a rejected action forever
with no fail cap, which silently burns quota, requests and time. Ship a guard that tails the
slot log and hard-kills the runner on the first anti-cheat rejection:
`scripts/anticheat_guard.py`. Decide first whether the flag is *transient* (retry is right)
or a *history contradiction* (retry is useless — see R1).

**R6 — Stopping a bot is two steps, and the supervisor dies FIRST.** A watchdog-enabled
watcher will resurrect a runner you just killed (it typically relaunches with default flags
and a cached gate memo). Kill the watchdog, then the runner:
`screen -S <watch> -X quit` → `systemctl --user stop <unit>` → verify with `screen -ls`,
a PID-exact process listing, the unit list, and the cron list. **Tell-tale that a watchdog,
not a human, restarted it:** the runner command shows the *default* flags (e.g. default
min-gap) rather than your tuned ones.

**R7 — Never trust a cached gate/precheck memo.** A launcher that gates on a cached
precheck file will refuse to start a wallet funded *after* that cache was written, and will
report "gate not ready" while the on-chain balance plainly says otherwise. Re-run the
precheck after every funding event, then start.

**R8 — Liveness is log mtime + heartbeat, not a pid file; kill by exact PID.** `pkill -f`
and `pgrep -f <pattern>` match **your own shell wrapper** — a pattern kill loop can kill the
shell running it. List processes, then kill explicit PIDs.

**R9 — Rate-limit your own probing.** Bursting a few hundred requests (e.g. 12 workers over
a history endpoint) earns a 429 and poisons the next few minutes of measurement. Fetch
sequentially, ≥1 s apart, spread across a few pooled proxies; back off on 429.

**R10 — Persist position across runs** (lat/lng in the state file) or the first fix after
every restart is a jump — the same failure class as R1, just smaller.

**R11 — Supervise always-on components with systemd, not `screen`.** Two `screen` sessions
died silently with **no traceback, no OOM and no reboot**, and the per-open notifications
simply stopped without anyone noticing until asked. Move notifiers and guards to systemd
**user** services with `Restart=always` + `RestartSec=15`, and use a **template unit** so
per-slot instances need no new files:

```ini
# ~/.config/systemd/user/<name>@.service
[Service]
WorkingDirectory=<project>
ExecStart=/usr/bin/python3 -u <project>/guard.py --slot %i --timeout 86400
Restart=always
RestartSec=15
StandardOutput=append:<project>/logs/guard_stdout.log
StandardError=append:<project>/logs/guard_stdout.log
[Install]
WantedBy=default.target
```

```bash
loginctl enable-linger "$USER"          # survive logout
systemctl --user daemon-reload
systemctl --user enable --now guard@3.service
systemctl --user is-active guard@3; systemctl --user is-enabled guard@3
```

R6's stop ordering (supervisor first, then runner) still applies — it just becomes
`systemctl --user stop <supervisor>` instead of `screen -X quit`.

**R12 — Never convert a short odds history into a fixed clock-hour schedule.** If you
average per-period odds by hour-of-day you will *always* find a "best hour" — with a couple
of days of data each bucket holds ~3 samples, so it is noise dressed as a pattern. On the
worked example the whole ≥5% spike came from a **single day**, and the same clock hour was
**20× different** (18.57% vs 0.90%) on the next day; the level drifts per *day* (stock-like,
smooth within a day), not per hour. Report the finding as "the level moves and must be
reacted to", not "open at 09:00". Also weigh the real cost of waiting: **unused daily quota
is forfeited**, so parking is not free.

**R13 — Audit who actually pays before assuming you need gas.** Pull recent winners from the
public stats feed and check the fee payer and native-balance delta of their delivery
transactions. On the worked example the **operator's treasury** paid the fee *and* created
the token account — the winner's native delta was `+0.000000`, so winning and receiving cost
the user **zero**; only cashing out to stable was gas-spending (~0.00008 SOL/tx, verified
against a real winner who received USDC +19.63). Payouts also often settle in **USDC, not the
native token** — auditing the native balance concludes "nothing arrived" while the money is
there.

**R14 — Operator conventions that remove back-and-forth.** Notifications are **always on** —
per action *and* per loot/claim event — and that default should never be asked about again:
wire the notifier before the runner, every time. When the user says a wallet is already funded
("udh gua topup"), skip the balance sweep, but **still run the launcher's mandatory precheck**:
it is a launcher requirement (R7), not a balance check — report its result as a *gate*
confirmation, never as funding verification. When they say the last wallet hit its daily cap,
that is the cue to onboard the next one, not to re-audit the finished one.

## Rule: the object-round clock is not competition

Loot ids carried a round component that advanced every **15 minutes** (4 rounds/hour). So
"my target vanished mid-walk" is usually a **round rollover**, not another player taking it —
and one good odds-hour contains four fresh grids. Check the round cadence before concluding
someone is racing you, and before assuming a region is "too busy".

## Procedure: onboard a new wallet/slot

1. Drop the key in a file, `chmod 600`, and confirm the file holds only keys (`awk` line
   count + length + a 5-char prefix — never echo secrets).
2. **Choose the region while the wallet is still idle** (R1) → see the next section.
3. Import the key bound to the chosen proxy, then **refresh the precheck** (R7) and confirm
   `gate=OK` plus the expected city from the server's own geo endpoint.
4. Arm the guard (R5), then start the runner with your tuned flags (not defaults).
5. Verify from the log, not from intent: proxy line, `[me]` gate/opensLeft, `[geo]` city,
   and the **first successful open**. Then leave it alone.

## Procedure: choose a region by measurement, not vibes

1. Geo-locate the whole proxy pool once and cache it (`ip-api.com/json/<ip>` per IP).
   **Normalize accents before matching**: a provider returns `São Paulo` while the game's
   geo endpoint returns `Sao Paulo` — unmatched, your quietest candidates silently vanish.
2. Rank cities by how thin the player base plausibly is for that game. For an
   English/US-card-centric game the measured ordering that worked: Bangkok > Rome >
   São Paulo > Madrid > Paris/Berlin > UK/Toronto > US datacenter.
3. For the top city, hit the game's own geo endpoint through **each** proxy to get real
   latency, then pull the loot-preview endpoint to get **count + nearest-target distance**.
   Nearest-target distance is the metric that matters operationally — it sets cycle time.
4. Bind the winner to the slot, precheck, start. Never reuse an IP that was already
   implicated in a flag if a fresh equivalent exists.

## Procedure: snipe the good odds

1. Poll the public stats/probability endpoint once a minute from a supervised loop; log one
   record per period (dedupe by period id) → `scripts/location_odds_probe.py`.
2. Alert only on a **new** period crossing a threshold (with per-tier breakdown and the
   best periods seen so far) so the alert stays meaningful.
3. Keep wallets pre-walked and unfunded-or-idle (R4) so the whole day's quota can be spent
   inside the good window; walking is free, opening is not.
4. Sanity-check whether randomness is predictable before dreaming bigger: if it is
   commit-reveal, verify the commitment (`sha256(revealed_seed) == published_commit`) and
   confirm the seed is disclosed **after** the period. If so, timing is the only edge —
   do not waste time grinding the roll.

## Verification checklist

- [ ] Server's own geo endpoint confirms the intended city for each slot
- [ ] First open succeeds with **zero** anti-cheat codes before you scale
- [ ] Guard is armed and proven to fire (check its log, not just its screen)
- [ ] Daily quota untouched by failed attempts (log the counter before/after)
- [ ] Odds/period logged, and the alert threshold justified by measured history
- [ ] Win delivery confirmed through the product's **own** API (its wallet/pull endpoint is
      authoritative for delivered-vs-removed) rather than a chain-level DAS/token call, and
      write down the recorded value so a later cashout can be reconciled
- [ ] Stopping is verified across screens, PIDs, units and cron — not just one of them

## Pitfalls

- **Concluding "the wallet is burned" or "the wallet is fine" from one attempt.** Transient
  vs history-contradiction flags look identical for the first attempt.
- **Assuming a proxy pool is rotating because a session died.** Verify by requesting the
  exit IP several times in a row; a stable IP rules rotation out and saves a wrong rewrite.
- **Believing a friendly claim (region/off-hours/"my friend says") without measuring.** Both
  the odds claim and the flag claim in the worked example were resolved by measurement, and
  one of them was right for the wrong reason.
- **Treating wallet-replacing as free.** Rotating a wallet in a slot overwrites the keyfile;
  the old funded wallet keeps its own state (balance, remaining daily quota, flag) and needs
  its own cooldown before reuse.
- **Assuming a runner's proxy-refresh will save you.** Read it: on a *static* proxy argument
  the refresh path is a no-op (it only rotates when the runner was given a rotating-proxy API
  URL), so a stuck runner keeps hammering the same exit IP forever. That is what the guard
  (R5) exists for.
- **Trusting a restart you did not command.** A watchdog restarting a slot will use the
  runner's **default** flags and its cached gate memo, silently overriding your tuned
  min-gap. Diff the running command against what you started before assuming your settings
  are live.
- **Concluding "no player competition" OR "heavy competition" without checking the round
  clock.** Both look like a target disappearing; the 15-minute rollover explains most of it.
- **Reporting a heartbeat as activity.** A runner producing blocks/heartbeats with zero
  user-level counters is not "working" — check the actual quota/claim counters before
  telling the user the fleet is producing.

## Support files

- `references/gocollect-hourly-odds-and-region.md` — full worked example: endpoint map,
  measured odds history, the region-change flag timeline, region-selection data.
- `scripts/anticheat_guard.py` — log-tailing guard that kills a runner on the first flag.
- `scripts/location_odds_probe.py` — per-period odds/rate poller with change-only alerts.
