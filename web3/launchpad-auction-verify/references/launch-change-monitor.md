# Launchpad Change Monitor — Watchdog Pattern (pools.trade case)

Proven 2026-08-05 while monitoring pools.trade / Uniswap Liquidity Launcher
pre-launch. Working deployments:
- `/root/.hermes/scripts/pools_webgh.py` — cron-safe watchdog (website + GitHub + raw addresses)
- `/root/.hermes/scripts/pools_daemon.py` — 30s background daemon, sends Telegram directly

## Design

State JSON (`~/.hermes/scripts/<name>_state.json`) holds the last-seen hashes.
First run writes baseline and exits SILENT (no alert for pre-existing state).
Every subsequent run diffs; only print (and deliver) when something changed.
Empty stdout = no delivery (cron `no_agent` watchdog semantics).

## Checks

### 1. Website HTML
```python
html = get("https://pools.trade")
teaser = "Coming soon" in html
html_for_hash = re.sub(r'nonce="[^"]+"', 'NONCE', html)   # CSP nonce is per-request!
h = hashlib.sha256(html_for_hash.encode()).hexdigest()[:16]
if state.get("site_hash") and state["site_hash"] != h:
    alert(...)  # site changed; if not teaser, extract CAs: set(re.findall(r'0x[a-fA-F0-9]{40}', html))
```

### 2. GitHub addresses file
```python
data = get("https://api.github.com/repos/Uniswap/sdks/commits?path=sdks/liquidity-launcher-sdk/src/addresses.ts&per_page=1")
sha = json.loads(data)[0]["sha"]   # if != state["gh_sha"] → new deploy generation
raw = get("https://raw.githubusercontent.com/Uniswap/sdks/main/.../addresses.ts")
raw_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
```
A commit message like `register the 2026-08-05 chain-4663 full-redeploy generation`
or a re-mined vanity launcher (`0x0000FffF...`) means the team redeployed the
whole stack — expect bot tokens to front-run within ~30s of the on-chain deploy.

### 3. On-chain factory (new token CAs)
```python
txs = get_json(f"{EXPLORER}/api/v2/addresses/{UERC20_FACTORY}/transactions?filter=to")
newest = txs["items"][0]
if state.get("factory_tx") and state["factory_tx"] != newest["hash"]:
    # extract created CA: receipt logs (Transfer from 0x0 event address) or
    # internal-transactions create2 entry
```
UERC20_FACTORY (Robinhood 4663): `0x000000e200088D55C39a11F609E5F667729ad49b`
Explorer: `https://robinhoodchain.blockscout.com`

## Bot-spam filter (critical for alert quality)

- Decode calldata FIRST: `bytes.fromhex(raw_input[2:]).decode('latin1')`
- Match markers on the DECODED text: `cli|automated|fast_|deploy|bot `
  (hex strings only contain 0-9a-f — matching on hex never fires)
- Deployer `/counters` `transactions_count` > 2000 → bot farm, skip
- Extract readable token name from the same decoded text (first ascii run,
  `len < 40`, not a URL)

Real case: FRKT "Fast Rocket" token was `FAST_CLI` in calldata — filtered.

## Delivery

- Cron: schedule `*/1 * * * *` minimum; cron rejects `30s`.
- 30s cadence: background daemon `while True: sleep(30); check; if changes:
  tg_send(...)`. Bot token + home channel read from `~/.hermes/.env`
  (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_HOME_CHANNEL`).
- Telegram 4096-char limit: split with `--- part N/M ---` markers at <4000 chars.
- Kill pattern: `process kill` the daemon session; `cronjob remove` the job;
  `cronjob pause` for A NONYM-style unrelated jobs the user wants paused.

## Verified facts from the pools.trade investigation

- Website: React Router SPA, "Coming soon from Uniswap", backend
  `entry-gateway.backend-prod.api.uniswap.org`, NS = same Cloudflare pair as
  uniswap.org → official.
- Launcher generations (Robinhood 4663): old `0x00004c4c...`, v3.1.1
  `0x7A6C...`, final vanity `0x0000FffF...` (deployed 2026-08-05 13:25, GitHub
  commit `dd0ea30b` registered it). Token factory stayed the same.
- Bot tokens created within 30s of each new launcher deploy (POOLS, UNIFROG,
  FORK, FRONG, UNIFRONG, FRKT...). "First through the new launcher" ≠ official.
