---
name: geolocation-reward-farming
description: Use when farming GPS reward-game fleets via proxies.
version: 1.0.0
author: spring
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Web3, Farming, Fleet, Geolocation, Anti-cheat, Proxy, Odds]
    related_skills: [web3-farmer-bot, watchdog-monitoring, change-monitor-watchdog]
---

# Geolocation Reward Farming (multi-wallet fleets)

Class: platforms that pay real value for **self-reported GPS trails** (walk-and-open
crates, distance rewards, geocaching drops) driven by many wallets behind proxies.
Covers the fleet-identity rules, the odds model, the gate model, and the operational
traps that a naive bot walks straight into.

Companion: `web3-farmer-bot` (user-owned) holds the SIWE/Turnstile/CryptoJS plumbing for
the individual bot. This skill is the **fleet + game-mechanics** layer on top.

## When to Use

- Farming a walk/GPS reward app with a **multi-wallet proxy fleet**.
- Deciding **where** (region) or **when** (time bucket) to spend a wallet's daily quota.
- Diagnosing a location anti-cheat reject (`suspicious_movement`, `motion_required`).
- An operator asks for a "quieter region", or for a region change on a wallet that has
  already walked — read the region rule first, it will cost a run otherwise.
- Auditing whether a published win probability is exploitable (time window vs RNG).

## Recon before scaling — four questions, each with a cheap test

Answer these with **zero funded wallets**. Rule: an unfunded wallet is a free test
harness (see "Hold-gates" below).

1. **Enumerate the API surface from the frontend bundle.**
   `grep -oE '"/v1/[A-Za-z0-9_/:.-]*"' app.js | sort -u`
   This is how the undocumented odds, history, geo and preview endpoints get found.
   UI copy leaks too: "odds change every hour with the vault" ⇒ a time-windowed odds
   endpoint exists somewhere.
2. **What is the geography of the reward grid?**
   Query the grid from two distant cities in the same bucket. Identical bucket id **and**
   identical `expiresAt` ⇒ **one global grid, one global roll**. If the preview payload
   carries no odds/rarity field, region cannot be affecting odds — stop looking there.
3. **Is there a published, time-bucketed probability?**
   `GET /v1/stats` → `commit.odds.p` (per-tier), whose sum equals the store's advertised
   `chances.free`. If it exists, read it every minute — that is the whole edge (below).
4. **What does the gate actually gate?**
   Probe each endpoint with a 0-balance wallet and record which ones pass.
   Also record whether the gate answers **before** a range/distance check when you call the
   action endpoint from far outside the allowed radius — that tells you the predicate order.

## Region identity is PERMANENT — the rule that cost a run

"Region" is not a setting; it is **which proxy the wallet is bound to**, because the runner
walks in the city returned by `GET /v1/geo` for its exit IP.

- **Choose the region before the wallet's first walk and never change it.**
- An **unwalked** wallet has no position history, so it can be placed anywhere at zero
  risk. Do ALL region assignments while slots are idle, before funding.
- Moving a wallet that has already walked is a **teleport** and trips the location
  anti-cheat on every subsequent action. Measured: 18 clean opens in Ashburn → repoint to
  Madrid (~6,000 km) → flag on the **first** open, flag again on the next target,
  **0 successes**, still rejecting after ~15 minutes of retries.

So when an operator says "move it to a quieter region":

1. Say the mechanism first, in one line: it will look like a 6,000 km teleport and the
   anti-cheat scores the *first* action after the swap.
2. If they still want it, spend it on a **fresh/unwalked wallet**, never on a live one.
3. Comply on an unwalked slot — that is safe and is the version of the request that
   actually helps.

**Also reject the premise when the data says so:** region does not move the odds. Verify,
state it once, and redirect the effort to the time window (next section). Operators often
accept the correction once they see it is not a refusal to act but a better target.

### Picking a "quiet" region objectively

Player-location data usually does not exist (a single-address lookup endpoint and a
`nearby` 404 are typical), so "quiet" is a heuristic. Measure the one thing that IS
objective — **nearest reward distance per city**, which sets how fast a wallet cycles:

```
for each candidate city: POST /v1/crates/preview {lat,lng} -> distances to nearest 5
```

One measured spread: Madrid 38 m → São Paulo 112 m → Rome 182 m → Ashburn 200 m →
Berlin 204 m → Bangkok 298 m. Combine that with a player-base heuristic (an
English-language, US-card-market game skews US-heavy) and pick the best of both.
Verify a candidate proxy by calling the **target's own** `/v1/geo` through it — not a
third-party geo API — since that is the value the runner will actually use.

## The real lever is the clock, not the map

Where the probabilities live (verified on one platform):

- Live bucket: `GET /v1/stats` → `commit.odds.p` = `{rare, grail, uncommon, common}`;
  `sum(p)` equals `store.chances.free` to full precision ⇒ it is the true per-action win
  probability, published in plaintext, identical worldwide.
- History: `GET /v1/proofs/{bucket}` → `{bucket, commit, odds}`.

Measured over 60 consecutive hours: worst **0.015%** (1 in 6,720), median 2.26%, best
**18.57%** (1 in 5.4) — a ~**1,250×** spread, top decile averaging **4.6×** the mean.
Value per open at the best bucket vs the lifetime average was roughly **19×**. Rarity
tiers move together, so a hot bucket is not just more junk commons.

⇒ **Park wallets, then spend the daily quota inside a high-probability bucket.**
Walking is free and usually needs no token, so pre-position during cold buckets.

### Verify the RNG honestly, then schedule

If the platform publishes `commit_n` for the live bucket and reveals `seed_n` later,
confirm the binding (`sha256(seed_n) == commit_n`). Once confirmed, **stop**: the roll is
not predictable. The honest play is scheduling into hot buckets, never roll prediction.
Do not present a scheduling edge as a prediction edge.

### Fetch history gently

Sweeping a few hundred `{bucket}` requests with a small thread pool got the whole IP 429'd
mid-sweep and silently truncated the result set. Fetch **sequentially at ≥1 s spacing**,
rotate proxies if needed, and treat a short result set as throttling rather than "no data".

## Hold-gates vs spend-gates

Probe with a 0-balance wallet and record what passes. Verified on one platform: login,
gate status, reward discovery and trail push **all succeeded unfunded**; only the action
endpoint answered `gate_failed`. Bonus: calling the action from ~1.2 km away (far outside
reach) still returned `gate_failed` rather than a range error ⇒ the gate is the **first**
predicate.

Two consequences:

1. **An unfunded wallet is a free harness** — you can validate auth, geography and trail
   acceptance with no capital at risk, and failing actions usually do not consume quota.
2. **A HOLD gate (not a spend) can be rotated.** One bag of the gated token can move
   wallet-to-wallet, so each wallet's quota becomes available the moment the bag lands:
   walks stay parallel, actions serialise behind the bag. Costs to state up front:
   2 transfers per wallet, a little gas in the sending wallet, and a fresh-wallet cluster
   that repeatedly receives and sheds the gate amount is a **much more legible on-chain
   pattern** than one permanently funded wallet.

## Fleet operations traps

- **Supervisors that gate on a cached eligibility file must be refreshed after funding.**
  A fleet launcher refused a freshly funded wallet (`SKIP (gate not ready)`) while the
  on-chain check on the same wallet read READY, because the launcher trusted a memo written
  before funding. Re-run the live eligibility probe, then launch.
- **Daily quota lives server-side and survives restarts and proxy swaps.** After a
  stop/repoint/restart the server reported the already-decremented count (25 − 18 = 7), so
  stopping a wallet is cheap and never re-issues spent quota. Plan against the server's
  number, not the bot's state file.
- **Check a runner's failure semantics before leaving it unattended.** Look for a fail cap:
  a loop that retries forever will hammer a persistent reject indefinitely and burn the
  day's quota on nothing. Check what its "refresh/rotate proxy" hook really does — on a
  static proxy list it is often a **no-op**, which is fine (no hidden mid-run IP rotation,
  which under the region rule would be a self-inflicted flag) but means no auto-recovery.
  **Stop a 100%-failing runner rather than letting it loop**, then re-arm deliberately.
- **Keep position continuous across runs** and never let two runners share a wallet.
  Liveness is log mtime plus a ~20 s heartbeat, not a pid file. Kill by PID — `pkill -f`
  matches your own shell command.
- Proxy/geo consistency: keep the device fingerprint, UA and walk city coherent, and align
  them with the exit IP.

## Anti-cheat error forensics

Same code, different causes, different recovery — always read the *cause*, not the code:

| code | cause | retryable? |
|---|---|---|
| `motion_required` | no motion telemetry at all | yes — fresh fix and retry |
| `suspicious_movement` | travel with no physical steps (accelerometer mismatch) | yes — ~17% of opens on a working fleet |
| `suspicious_movement` | **position discontinuity** (proxy/region changed mid-life) | **no** — does not clear on retry |

Corroborate with history: 24 clean opens on wallet A (direct IP) and 18 clean opens on
wallet B (Ashburn) vs flag-on-first-open for B in Madrid isolates the variable to the geo.

## Working with the operator

- The user wants a **verdict plus the number**, not a survey: what is the lever, how big,
  what does it cost. Lead with the measured value and the falsifier.
- **Notification-per-action**, not milestone-only, to the webhook they specify.
- When they override your evidence-backed recommendation: **comply, but pre-register the
  testable prediction** ("this should trip the anti-cheat on the first action") *before*
  acting, then report the measured outcome honestly — including when it validates your
  original read. That is how the region lesson above was actually learned, and it keeps
  the disagreement about data instead of authority.
- Stabilise before diagnosing: stop a failing loop first, then explain, then re-arm.

## Support files

- `references/gocollect-verified-2026-09.md` — full evidence: endpoints, the gate probe,
  the 60-bucket odds table, the region-swap failure timeline, the swap procedure, the proxy
  pool survey.
- `templates/time-bucket-odds-watch.py` — copy-and-adapt watcher: polls a time-bucketed
  published probability, stores one record per bucket, alerts on a threshold crossing.
