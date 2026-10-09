# Free-mint site verification (prove 0 wei on-chain)

Before broadcasting any mint, prove "free" = `0 wei` — never trust page labels.
Proven liars: Hoodilio ("freemint" = 0.00055 ETH), Market Arcana ("it is free"
= 0.0015 ETH), Robin Gorillas (price 0 → 0.0018 ETH at open). Recipe tested on
AlienNode, MINECAT, NiuFactory, StonksWar, Fablings, Mythborn.

## Steps

1. **Fetch the site** (`curl -L`, read via `read_file` on saved HTML).
   Many projects ship `skill.md` / `skill.en.md` — the LLM brief. It states
   contract, chain, price, mechanics. Cross-check everything against chain.
2. **Find the contract** — Next.js/Vite pages: grep the page JS chunks for
   `0x[0-9a-fA-F]{40}` and `fetch("/api/...")`. Artifact files (`/abi/X.json`,
   `src/config.js`) often contain `addresses` + `params`. `viem`-based sites
   list contracts in a config module (e.g. `CONFIG.addresses`).
3. **Read ABI** from site artifact or Blockscout
   (`/api/v2/smart-contracts/<addr>`). Note view functions: `mintPrice()`,
   `PRICE()`, `mintCost(wallet,qty)`, `mintOpen()`, `mintPhase()`,
   `MAX_SUPPLY()`, `totalSupply()`, `FREE_PER_WALLET()`,
   `freeMintsRemaining(wallet)` / `freeMinted(wallet)`, `MAX_PER_TX`,
   `mintInterval()`, `lastFreeMintAt()`.
4. **Probe on-chain via RPC** (Alchemy Robinhood). Compute selectors with
   keccak — never hardcode guesses. Key checks:
   - `mintPrice()` == 0 AND `mintCost(wallet,1)` == 0 (some contracts give 1
     free per wallet; cost of qty 2+ is the paid lane).
   - `mintOpen()==true`, `mintPhase` active, `totalSupply() < MAX_SUPPLY()`.
   - `FREE_PER_WALLET` vs `freeMintsRemaining(wallet)`.
5. **Sold-out trap**: `totalSupply == MAX_SUPPLY` means mint reverts even when
   the free allowance mapping still shows slots (StonksWar: 10,000/10,000,
   ownerOf of top IDs all one wallet = sweep). Check ownerOf last IDs to see
   if a whale/bot swept.
6. **Paid lanes**: `mintSkip`/`skipPrice`, `value` in the JS `sendTx` call —
   skip those; only `0 wei` mints qualify.

## Fast answers for the "ga ada yg free?" question

| Project | Free? | Proof |
|---------|-------|-------|
| NiuFactory | NO | mint 0.005 ETH, teamFreeMint 10/10 used |
| StonksWar | NO (sold out) | FREE_PER_WALLET=1 but supply 10,000/10,000 |
| Fablings | YES | mintFree 0 wei, FREE_PER_WALLET=10, supply 33k/40k |
| MINECAT | mining free, claim ~0.0001 ETH | submitWork 0, claim mintPriceWei |
| AlienNode | NO | 0.0005 ETH puzzle-PoW mint |
| Mythborn | no (signed stages) | OG/FCFS gated, public 0.0002 ETH |

## Caveats

- `eth_call` returns null for a wrong selector — treat as selector bug, not
  "function missing", unless the ABI confirms absence.
- Drops API (`api.opensea.io/api/v2/drops/<slug>`) is authoritative only for
  OpenSea SeaDrop; custom contracts (AlienNode, Fablings) won't appear there.
- `remainingSpots:0` in a whitelist API response does NOT mean closed (Robillio
  accepted 100 entries with `remainingSpots:0`). Only an explicit error means
  closed.
