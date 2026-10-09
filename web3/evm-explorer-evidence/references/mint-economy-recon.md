# Mint-Economy Recon (RPC probe recipe)

Verify an NFT mint site's TRUE economy before minting. Site JS labels,
configs, and UI are untrusted — the chain is the authority. Verified on
Robies, NiuFactory, StonksWar, Doodads, and FABLINGS (2026-08).

## Probe skeleton (RPC eth_call)

```python
from eth_utils import keccak
def sel(name, ins): return '0x'+keccak(text=name+'('+','.join(ins)+')')[:4].hex()
# per candidate address, eth_call with:
sel('ownerOf',['uint256'])+format(1,'064x')   # address => ERC-721
sel('decimals',[])                             # 18 => ERC-20
sel('totalSupply',[])
sel('maxSupply',[])
sel('mintPrice',[])
sel('treasury',[])
sel('owner',[])
sel('freemintOpen',[])
sel('mintOpen',[])
```

Contract source (Blockscout `/api?module=contract&action=getsourcecode`) is
the decisive evidence for burn/economy mechanics.

## 1. Which contract is the NFT vs the token

JS config labels LIE. Robies config named `robies` → on-chain that was the
ERC-721 NFT, while config `token` → the ERC-20 $ROBIE.

| Probe | ERC-721 NFT | ERC-20 token |
|---|---|---|
| `ownerOf(1)` | returns address | REVERT |
| `decimals()` | REVERT | 18 |
| `totalSupply()` | small (minted count) | huge / 1e18 |

Map: `code_len`, `name()`, `symbol()`, `decimals()`, `totalSupply()`,
`ownerOf(1)`, `maxSupply()` per address.

## 2. maxSupply: on-chain beats config

Robies site config said `supply: 1e4` but on-chain `maxSupply()` returned
3000. JS defaults are aspirations; contract values decide. Always read
`maxSupply()`, `minted()`, `totalSupply()` from RPC.

## 3. Burn economy check

Verify mint REALLY burns (totalSupply drops) instead of transferring to the
contract:

```solidity
// in NFT mint():
robies.burnFrom(msg.sender, qty * mintPrice);   // ERC-20 burn, permanent
```

- Probe `burn(uint256)` / `burnFrom(address,uint256)` on the token.
- Read token `totalSupply()` twice over time — decreasing = real burn.
- `balanceOf(0x0)` / `balanceOf(0xdead)` large = "burn by send-to-zero"
  (still permanent, different mechanism).

## 4. Buy mechanism: DEX vs fixed-rate counter

Not every "buy" is a DEX. RobiesExchange is a plain counter:

```solidity
function buy() external payable {
    amount = quote(msg.value);               // ETH * fixed rate
    robies.transfer(msg.sender, amount);     // sells from shelf
}
```

Not-a-DEX signals: no pool address, no swap/router functions, no liquidity
pair, no slippage handling, owner-editable fixed rate, `shelf is empty`
guard, ETH swept to treasury. Consequence: no price upside, token is pure
utility — buying = paying the dev at dev-set price.

## 5. Who gets the money

- `treasury()` on the exchange → `owner()` on the NFT → same address = dev
  controls everything (rate, shut, phase, prices, freemint, reservedMint,
  sweep).
- `reservedMint(to,qty)` (onlyOwner, no burn) = collab/vault/team copies.
- `freemintOpen()` / `freemintAllowance(addr)` = free tail may exist but be
  CLOSED; `freemintOpen=0` means no claim possible until owner opens it.

## 6. Free-claim verification (case library)

- `mintPrice()==0` or nonpayable `mintFree()` AND
  `totalSupply()<MAX_SUPPLY()` proves free. UI/API `mintOpen:true` is NOT
  proof.
- **StonksWar** (`0x09C9a292...`): `totalSupply==MAX_SUPPLY=10000` while API
  said `mintOpen:true`; one wallet owning tail ids (9990-10000) = bot swept
  it. `FREE_PER_WALLET=1` in ABI but useless — cap hit first.
- **NiuFactory** (`0x4e3490f4...`): `teamFreeMint=10` but `teamFreeMinted=10`
  — free allocation exhausted, zero left for public; public mint 0.005 ETH.
- **Doodads** (`0x4F2cdecf...` collection, `0xa326f559...` auction): not a
  mint — auction house with `reservePrice=0.0006154` ETH and
  `minimumNextBid=0.00945` ETH payable `bid(uint16,uint128)`. "ONE DOODAD AT
  A TIME" clock: arrival 780s → first close 30s → extension 15s → hard close
  75s.
- **FABLINGS** (`0xa1858144...`): genuinely free — nonpayable `mintFree()`,
  `FREE_PER_WALLET=10`, global drip `lastFreeMintAt()+mintInterval()`,
  `DripNotReady` on race loss. See `free-mint-drip-race` skill for the race
  loop.

## Reporting

Separate: `paid`, `free-but-sold-out`, `free-live`, `auction`, `burn-economy`
(paid + token burn). State who receives the ETH (treasury address == owner?)
so the user can judge "apakah guna / apakah dana ke dev".
