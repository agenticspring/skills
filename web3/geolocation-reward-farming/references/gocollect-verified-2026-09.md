# GoCollect-class platform — verified evidence (2026-09)

Platform: `gocollect.fun` (Solana, SIWS auth, client-asserted GPS trail, real graded
Pokémon cards as prizes, paid out via Collector Crypt). Everything below was measured
against the live API, not inferred from a bot's docstring.

## Endpoint map

Discovered by grepping the frontend bundle:
`grep -oE '"/v1/[A-Za-z0-9_/:.-]*"' app.js | sort -u`

| endpoint | auth | what it gives |
|---|---|---|
| `POST /v1/auth/challenge` + `POST /v1/auth/wallet` | none | SIWS login → bearer token |
| `GET /v1/me` | bearer | `opensLeft`, `metersWalked`, `gate{required,ok,min}`, `review{checking,denied[]}`, `xp/level/shards/pity` |
| `GET /v1/geo` | none | geo of the **calling exit IP** → `{lat,lng,city}`; the runner walks here |
| `POST /v1/crates` | bearer | rewards near a lat/lng + a `commit` |
| `POST /v1/crates/preview?lat&lng` | none | pure geometry: `{id,lat,lng,expiresAt}` — **no odds field** |
| `POST /v1/crates/{id}/open` | bearer | the gated action; returns `pity`, `u`, tier |
| `POST /v1/fixes` | bearer | trail push (throttled ~1 fix/s) |
| `GET /v1/stats` | none | global counters, `inventory`, `recent`/`topPulls`, `funds`, **`commit.odds`**, `lastReveal` |
| `GET /v1/proofs/{hour}` | none | `{hour, commit, odds}` for a past hour |
| `GET /v1/store` | none | `chances.gold`, `chances.free`, product SKUs |
| `GET /v1/draw` | none | weekly paid raffle state |
| `GET /v1/players/{address}` | none | single-player lookup (there is **no** nearby-players endpoint) |

`/v1/players/nearby`, `/v1/players?lat=..`, `/v1/stats?lat=..` → 404 / ignored coords.

## The gate: unfunded wallet as a free harness

Throwaway wallet, zero balance, over a free pool proxy, Jakarta coords:

```
[Q1] POST /v1/auth/challenge       -> 200
[Q1] POST /v1/auth/wallet (SIWS)   -> 200  token=yes
[Q2] GET  /v1/me                   -> 200  gate={"required":true,"ok":false,"min":10000}  opensLeft=25
[Q3] POST /v1/crates               -> 200  crates=17  commit=yes
[Q4] POST /v1/fixes (20 fixes)     -> 200  accepted=20
[Q5] POST /open (1,261 m away)     -> 403 gate_failed
     "Hold at least 10,000 $COLLECT in this wallet to open crates."
```

Conclusions: login / gate read / reward discovery / trail push all work at 0 balance; only
`/open` is gated. The gate is evaluated **before** the distance check (a 1,261 m call still
returned `gate_failed`, never a range error). The gate is a **hold** (not a spend) and the
read is effectively live — `gate.ok` flipped from false to true minutes after funding.

Mint: `nDZknLvfFRp5rgUHdzTrQsmSY5NKzoavqdLjSHVpump`.

## Odds are per-HOUR and published in plaintext

`GET /v1/stats` → `commit`:

```json
{"hour": 497339,
 "commit": "9d2f44e7…",
 "oddsHash": "36468434…",
 "odds": {"p": {"rare": 0.0008487109676985646,
                "grail": 0.00010083694665725522,
                "common": 0.005335955093946422,
                "uncommon": 0.00315955766192733}}}
```

`sum(odds.p)` = `0.009445060670229571` = `store.chances.free` exactly (16 digits).
`chances.gold` = `0.05892` = the store copy "About 1 in 17 holds a graded card"
(1/0.05892 = 16.97). So these are the true per-crate win probabilities.

### 60-hour distribution (from `/v1/proofs/{hour}`)

| | total free-crate odds | 1 in |
|---|---|---|
| best (hour 497306) | **18.5722%** | 5.4 |
| mean | 3.369% | 30 |
| median | 2.262% | 44 |
| worst (several hours) | **0.0149%** | 6,720 |

- spread max/min ≈ **1,248×**; stdev 4.576% (heavy-tailed — a fixed schedule loses)
- top 10% of hours average **15.63%** vs 3.37% mean = **4.64×**
- hours ≥10%: 10% of hours; ≥15%: 6.7%
- tiers move together: best hour had `grail` 0.5843% vs 0.0101% in hour 497339 (**58×**
  on the $365–600 tier)
- movement is a smooth drift, often holding a value for a run of hours (2.2768 × 10)
- current hour at the time of measurement: **0.9445%** (1 in 106) — below median

### Commit-reveal is sound

`sha256(lastReveal.seed for hour 497338)` = `7bf167f71b81c1522a87aa5159caff6a…`, which is
exactly `/v1/proofs/497338` → `.commit`. So `commit_n = sha256(seed_n)` and the seed is
revealed only **after** hour n ends ⇒ the roll cannot be predicted. Optimise the clock,
not the RNG. (`oddsHash` did not reproduce from any of 7 plausible serialisations of the
odds object — the odds value itself is published in the clear, so this did not matter.)

### Value per open

Tier probabilities in the 18.57% hour × rough tier values (from `inventory` + `recent` +
`topPulls`): common 12.627% × ~$15 = $1.89, uncommon 3.557% × ~$50 = $1.78,
rare 1.804% × ~$190 = $3.43, grail 0.5843% × ~$450 = $2.63 → **≈ $9.7/open**.
Lifetime average from the same endpoint: `valueOutUsd 111,921 / 223,268 opens` = **$0.50/open**,
win rate 2,854/223,268 = **1.278%** (1 in 78). Ratio ≈ **19×**.

## Region has NO effect on the odds

- `/v1/crates/preview` returns only `{id, lat, lng, expiresAt}` — no odds anywhere.
- Crates in Ashburn (US), Jakarta (ID), Chojnice (PL) and Reykjavik (IS) all carried the
  **same round id** (`:1989357`) and the **same `expiresAt`** (`1790422500000`) ⇒ one global
  grid, one global hourly roll.
- Crate density in the preview radius did vary (Reykjavik 23, Jakarta 17, Ashburn 13,
  Bangkok 18, Berlin 18, Rome 19, Madrid 21, São Paulo 24) — a geometry artefact, not odds.

**Rounds roll every 15 minutes**: `expiresAt` advanced `1790422500000 → 1790423400000`
(900,000 ms) and the id went `:1989357 → :1989358`. So the grid regenerates 4× per hour,
independently of the hourly odds. A "target vanished mid-walk" is most likely a round
rollover, not another player — which also means competition is largely a non-issue.

### Nearest-crate distance per city (one round snapshot)

| city | crates | nearest | next four |
|---|---|---|---|
| Madrid ES | 21 | **38 m** | 189 / 246 / 277 / 419 |
| São Paulo BR | 24 | 112 m | 220 / 391 / 420 / 481 |
| Rome IT | 19 | 182 m | 354 / 462 / 488 / 585 |
| Ashburn US | 23 | 200 m | 253 / 386 / 419 / 465 |
| Berlin DE | 18 | 204 m | 400 / 411 / 414 / 578 |
| Bangkok TH | 18 | 298 m | 399 / 672 / 701 / 727 |

## The region swap that failed (the key lesson)

Timeline for one wallet with 18 successful opens in Ashburn:

```
18:37:31  [open 18/24] 892aaa84603ffff:1989358     <- last Ashburn open, OK
          stop → repoint 45.3.38.134 (Ashburn) -> <PROXY_IP_REDACTED> (Madrid) → start
18:39:56  [proxy] http://***@<PROXY_IP_REDACTED>:3129
18:39:56  [geo] Madrid 40.42,-3.7   [me] opensLeft=7  gate.ok=true
18:44:18  [open err] suspicious_movement  POST /v1/crates/89390cb1b17ffff:1989358/open -> 403
18:44:18  [loop err 1] suspicious_movement … — retry
~18:52    [open err] suspicious_movement  (2nd crate) -> [loop err 2]
```

Result: **0 opens in Madrid, 2 rejections**, still failing after ~15 min. Cause: a ~6,000 km
position discontinuity (39.04,-77.49 → 40.42,-3.70) between two sessions minutes apart.
Isolating evidence: 24 clean opens on a different wallet run direct from the VPS IP
(Chojnice PL), 18 clean opens on this wallet in Ashburn, flag on the **first** open in
Madrid — the geo was the only variable.

### Swap procedure (only valid for an UNWALKED slot)

```
./fleet.py stop --slots N
PX=$(sed -n '<line>p' proxies.txt)                      # host:port:user:pass
python3 mkfleet.py import --slot N --key keys/GN.key --proxy "$PX" --force
./fleet.py precheck --slots N                           # MUST refresh the cached probe
./fleet.py start --slots N --max 24 --min-gap 320
```

The supervisor refuses to repoint a slot whose runner is alive (correct guard — a
deliberate stop+repoint defeats it and pays the flag).

After the restart the server reported `opensLeft=7` (= 25 − 18), i.e. the daily ledger is
server-side and survives the swap.

## Fleet ops traps hit this session

- `fleet.py start` gates on a **cached** `precheck.json`, not the live balance:
  `slot 2: SKIP (gate not ready — no 10k $COLLECT yet)` while `balances` said
  `10,005 $COLLECT · READY`. Re-run `precheck` after funding, then `start`.
- The runner has **no fail cap**: on a persistent reject it retries forever `[loop err n]`
  and never advances — stop it rather than letting it burn the quota.
- `refreshProxy()` (fires after 4 consecutive failures) is a **no-op** unless `--proxy-url`
  is set, so with a static `--proxy host:port:user:pass` there is no hidden mid-run IP
  rotation (which under the region rule would be a self-inflicted flag).
- Sweeping `/v1/proofs/{hour}` with a 12-worker pool 429'd the IP and silently truncated the
  result to 62 rows. Sequential at ≥1 s spacing worked.

## Proxy pool survey (100 entries, datacenter)

Geo-located by hitting `ip-api.com/json/{ip}` per proxy (do NOT geo-locate the proxy by
routing through it if the target's own `/v1/geo` is available — use that instead).

| city | count | | city | count |
|---|---|---|---|---|
| Ashburn US | 53 | | São Paulo BR | 7 |
| Berlin DE | 11 | | Madrid ES | 3 |
| Toronto CA | 9 | | Bangkok TH | 2 |
| City of London UK | 8 | | Rome IT | 1 |
| Paris FR | 7 | | | |

Datacenter exits were **not** punished on the first run — 18 opens through one completed
with zero rejections. Connectivity verified through each proxy by
`GET https://gocollect.fun/v1/geo` (~390–460 ms round trip; a proxied walk converges
~2× slower in wall-clock than direct, ~0.7 m/s vs ~1.3 m/s effective, because the server
throttles at ~1 fix/s and each batch pays proxy latency).

## Watcher

`odds_watch.py` in the fleet dir: polls `/v1/stats` every 60 s, appends one record per hour
to `odds_hourly.jsonl`, and fires a Discord alert when a new hour crosses
`GC_ODDS_THRESHOLD` (default 5% = top ~17% of hours). Runs detached in `screen`.
See `templates/time-bucket-odds-watch.py` for the generic version.
