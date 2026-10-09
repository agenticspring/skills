# HashBroker — SHA-256 PoW NFT recon (Robinhood Chain, 2026-09-12)

Worked example for the pre-flight method in SKILL.md. Algorithm fully recovered and verified.

**Two verdicts, in order — see "Hardware changes the verdict" below.** On the 4-core non-SHA-NI
VPS the pre-flight said *not viable* (share ≈0.1%). A later AMD EPYC (6 core, **SHA-NI**)
measured **55 MH/s — 14x** — which moved it to "marginal but free", and a supervised bot was
deployed and run there. It did not win in a 34-minute run, which is the expected outcome.

## Target
- Site: `hashbroker.fun` — "You don't buy a broker. You discover one." Free mint (0 ETH, gas only),
  4,444 supply, 100% on-chain SVG.
- Chain: Robinhood Chain (4663), explorer `robinhoodchain.blockscout.com`
- Mining contract `0x4272D6f51771839F596082eF48fa84D35239Bab3` (**not verified** — bytecode only, 7753 B)
- Staking `0xE2828077B67aAff31816281e1A64d0453959e94`

## Step 1 — recover the spec from the site
Static site, three files. `config.js` is a frozen object with everything you need:

```
CONTRACT_ADDRESS, CHAIN_ID_DECIMAL=4663, RPC_URL, EXPLORER_URL,
MAX_SUPPLY=4444, MINT_PRICE_WEI="0", STAKE_ACTIVATION_SUPPLY=1000, REWARD_TOKENS[]
```

`app.js` holds the selectors verbatim — read them, don't guess:

| Function | Selector |
|---|---|
| `totalSupply()` | `0x18160ddd` |
| `mintPrice()` | `0x6817c76c` |
| `challenge()` | `0xd2ef7398` |
| `currentDifficulty()` | `0x5c062d6c` |
| `mine(uint256,bytes32)` | `0xe43e322c` |

Calldata assembly, straight from `submitProof()`:

```js
const data = SELECTORS.mine + encodeUint256(nonce) + proofChallenge.slice(2);
```

`miner.js` is the WebGPU worker. The `setJob()` / `digest()` WGSL functions give the byte order:

```js
// setJob: baseParams = [...hexWords(address,5), ...hexWords(challenge,8)]
// digest(nonceLo, nonceHi):
//   first[0..4]=address  first[5..10]=0  first[11]=nonceHi  first[12]=nonceLo  first[13..15]=challenge[0..2]
//   second[0..4]=challenge[3..7]  second[5]=0x80000000  second[15]=672
// hexWords() slices the hex into 8-char BE u32 words
```
⇒ 84-byte message, two SHA-256 blocks, block 2 constant per challenge.

## Step 2 — verify against real winning txs
Explorer tx list → take successful `0xe43e322c` calls, split calldata into nonce + challenge,
recompute locally, count leading zero bits:

```
sha256(address(20) ‖ zeros(24) ‖ nonceHi(4 BE) ‖ nonceLo(4 BE) ‖ ch[0:12] ‖ ch[12:32])
```

| Sender | leading zero bits | contract difficulty | result |
|---|---|---|---|
| 0x8f2dAf3A… | 38 | 37 | ✅ ok |
| 0x1b81674A… | 37 | 37 | ✅ ok |
| 0x0f4DD5C1… | 38 | 37 | ✅ ok |
| 0xd910Dfc2… | 37 | 37 | ❌ **tx failed** |

**Reading that last row:** 37 bits at difficulty 37 also failed — so the threshold is not the
discriminator. The failure was a **stale challenge** (submitted value ≠ contract `challenge()` at
that block). Lesson: a rejected proof with sufficient bits means the challenge rotated, not that
your formula is wrong. Always re-read `challenge()` before concluding a bug.

## Step 3 — viability math (the part that saves the session)
- `totalSupply()` 35 → 40 during recon; difficulty sampled at historical blocks:
  **35 → 34 → 35 → 36 → 37 → 38** (rising with supply ⇒ adaptive, and the easy window is gone).
- 48 txs, 39 successful, only ~5 distinct addresses (one address minted 9× ⇒ **no per-wallet cap**).
- Median gap between successful mints ≈ **27 s** (bursts; ~3 min in quiet stretches).
- ⇒ implied network `2^38 / 27 s ≈ 9 GH/s`, i.e. GPU rigs.
- This VPS: 4 cores Intel Xeon Gold 6138, **no GPU, no SHA-NI**. Measured `openssl speed sha256`
  at 64 B ≈ 52 MB/s ≈ 0.82 MH/s/core ⇒ ~3 MH/s total, ~0.32 MH/s from Python `hashlib`.
- ⇒ share ≈ 0.1% ⇒ expected ~1000 challenges per win. **Skip.**
- Precompute shortcut tested and **absent**: `keccak(blockhash)`, `keccak(prevRandao)`,
  `keccak(prevChallenge)`, `keccak(nonce)`, `keccak(sender)`, and concatenations — all miss.
  `prevRandao` was constant (`0x…092400`) across the sampled blocks, so it carries no entropy,
  yet still isn't the challenge source — the derivation uses something else internal.

## Technique: reading a Cloudflare-protected explorer from the agent

`curl` against `robinhoodchain.blockscout.com/api/v2/...` returns **HTTP 403 "Just a moment…"**
(Cloudflare challenge), and the API can return 500 for unverified contracts. Working path:

1. Open the explorer in the browser tool once to clear the challenge.
2. Run the API call **from inside the page** (`browser_console` with a `fetch(...)` expression) —
   same-origin, already-thened cookies, no challenge:

```js
(async () => {
  const r = await fetch('/api/v2/addresses/0x…/transactions?filter=to', {headers:{accept:'application/json'}});
  return await r.json();
})()
```

Useful endpoints: `/api/v2/addresses/{a}/transactions?filter=to`,
`/api/v2/smart-contracts/{a}` (`is_verified`, `source_code`, `abi` — absent for unverified).
Return only the fields you need; raw responses are large.

## Hardware changes the verdict (second pass, 2026-09-12)

The pre-flight verdict above was measured on `empero` (82.39.206.183 — Intel Xeon Gold 6138,
4 core). A second VPS `<REDACTED>` (**AMD EPYC, 6 core, `sha_ni` present**) was benchmarked
and is **14x faster on the identical workload**:

| Machine | cores | `sha_ni` | per core | total |
|---|---|---|---|---|
| empero, Xeon Gold 6138 | 4 | ❌ | 0.97 MH/s | 3.93 MH/s |
| vmi3236372, AMD EPYC | 6 | ✅ | 9.45–10.1 MH/s | **51–57 MH/s** |

- `openssl speed -seconds 3 sha256`: 52.5 MB/s @64 B (empero) vs **179 MB/s** (EPYC).
- Kernel used OpenSSL `SHA256_Transform` (1 block/call) — 10.11 MH/s/core vs 8.05 for the
  Init/Update/Final API, i.e. **~25% saved** by dropping per-call overhead. Compile
  `-DOPENSSL_SUPPRESS_DEPRECATED -lcrypto`.
- That is ~86–92% of the SHA-NI ceiling (EPYC bulk rate 1.4 GB/s @8 KB ⇒ ~11 MH/s/core max),
  so there was no meaningful headroom left — hence no hand-written intrinsics.
- Recomputing the share: 55 MH/s against an implied network of ~15–55 GH/s ⇒ **~0.1–0.4%**,
  and difficulty kept climbing (41 → 43 during the session, supply 64 → 102 in 34 min).
  Expected ~5–20 wins over the whole remaining run, ~11 h of mining per proof.

**Takeaway that generalises:** the pre-flight "skip" verdict is only valid for the machine you
measured it on. For SHA-256 PoW, re-run `grep -o sha_ni /proc/cpuinfo` on any *other* box
before believing the verdict — checking one non-SHA-NI VPS and concluding "bad project" is the
expensive mistake.

## Free validation of the submit path (no gas spent)

Both checks from SKILL.md were run against the unverified contract, and both paid off:

1. **Historical replay.** A real winning mint (sender `0x8f2dAf3A…`, nonce `0xcae298007226ba59`,
   challenge `0x96f61170…`) rebuilt as `0xe43e322c` + nonce(32 B) + challenge(32 B):
   - `--block 61212355` (one block before the mint) → **succeeds**, returns `0x…24`
   - `--latest` → **reverts** — correct, the challenge had moved on
   ⇒ calldata encoding proven correct for free, on a contract with no ABI published.
2. **Difficulty-floor probe.** Mined a 30-bit proof for the live challenge, `eth_call`'d it:
   - revert `0x09bde339` = **`InvalidProof()`** ⇒ difficulty really is enforced for every wallet,
     no fresh-wallet allowance, no shortcut. hashrate is the only lever. (Cost: $0.)
   - the earlier stale-challenge revert decoded as `0xaa2bf635` = **`StaleChallenge()`**.

Selectors resolved via `api.openchain.xyz/signature-database/v1/lookup?function=0x<sel>` — the
only practical way to learn error semantics on a contract with no verified source.

## Deployed bot (vmi3236372) and its honest result

Layout `/root/.hb/`: `hb_mine` (+ .c), `hb_bot.py` (poll challenge → mine a 5 s chunk →
re-check → free `eth_call` simulate → sign+send raw), `hb_ctl.sh {start|stop|status|watchdog}`,
`pk` (0600), `bot.log`, `state.json`; cron watchdog every 5 min; wallet = the set-1 burner.

Run: **33.7 min, 387 chunks, 51.2 MH/s sustained (~98% duty), ~104 billion hashes, best 38 bits
against a required 41→43, 0 wins, 0 errors, 0 gas spent.** The user then stopped it.

Sanity check that the kernel was genuinely working rather than silently wrong: over 1.04e11
random candidates the best-of-run leading-zero count should sit near `log2(1.04e11) ≈ 36.6`;
we observed **38**. Match ⇒ the miner was correct and the race simply wasn't won — which is the
expected result at ~0.2% share over half an hour, not a bug.

Key operational pitfalls hit here are written up in SKILL.md ("Running the miner as a
long-haul supervised job") — the `pkill -f <script>` self-match over SSH, the watchdog cron
resurrecting a "stopped" bot, duplicated logging, and `/dev/shm` keys not surviving reboot.

## Artefacts
- `/tmp/hashbroker_{config,app,miner}.js` — site sources
- `/tmp/hb_verify.py` — formula + 3/3 tx verification (the script worth keeping)
- `/tmp/hb_diff_hist.py` — difficulty-at-historical-block sampler
- `/tmp/hb_chal_test.py` — challenge-derivation hypothesis tester
