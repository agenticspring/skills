# HONKERS join — Robinhood Chain

## Summary
CLI farmer for paid `join()` mint on Robinhood Chain + optional read-only slot monitor.

## Params
| Item | Value |
|---|---|
| Chain | Robinhood Chain |
| Chain ID | `4663` (`0x1237`) |
| RPC | `https://rpc.mainnet.chain.robinhood.com` |
| Token | `0x04E71447c345309858C015de1D8e6aFb7224AF8b` |
| Call | `join()` selector `0xb688a363` |
| Value | `0.001 ETH` → `100 HONKERS` |
| Explorer | `https://robinhoodchain.blockscout.com` |

## Local setup (Dez VPS)
- Path: `/root/honkers_join_bot`
- Deps: `eth-account` in project `.venv`
- Secrets: `keys.txt` + `wallets.json` chmod 600; never echo PKs in chat
- Public: `addresses.txt` for funding
- Default generate **1 wallet** unless user asks more
- Run: `.venv/bin/python honkers_join.py --file keys.txt --yes`
- Check: `.venv/bin/python honkers_join.py --check 0xADDR`

## Pre-flight (no TX)
```text
eth_call join(from=wallet, value=0.001e18, data=0xb688a363)
```
| Result | Meaning |
|---|---|
| success / insufficient funds (node) | capacity may still be open |
| revert `0x5cacae9d` | **VaultFull()** — do not broadcast |
| other selector e.g. `0x9a0833b6` | often wrong value |

## Capacity views (unverified, probed)
| Selector | Name (probed) | Role |
|---|---|---|
| `0xbf4386a0` | maxMembers() | capacity |
| `0x11aee380` | memberCount() | filled |
| `0x01e1d114` | totalAssets() | vault ETH |
| `0xc57981b5` | join price wei | 1e15 |
| `0xd1b17078` | reward wei | 100e18 |
| `0x18160ddd` | totalSupply | e.g. 2500 when full |

Observed full state: max=25, members=25, supply=2500, vault ETH=0.025.

## Live attempt lesson
- Funded 0.0015 ETH → tx broadcast → **REVERT VaultFull**
- Gas only spent; residual ETH ~0.001498
- Wallet example: `0x193Af36FcD692b790CC00d39fBE4b787f703bdf7`

## Slot monitor (read-only by default)
- `monitor_slots.py --loop 5 --no-auto-join` in `screen -S honkers-monitor`
- `monitor.env`: `DISCORD_WEBHOOK` + `DISCORD_PING_USER_ID` + `AUTO_JOIN=0` (gitignored)
- Alert only on capacity reopen (slotsLeft↑ / maxMembers↑ / joinOpen false→true)
- `--test-alert` for webhook smoke test
- **Default: notify only.** Do not auto-mint on slot open unless Dez says gas join/mint
- Auto-join can be enabled later via `--auto-join` / `AUTO_JOIN=1`, but wait for explicit user command on FCFS
- Before join: fund ~0.0015–0.002 ETH (burner may be nearly empty after failed REVERT gas)

## Cost estimate
- Fixed: 0.001 ETH + small gas
- ~$1.9–$2.8 at ETH ~$1850–1870; plan ~0.0015–0.002 ETH per wallet
