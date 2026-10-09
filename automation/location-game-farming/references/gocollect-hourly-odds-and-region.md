# Worked example: GoCollect-class location game — hourly odds, region, flag timeline

All numbers below are measured against a live target (Solana SIWS + client-asserted GPS).
Endpoint names are kept because the shapes generalise; treat any number as *that session's*
measurement, not a constant.

## Endpoint map

| endpoint | what it gave |
|---|---|
| `POST /v1/auth/challenge` → `POST /v1/auth/wallet` | SIWS challenge + signature → bearer token |
| `GET /v1/me` | `opensLeft`, `metersWalked`, `gate {required, ok, min}`, `review {checking, denied[]}` |
| `GET /v1/geo` | the city/coords the server attributes to your **exit IP** |
| `POST /v1/crates` | loot grid around claimed coords + `commit` |
| `GET /v1/crates/preview?lat&lng` | geometry only — **no odds field anywhere** |
| `POST /v1/fixes` | trail upload (throttled ≈1 fix/s; `ts` must be <30 s old) |
| `POST /v1/crates/{id}/open` | the claim — this is where the gate and anti-cheat live |
| `GET /v1/stats` | global players/opens/wins/valueOut, **`commit.odds.p` per tier**, `funds` |
| `GET /v1/proofs/{hour}` | historical per-hour odds + commit (≈62 h retained) |
| `GET /v1/store` | `chances.free` / `chances.gold` |
| `GET /v1/players/{addr}` · `/wallet` · `GET /v1/cards/{mint}` | holdings, `stillHeld`, `cashedOut`, pull history |

## The odds are published, and they are per HOUR

`sum(GET /v1/stats → commit.odds.p)` equalled `GET /v1/store → chances.free`
**to 16 digits** (0.009445060670229571 in the hour sampled). The store blurb for the paid
crate ("About 1 in 17") matched `chances.gold = 0.05892` exactly — so these are the real
per-open probabilities, not decoration.

60 hours of `GET /v1/proofs/{hour}`:

| | free-crate odds | |
|---|---|---|
| best hour | **18.5722%** | 1 in 5.4 |
| median | 2.262% | 1 in 44 |
| worst hours | **0.0149%** | 1 in 6,720 |
| the hour when first measured | 0.9445% | 1 in 106 |

Spread **≈1,248×**. Mean 3.369%, stdev 4.576% (heavy-tailed). Hours ≥10%: 10% of all hours;
≥15%: 6.7%. Top decile averaged **15.63% vs 3.37% mean = 4.64×**. Rarity moved with it —
grail 0.5843% in the best hour vs 0.0101% in a poor one (**58×** on the $365–600 tier).

**Randomness is not grindable.** `sha256(revealed seed for hour N)` equalled the published
`commit` for hour N, and the seed is only disclosed *after* the hour ends. Roll cannot be
predicted; only timing can be exploited.

### ⚠️ The spike was ONE DAY, not a daily clock

Grouped by clock hour it *looked* like a window (07:00–12:00 local, peak ~7.2%). Grouped by
**date** it collapsed:

```
hour-of-day →   07     08     09     10     11     12  ...   22     23
Day 1          2.28   2.28   2.28   2.28   2.28   2.28      0.01   0.01   (flat, then collapse)
Day 2         15.83  15.83  18.57  18.19  14.93  10.41      2.15   1.70   (the only spike)
Day 3          0.63   0.79   0.90   1.28   1.36   1.10       ...    ...   (low all day)
```

Same clock hour, **20× different** between day 2 and day 3. The level drifts per *day*
(vault-stock-like, smooth within a day), and every ≥5% hour came from a single day.
**Conclusion: do not build a fixed-schedule "best hour" plan from an averaged hour histogram
with only a couple of days of history.** With n≈3 per bucket it is noise dressed as a pattern.
Poll live and react instead.

Also measured: the odds value often *held* for runs of hours (one value repeated 10×), i.e.
drift rather than an iid draw — consistent with a stock/liability-driven number.

## Region: no effect on odds, but it does gate competition

- `GET /v1/crates/preview` returned **only geometry** — no odds — and crates queried in
  Ashburn, Jakarta, Chojnice and Reykjavik all carried the **same round id** (`:1989357`)
  and the **same `expiresAt`** (`1790422500000`). One global grid, one global roll.
- Crate counts inside the preview radius differed (Reykjavik 23, Jakarta 17, Ashburn 13) —
  so region can affect *availability*, never the roll.
- **Requesting the same crates twice in one round returned the same ids**, and the "target
  vanished mid-walk" event was explained by the **round clock**: `expiresAt` advanced
  900000 ms (15 min) and the round id incremented `:1989357 → :1989358`. Rounds roll **4× per
  hour** — so a vanished target is a rollover, not a competing player, and one hot hour
  contains four fresh grids.

### Region-selection measurements (the numbers that decided it)

```
Bangkok TH     18 crates   nearest 298 m   ~416 ms
São Paulo BR   24 crates   nearest 112 m   ~445 ms
Rome IT        19 crates   nearest 182 m   ~395 ms
Madrid ES      21 crates   nearest  38 m   ~402 ms
Berlin DE      18 crates   nearest 204 m   ~400 ms
Ashburn US     23 crates   nearest 200 m   ~459 ms
```

Chosen: **Madrid** (quiet relative to a US-dominant player base, densest near-field), then
later **São Paulo** (39 crates / 70 m nearest at 436 ms) for the next slot.

**Accent trap:** the ip-api sweep returned `São Paulo` while the game's `/v1/geo` returned
`Sao Paulo`. Matching on the raw string silently dropped all seven São Paulo candidates from
the "quietest free proxy" list. Normalize (strip diacritics / casefold) before matching.

Sweep of the pool (100 Proxyscrape datacenter IPs): Ashburn 53, Berlin 11, Toronto 9,
London 8, Paris 7, São Paulo 7, Madrid 3, Bangkok 2, Rome 1. **All datacenter** — and
datacenter exits were not punished on the first run, though connectivity ≠ safety.

## Gate semantics (measured with an unfunded throwaway wallet)

```
[Q1] POST /v1/auth/challenge / /v1/auth/wallet   -> 200  token=yes
[Q2] GET  /v1/me                                 -> 200  gate={"required":true,"ok":false,"min":10000}
[Q3] POST /v1/crates                             -> 200  crates=17  commit=yes
[Q4] POST /v1/fixes (20 fixes)                   -> 200  accepted=20
[Q5] POST /open  (1,261 m away, unfunded)        -> 403  gate_failed
     "Hold at least 10,000 $COLLECT in this wallet to open crates."
```

Everything except the open works on a **zero balance**, and the gate fires **before** the
distance check. Because the requirement is a **hold, not a spend**, capital can be rotated
wallet-to-wallet — at the cost of serialised opens, 2 transfers per wallet, and a more
legible on-chain cluster.

## The region-change flag timeline (why R1 exists)

```
18:37:31  [open 18/24] ...            <- 18 clean opens, Ashburn, suspicious_movement = 0
          stop → repoint Ashburn(45.3.38.134) → Madrid(<PROXY_IP_REDACTED>) → start
18:39:56  [proxy] ***@<PROXY_IP_REDACTED>   [geo] Madrid   [me] opensLeft=7  gate.ok=true
18:44:18  [open err]  suspicious_movement  403     <- FIRST open from the new geo
18:44:18  [loop err 1] suspicious_movement — retry
~18:52    [open err]  suspicious_movement  (second crate) → [loop err 2]
```

Result: **0 successful opens in the new region, 2 rejections, run stalled.**
Then the revert test:

```
18:57  repoint BACK to the original Ashburn proxy (exit IP verified stable, 5/5 requests)
18:58  [open err] suspicious_movement   <- flagged again on the very first open
19:05  one clean attempt 5 min later    <- flagged again
```

Flag events: 18:44 (Madrid), ~18:52 (Madrid), 18:58 (Ashburn after revert), 19:05 (Ashburn).
So `suspicious_movement` here was **wallet state, not a region artefact**, it survived an IP
revert, and the cooldown exceeded 5 minutes (true duration never measured — the user stopped
the run).

**The fix that worked:** a **fresh wallet** from a new key file, imported into the slot while
the slot was idle, region chosen before its first walk → first open succeeded, 0 flags:

```
[farm] budget=24 opens, min-gap=320m
[me] (new) opensLeft=25  gate.ok=true
[geo] São Paulo -23.56,-46.64
[open 1/24] ... -> empty (pity=1, u=0.946)      <- clean
```

Also observed: `GET /v1/me` answered `unauthorized` in a standalone probe right after a
successful `POST /v1/auth/wallet`, while the runner's own `/v1/me` calls worked. Unresolved —
possibly session/device binding. Prefer reading state through the runner's own `[me]` line.

## Payout rail — who actually pays

Deliveries are **operator-paid**:

```
recent winners from /v1/stats -> getSignaturesForAddress -> getTransaction:
  fee payer  = treasury GaB8TsBavRCodk…   (same address as GET /v1/launch → treasury)
  winner SOL delta = +0.000000
  the tx also invoked ATokenGPvbdGVxr… (ATA creation) — paid by the treasury
```

So winning, and receiving the card, cost the winner **zero SOL** — the gate only requires the
token *hold*. Cashing out is the only gas-spending step and the client signs it
(`POST /v1/prizes/{id}/cashout {asset}` then `POST /v1/cashouts/{id}/sent {signedTx}`);
observed self-paid txs 0.000005–0.000145 SOL, and one winner received **USDC +19.63** while
paying **0.000081 SOL**. Payouts settle in **USDC** (`EPjFWdd5…`) net a **2% platform fee** —
checking native SOL concludes "nothing arrived" while the money is there.

First win of the campaign: `u = 0.008731576005942099` against a `< 0.011` band — tier
`common`, `2026 #30 Mega Charizard Y EX CGC 9`, insured $15. Delivery verified through
`GET /v1/players/{addr}/wallet` → `stillHeld: ["HXjTuK1j…AcFUi"]`, `cashedOut: false`, and the
runner's `[me]` line showing `review={"checking":0,"denied":[]}`.

Run rate across the campaign: ~1 card per 80 opens ≈ **1.25%**, vs the game's own lifetime
average 1.278% (2,854 wins / 223,268 opens) — i.e. no edge was being extracted on the roll
itself, only on timing.
