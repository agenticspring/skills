# Full Button Audit — Spring-Trade Bot

## Dispatch Chain (urutan handler di `routeCallback`)

```
routeCallback(ctx, update, userID, chatID)
  │
  ├─ a.answer(ctx, cq.ID, "")                        // spinner dismiss
  │
  ├─ Admin guard (data=="admin" || HasPrefix "adm:")  // line 25
  │   └─ handleAdminCallback(ctx, userID, chatID, msgID, data)
  │
  ├─ Settings guard                                   // line 31
  │   └─ handleSettingsCallback → handleCardCallback / handleBgCallback
  │
  └─ Main switch                                      // line 35
      ├─ main, main:refresh, help
      ├─ wallet, wact:, wallet:*, wexpc:, wexp:
      ├─ settings, cg:, cf:, cv:, cr:, ce:
      ├─ bridgemenu, bridge, bridge:go, bfast:, bx
      ├─ arm, arm:go, arm:cancel, armx, claim, bridge:iris
      ├─ claim:* (manual guard)
      ├─ gate, csrc:
      ├─ trade, trade:pos, trade:snipe
      ├─ tcard:, tbuyq:, tsellt:, tbuyx:, tsellx:
      ├─ tgweiv:, tslipv:, tgweix:, tslipx:, tgwei:, tslip:
      ├─ psell:, pcard:
      └─ default → "Aksi tak dikenal." (typo: tak→tidak)
```

## Complete Callback→Handler Matrix

### Main Menu
| Callback | Handler | Source |
|----------|---------|--------|
| `main` | `showHome(ctx, chatID, msgID, userID, false)` | keyboard.go:navHome |
| `main:refresh` | `invalidateHome` + `showHome(force=true)` | keyboard.go |
| `help` | `editOrSend(helpText, backHome())` | keyboard.go |
| `admin` | `showAdmin(ctx, chatID, msgID)` via handleAdminCallback | keyboard.go (admin only) |

### Wallet
| Callback | Handler | Source |
|----------|---------|--------|
| `wallet` | `showWallet` | keyboard.go |
| `wact:<addr>` | `activateWallet` | keyboard.go |
| `wallet:import` | `setPending("import")` + prompt | keyboard.go |
| `wallet:gen` | `generateWallet` | keyboard.go |
| `wallet:del` | `showDeleteWallet` | keyboard.go |
| `wallet:rm:<addr>` | `deleteWallet` | callbacks.go |
| `wallet:export` | `showExportMenu` | keyboard.go |
| `wexpc:<addr>` | `confirmExport` (encrypted) | callbacks.go |
| `wexp:<addr>` | `confirmExport` (plaintext) | callbacks.go |

### Bridge
| Callback | Handler | Source |
|----------|---------|--------|
| `bridgemenu` | `showBridgePlan` | keyboard.go |
| `bridge` | `showBridgePlan` with plan | keyboard.go |
| `bridge:go` | `doBridge` | confirmBridge keyboard |
| `bfast:<amount>` | `setFastBridge(amount)` | keyboard.go |
| `bx` | `setPending("bridgex")` + prompt | keyboard.go |
| `csrc:<chain>` | `setSourceChain` + invalidateHome | keyboard.go |
| `arm` | `showArm` | keyboard.go |
| `arm:go` | `startArm("")` + `showArm` | armMenu keyboard |
| `arm:cancel` | `clearArm` | keyboard.go |
| `armx` | `setPending("armx")` + prompt | keyboard.go |
| `claim` | `showClaim` → sets pending("claimtx") + prompt | keyboard.go |
| `bridge:iris` | `setPending("iristx")` + prompt "Kirim tx hash..." | keyboard.go |
| `gate` | `showGate` | keyboard.go |

### Claim (manual input)
| Callback | Handler | Source |
|----------|---------|--------|
| `claim:<burnTx>` | `doClaim` async | → dulu dari list, sekarang deprecated |
| text input | `pending=="claimtx"` → validates 0x → `doClaim` async | handlePendingExtra |
| text input | `pending=="iristx"` → validates 0x → `showIrisStatus` | handlePendingExtra |
| `/claim` | `showClaim` → sets pending("claimtx") | dispatch.go |
| `/iris` | `setPending("iristx")` + prompt | dispatch.go |

### Trade
| Callback | Handler | Source |
|----------|---------|--------|
| `trade` | menu trade (paste CA) | keyboard.go |
| `trade:pos` | `showPositions` | keyboard.go |
| `trade:snipe` | auto-snipe info | keyboard.go |
| `tcard:<token>` | `showTokenCard` | token list |
| `tbuyq:<token>:<amt>` | `doBuyToken` | token card |
| `tsellt:<token>:<amt>` | `doSellToken` | token card |
| `tbuyx:<token>` | `setPending("tbuyx:TOKEN")` + prompt | token card |
| `tsellx:<token>` | `setPending("tsellx:TOKEN")` + prompt | token card |
| `tgweiv:<token>:<gwei>` | set priority gwei | token gwei picker |
| `tslipv:<token>:<slip>` | set slippage | token slip picker |
| `tgweix:<token>` | `setPending("tgweix:TOKEN")` + prompt | token card |
| `tslipx:<token>` | `setPending("tslipx:TOKEN")` + prompt | token card |
| `tgwei:<token>` | gwei picker menu | token card |
| `tslip:<token>` | slippage picker menu | token card |
| `psell:<idx>:<pct>` | `sellPositionByIndex` | position card |
| `pcard:<idx>` | `sendPnLCard` | position card |

### Settings
| Callback | Handler | Source |
|----------|---------|--------|
| `settings` | `showSettings` | keyboard.go |
| `cg:<group>` | `showGroup` | settings menu |
| `cf:<field>` | `showField` | group view |
| `cv:<value>` | `setFieldValue` | field view |
| `cr:<field>` | `resetField` | field view |
| `ce:<field>` | `setPending("ce:FIELD")` + prompt | field view |

### Admin (handleAdminCallback)
| Callback | Handler | Source |
|----------|---------|--------|
| `admin` | `showAdmin` | keyboard.go |
| `adm:gen` | `showGenCode` | admin menu |
| `adm:mkx` | `setPending("adm:mkx")` + prompt | admin menu |
| `adm:mk:<n>` | `makeCode(n)` | admin menu |
| `adm:codes` | `showCodes` | admin menu |
| `adm:rv:<code>` | `RevokeCode` | code list |
| `adm:users:<p>` | `showUsers(p)` | admin menu |
| `adm:ban:<id>` | `SetUserStatus(id, banned)` | user list |
| `adm:unban:<id>` | `SetUserStatus(id, active)` | user list |
| `adm:stats` | `showStats` | stats page |

### PnL Card (handleCardCallback)
| Callback | Handler | Source |
|----------|---------|--------|
| `card:settings` | tombstone settings → showCardSettings | settings menu / card inline |
| `card:tmpl` | `editCardKeyboard(cardTmplRows)` | showCardSettings |
| `card:tmpl:<tmpl>` | `SetSetting` + `showCardSettings` | cardTmplRows |
| `card:font` | `editCardKeyboard(cardFontRows)` | showCardSettings |
| `card:font:<font>` | `SetSetting` + `showCardSettings` | cardFontRows |
| `card:color` | `editCardKeyboard(cardColorRows)` | showCardSettings |
| `card:color:<color>` | `SetSetting` + `showCardSettings` | cardColorRows |
| `card:bg` | `editCardKeyboard(showBgInlineRows)` | showCardSettings |
| `card:back` | `showSettings(ctx, chatID, 0, userID)` — KIRIM BARU | card inline rows |
| `card:home` | `showHome(ctx, chatID, 0, userID, false)` — KIRIM BARU | card inline rows |

### Background (handleBgCallback)
| Callback | Handler | Source |
|----------|---------|--------|
| `settings:bg` | `showBackgroundMenu` | legacy settings → bg |
| `bg:gallery` | `showBgGallery` | showBackgroundMenu |
| `bg:del:<idx>` | `deleteBgFromGallery` + `showBgGallery` | showBgGallery |
| `bg:set:<key>` | `SetSetting` + `dismissPicker` + `showCardSettings` | showBackgroundMenu / showBgInlineRows |
| `bg:reset` | `SetSetting("")` + `dismissPicker` + `showCardSettings` | showBackgroundMenu / showBgInlineRows |
| `bg:upload` | `setPending("bgupload")` + `showPicker(prompt)` | showBackgroundMenu / showBgInlineRows |
| `bg:preview` | `sendCardPreview` | showBackgroundMenu |

## Audit Checklist

- [ ] All keyboard.go `btn()` calls have a matching handler in `routeCallback` or sub-handlers
- [ ] All callbacks prefixed with `adm:` are caught by the admin guard (line 25)
- [ ] All callbacks prefixed with `card:`/`bg:`/`settings:bg` are caught by handleSettingsCallback
- [ ] Card inline keyboard rows use `card:home`/`card:back` (NOT `navHome`/`navBack`)
- [ ] No callback falls through to `default: "Aksi tak dikenal."` in production
- [ ] All `setPending` states have a matching `case pending ==` in `handlePendingExtra`
