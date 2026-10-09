# Robies And Co. — worked example (2026-08-19)

Full on-chain economy recon of a burn-to-mint NFT project on Robinhood Chain
4663. This is the reference case for `nft-economy-recon` steps 1b–1d.

## Contracts (site config labels were WRONG)

| Config label | Address | On-chain reality |
|---|---|---|
| `token` | `0xb614Ee7A91BD50a88A1f0E64b28Bc4F40cA4A075` | **$ROBIE ERC-20** (decimals 18, totalSupply ~999M) |
| `robies` | `0xA761e19d93A0274BC744DF8f0F3CeE31F56d010c` | **Robies NFT ERC-721** (ownerOf works, maxSupply) |
| `exchange` | `0x0bFFC47628Fe850f5E3FbaCE96Da8886e24B43Da` | RobiesExchange (fixed-rate counter) |
| `art` | `0xa18Bc9b84dd914179bCE5D161E3621602b51e27C` | renderer/art contract |

Lesson: config named the ERC-20 `token` and the ERC-721 `robies` — reversed.
Classify with `ownerOf(1)` / `decimals()` / `MAX_SUPPLY()`, never labels.

## Burn is REAL (from verified source)

`Robies.mint(uint256 qty)`:

```solidity
robies.burnFrom(msg.sender, qty * mintPrice);   // 480 $ROBIE destroyed
```

- `mintPrice` = 480 `$ROBIE` per print (not ETH).
- `RobiesToken` has standard `burn(uint256)` + `burnFrom(address,uint256)`.
- Confirmed drift: token totalSupply dropped ~109k between two reads while
  mints happened.
- `reservedMint` (owner-only, collab/vault/team) does NOT burn.

## Buy step is a FIXED-RATE COUNTER, not a DEX

`RobiesExchange` verified source:

```solidity
uint256 public robiesPerEth = 1_000_000e18;   // fixed, owner-editable
function buy() external payable {
    require(!shut, "the counter is closed");
    uint256 amount = quote(msg.value);        // msg.value * rate
    require(robies.balanceOf(address(this)) >= amount, "shelf is empty");
    require(robies.transfer(msg.sender, amount), "transfer failed");
}
```

- No pool, no AMM, no slippage, no router. Rate is set by owner via
  `setRate`. ETH sweeps to treasury via `sweep()`.
- `shut = true` on deploy; owner must `setShut(false)` to open.

## Money flow (dev cash-out structure)

```
User ETH → RobiesExchange → sweep() → treasury 0x9dd5a20f...
                                        (= NFT owner, same wallet)
User gets $ROBIE → mint() → burnFrom 480 $ROBIE → destroyed
Dev holds: ETH from sales + 900M of 1B $ROBIE supply
```

Treasury `0x9dd5a20f...` == NFT `owner()` — same wallet controls:
`setRate`, `setShut`, `restock`, `setPhase`, `setPrices`,
`setFreemintOpen`, `reservedMint`, `sweep`. 100% project control.

## Live state observed

- Exchange: `shut=0` (open), rate 1M $ROBIE/ETH, shelf 99.28M $ROBIE,
  treasury 0.23 ETH + 0.49 ETH pending sweep.
- NFT: phase 2, minted 1335/3000 (site config said 10000 — contract wins),
  reserved 300, tailMinted 0, freemintOpen 0 (window closed),
  walletLimit 10, mintPrice 480 $ROBIE.

## Verdict

Not free, not a DEX, no second-hand token value: ETH → dev, $ROBIE burned.
Only "value" is the NFT as a collectible; economically a 100% sunk cost per
print. Skip for farming unless the user explicitly wants the NFT.
