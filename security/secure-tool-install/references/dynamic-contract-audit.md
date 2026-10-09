# Dynamic Contract Audit (no source available)

When a target EVM contract has NO verified source on the explorer (Blockscout
returns 404 on `/api/v2/smart-contracts/<addr>` and the web UI), you can still
audit for rug/honeypot vectors by reading bytecode + storage over RPC. Used
live on Arc (NOXA Fun) 2026-07-08 where all contracts were unverified.

## Prereqs
- `cast` (foundry) on PATH.
- A working RPC for the chain. Arc mainnet RPC that worked: `https://5042.rpc.thirdweb.com`
  (the one in spring-trade `registry.go` was wrong — llamarpc is ETH, not Arc).
- Blockscout for Arc: `https://arc-mainnet.cloud.blockscout.com` — but its API
  returned 404 for all contracts; fall back to RPC reads.

## Technique

### 1. Get bytecode size (does contract exist?)
```bash
cast codesize <ADDR> --rpc-url <RPC>
```

### 2. Selector scan (what functions exist?)
Get the deployed bytecode, then grep for 4-byte selectors of risky functions:
```bash
BYTECODE=$(cast code <ADDR> --rpc-url <RPC>)
for sel in 0x8da5cb5b 0x40c10f19 0xf9f92be4 0x437823ec 0x5c975abb; do
  echo "$BYTECODE" | grep -qi "${sel#0x}" && echo "PRESENT $sel" || echo "absent $sel"
done
```
| Selector | Function | Red flag if present |
|----------|----------|---------------------|
| `0x8da5cb5b` | `owner()` | owner can act |
| `0x40c10f19` | `mint(address,uint256)` | mint rug possible |
| `0xf9f92be4` | `blacklist(address)` | can freeze holders |
| `0x437823ec` | `excludeFromFee(address)` | fee tricks |
| `0x5c975abb` | `paused()` | can pause trading |

If `owner()` is present but `cast call <ADDR> "owner()(address)"` REVERTS →
no owner set (good). If `mint`/`blacklist` selectors are ABSENT → non-mintable,
non-freezable (good).

### 3. Read storage values
```bash
cast call <ADDR> "owner()(address)" --rpc-url <RPC>          # reverts = no owner
cast call <ADDR> "totalSupply()(uint256)" --rpc-url <RPC>
cast call <ADDR> "name()(string)" --rpc-url <RPC>            # spoof check
cast call <ADDR> "symbol()(string)" --rpc-url <RPC>          # e.g. faked "USDC"
cast call <ADDR> 'balanceOf(address)(uint256)' <POOL> --rpc-url <RPC>  # LP depth
```

### 4. Upgradeability check
```bash
echo "$BYTECODE" | grep -qiE "3659cfe6|delegatecall" && echo "DELEGATECALL/proxy" || echo "not upgradeable"
```
`3659cfe6` = `delegatecall()` opcode. Absence = cannot be swapped for malicious impl.

### 5. Resolve token from a V3 pool
```bash
T0=$(cast call <POOL> "token0()(address)" --rpc-url <RPC>)
T1=$(cast call <POOL> "token1()(address)" --rpc-url <RPC>)
# the non-USDC one is the token under review
```

## Verdict pattern (from NOXA/NOAH audit)
- Token `0x0006ED5d...` (name "FatCatBatRatWifHat", symbol spoofed "USDC"):
  no owner/mint/blacklist/fee → **SAFE contract** (spoof is social-eng, not vuln).
- LaunchFactory `0xE7d4E640...`: no delegatecall → **not upgradeable**.
- Warnings: active owner `0x7E035Fb...` (can set maxTx/fees → monitor);
  LaunchLocker balance = 0 (LP not locked → can be pulled if not graduated);
  pool USDC side tiny ($3.30) → illiquid, high slippage.

## Limits
- Selector scan ≠ full Slither. It catches the big rug vectors (mint/owner/
  blacklist/upgrade) but NOT logic bugs (reentrancy, bad math) — those need source.
- If source ever becomes available, run `slither .` for the real analysis.
