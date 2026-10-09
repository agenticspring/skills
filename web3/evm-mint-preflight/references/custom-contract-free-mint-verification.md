# Custom Contract Free-Mint Verification — Worked Checks

Session detail: stonkswar.com (Stonks War — Goblin Genesis) and niulai.cx
(NiuFactory), both Robinhood Chain 4663. Both look like "free mint" sites;
neither is mintable for free. These are the exact checks that proved it.

## General recipe

1. Fetch site → find JS bundle → extract contract address + ABI strings.
2. Pull ABI: `https://<site>/abi/<Contract>.json` (foundry artifact) or
   Blockscout verified contract.
3. Compute selectors: `keccak(text="fnName(type1,type2)")[:4]` → hex.
4. `eth_call` via Alchemy Robinhood RPC:
   `https://robinhood-mainnet.g.alchemy.com/v2/<key>` (chain id 4663).
5. Wallet reads must use the lowercase padded address:
   `sel + addr[2:].lower().rjust(64, '0')` for `(address)` args.

## Stonks War — Goblin Genesis (sold out despite free ABI)

Contract: `0x09C9a2928C8b03B8e0638F3ec3d1E3E96dE704cB`
Treasury: `0xAc4b784B94AAe6f4BBE6b65A1B69F341F2d591e3`
trustedSigner: `0x5c69B4cAfFEcD528597d38e355E2351084bB18e7`

Free-mint ABI surface (all present, all look promising):

```text
mintOpen() view returns (bool)          → 1 (true)
mintPhase() view returns (uint8)        → 1
mintPrice() view returns (uint256)      → 1000000000000000 (0.001 ETH)
maxPerWallet() view returns (uint256)   → 5
FREE_PER_WALLET() view returns (uint256) → 1
freeMintsRemaining(wallet)               → 1 for Set 1
mintCost(wallet, 1)                      → 0  ← looks free!
```

Why it is NOT mintable:

```text
totalSupply() == 10000
MAX_SUPPLY()  == 10000   → SOLD OUT
ownerOf(10000/9999/9990) == same wallet 0x5603...a29 (sweep)
ownerOf(1) == 0x5c69...e7 (trustedSigner/team)
```

Site API `GET /api/mint-status` returned `mintOpen:true`, `mintPhase:1`,
`totalSupply:10000`, `maxSupply:10000` — the API mirrors phase, not remaining
supply. On-chain `totalSupply == MAX_SUPPLY` is the authority.

Mint flow is website-gated EIP-712: `mint(qty, nonce, deadline, sig)` where
`sig` comes from `POST /api/mint-auth` (trustedSigner signs). No direct-call
path without the backend signature.

## NiuFactory — pixel bulls (teamFreeMint is NOT public)

Contract: `0x4e3490f402E8F633b649dFda476af9024676E7F1`
NB token: `0xc965aea226a035f812e290c53ce17c7c3859bbe4`
Milk (NN): `0x146a297997ae5c0259037472d4924a40f6b3fd6a`

Free-looking ABI surface:

```text
TEAM_FREE_MINT() view → 10     ← free allocation for TEAM ONLY
teamFreeMinted() view → 10     ← team quota fully spent
MINT_PRICE() view     → 0.005 ETH (paid)
MAX_SUPPLY()          → 3000
totalMinted()         → 750 (public mint, 0.005 ETH)
```

Lesson: a `TEAM_FREE_MINT` constant in the ABI does not mean the public gets
free mints. `teamFreeMinted == TEAM_FREE_MINT` means the team already spent
its quota. Paid `MINT_PRICE` is the real gate.

## Decision rules

| Signal | Meaning |
|--------|---------|
| `mintCost(wallet,1) == 0` AND `totalSupply < MAX_SUPPLY` | free AND mintable |
| `mintCost(wallet,1) == 0` AND `totalSupply == MAX_SUPPLY` | free allowance but SOLD OUT — skip |
| `teamFreeMinted < TEAM_FREE_MINT` | team-only free quota, not public |
| site API `mintOpen:true` alone | NOT proof — stale phase mirror |
| last token IDs one wallet | sweep happened, window closed |
| `trustedSigner` + `/api/mint-auth` | EIP-712 gated; needs site signature |

## Selector table (computed with eth_utils keccak)

```text
mintOpen()            → 0x8f38249c
mintPhase()           → 0x93206ada
mintPrice()           → 0x6817c76c
maxPerWallet()        → 0x24cbe8b6
FREE_PER_WALLET()     → 0x51b0c9c2
freeMintsRemaining(address) → 0x2433af56
mintCost(address,uint256)   → 0x9cd81f37
mintedBy(address)     → 0x1fb4372d
totalSupply()         → 0x18160ddd
MAX_SUPPLY()          → 0x32cb6b0c
trustedSigner()       → 0x22b91a0c
TEAM_FREE_MINT()      → 0xf9b57c66
teamFreeMinted()      → 0x08d7a4ac
ownerOf(uint256)      → 0x6352211e
```

Selectors are reproducible from the verified ABI; recompute rather than trust
a table copied from an unrelated session if the ABI changes.

## Fablings — genuine free drip (positive case, 2026-08)

Contract items: `0xa185814414aa3D39c9A0B73A373E00C8C04Cb384`
Chain 4663. Proved free AND mintable:

```text
FREE_PER_WALLET() → 10        ← genuine public free allowance
freeMinted(Set1)  → 0         ← unused
mintFree()        → nonpayable (value 0)
mintInterval()    → 3         ← global drip cooldown (seconds)
lastFreeMintAt()  → shared timestamp, resets when ANYONE wins
totalSupply()     → 32945 < MAX_SUPPLY() 40000
```

Key mechanics learned (see `free-mint-drip-race` skill for full scripts):

- The drip is GLOBAL: `mintFree()` reverts `DripNotReady` (0x5273678a) unless
  `(lastFreeMintAt + mintInterval) <= blockTime`. Race loop: poll, fire with
  explicit nonce, retry on DripNotReady, stop at `FreeWalletCapReached`
  (0x53353903).
- `mintFree()` selector `0x8ab53447`; `lastFreeMintAt()` `0xfca4b80e`;
  `mintInterval()` `0x0e726e6b`.
- Result: 100 NFTs minted free across 10 wallet sets (10/wallet), consolidated
  to Set 1 via `safeTransferFrom` (from=owner, to=Set1 — arg order matters,
  reversed = `ERC721IncorrectOwner` 0x177e802f), dust swept at baseFee*1.10.

## Doodads — auction house, not a mint

Site `doodads.wtf` — "ONE DOODAD AT A TIME", 1,000 CC0 prints. Not free:

```text
Collection:  0x4F2cdecf80D8BA89c62A5f58c706639A1F08053A  (ERC-721, MAX_SUPPLY 1000)
AuctionHouse: 0xa326f559De3d2D9569D1a768a82C9E645F4C43DD  (DoodadAuctionHouse)
reservePrice()    → 0.0006154 ETH (auction opening price)
minimumNextBid()  → 0.00945 ETH
MAX_SLOTS()       → 1000
ARRIVAL_WINDOW    → 780s / FIRST_CLOSE 30s / EXTENSION 15s / HARD_CLOSE 75s
bid(uint16,uint128) → payable — mint happens only by winning the auction
```

Signals that a site is auction-gated instead of free-mint: copy says "one at a
time" / "mint button in the Bidding Box"; ABI has payable `bid()` plus
`reservePrice()`/`minimumNextBid()`; `currentAuction()` returns a struct slot
counter. Nonzero reserve = paid bidding only — skip under free-only policy.

## Robies And Co. — config labels lie about which CA is the NFT

Site `robieshood.xyz` — "10,000 prints, buy $ROBIE, burn to print". Config
object from JS chunk (`7808-1b60634ebedef648`) mapped addresses as:

```text
"token"    → 0xb614Ee7A91BD50a88A1f0E64b28Bc4F40cA4A075  ← actually $ROBIE ERC-20
"robies"   → 0xA761e19d93A0274BC744DF8f0F3CeE31F56d010c  ← actually NFT (ERC-721)
"exchange" → 0x0bFFC47628Fe850f5E3FbaCE96Da8886e24B43Da
"art"      → 0xa18Bc9b84dd914179bCE5D161E3621602b51e27C
```

The key names were EXACTLY OPPOSITE of the contract types. On-chain probe that
settled it:

```text
0xb614Ee7A: decimals() → 18, totalSupply() ≈ 999.4e21  → ERC-20 $ROBIE
0xA761e19d: ownerOf(1) → 0x83...7373 (address), maxSupply() → 10000 → ERC-721 NFT
```

Rule: never trust config key names (`token` vs `art` vs `robies`) to pick the
NFT CA. Probe `ownerOf(1)` (ERC-721 returns an address) and `decimals()`
(ERC-20 returns 18) before reading mint state. `name()`/`symbol()` can return
empty on custom contracts, so ownerOf/decimals are the authoritative probes.

Mint price: 0.00048 ETH or 480 $ROBIE; freemint = last 300 reserved prints via
`FreemintAllowance` — allowance-gated, not open.
