# Bridge Claim — 100% Manual Input Flow

**User directive:** "Edit fitur claim jadi manual aja. Jadi user harus input tx hash."

The claim feature is now 100% manual input — NO list of pending burns, NO per-burn buttons.
Every claim path routes the user to paste a tx hash.

## Current UX Flow

```
User clicks "♻️ Klaim" (in bridge keyboard or /claim command)
  → showClaim: displays prompt "Kirim tx hash burn yang mau diklaim"
  → sets pending "claimtx"
  → User pastes tx hash (e.g. 0xf964...ad9b)
  → validated (0x prefix, min 66 chars)
  → go a.doClaim(context.Background(), userID, chatID, tx)

User clicks "🔍 Cek Iris" (in bridge keyboard)
  → sets pending "iristx"
  → User pastes tx hash
  → a.showIrisStatus(ctx, userID, chatID, tx)
```

## showClaim (bridge.go) — prompt only, no list
```go
func (a *App) showClaim(ctx context.Context, chatID int64, msgID int, userID int64) {
    rows := [][]models.InlineKeyboardButton{
        row(navBack("bridgemenu"), navHome),
    }
    pend, _ := a.St.ListPending(userID)
    txt := "<b>♻️ Klaim Manual</b>\n\nKirim <b>tx hash</b> burn yang mau diklaim..."
    if len(pend) > 0 {
        txt += fmt.Sprintf("\n\n📋 <b>%d burn pending</b> di database.", len(pend))
    }
    a.editOrSend(ctx, chatID, msgID, txt, &models.InlineKeyboardMarkup{InlineKeyboard: rows})
    a.setPending(userID, "claimtx")
}
```

## Session field additions (app.go)
```go
type App struct {
    claimMu  sync.Mutex
    claiming map[string]bool // burnTx → in-flight (reentrancy guard)
}
// in New(): claiming: map[string]bool{}
```

## Handler dispatch (callbacks.go)
```go
case data == "claim":
    a.showClaim(ctx, chatID, msgID, userID)
case data == "bridge:iris":
    a.setPending(userID, "iristx")
    a.send(ctx, chatID, "🔍 Kirim tx hash burn untuk dicek status Iris-nya...", nil)
```

## Pending handlers (callbacks.go — handlePendingExtra)
```go
case pending == "claimtx":
    a.clearPending(userID)
    tx := strings.TrimSpace(text)
    if !strings.HasPrefix(tx, "0x") || len(tx) < 66 {
        a.send(ctx, chatID, "❌ Tx hash tidak valid...", nil)
        return
    }
    a.send(ctx, chatID, "🔄 Memproses claim manual untuk tx: ...", nil)
    go a.doClaim(context.Background(), userID, chatID, tx)

case pending == "iristx":
    a.clearPending(userID)
    tx := strings.TrimSpace(text)
    if !strings.HasPrefix(tx, "0x") || len(tx) < 66 {
        a.send(ctx, chatID, "❌ Tx hash tidak valid...", nil)
        return
    }
    a.showIrisStatus(ctx, userID, chatID, tx)
```

## doClaim skeleton (bridge.go) — with userID guard
```go
func (a *App) doClaim(ctx context.Context, userID, chatID int64, burnTx string) {
    // Reentrancy guard
    a.claimMu.Lock()
    if a.claiming[burnTx] {
        a.claimMu.Unlock()
        a.send(ctx, chatID, "⏳ Klaim untuk burn ini sedang diproses...", backHome())
        return
    }
    a.claiming[burnTx] = true
    a.claimMu.Unlock()
    defer func() { a.claimMu.Lock(); delete(a.claiming, burnTx); a.claimMu.Unlock() }()
    defer func() {
        if r := recover(); r != nil {
            a.send(ctx, chatID, fmt.Sprintf("❌ Klaim crash: %v", r), backHome())
        }
    }()

    b, err := a.St.FindBurnByTx(burnTx)
    if err != nil { a.send(ctx, chatID, "❌ Gagal cari burn: "+err.Error(), backHome()); return }
    if b == nil { a.send(ctx, chatID, "❌ Burn tidak ditemukan.", backHome()); return }
    // USERID GUARD
    if b.UserID != userID {
        a.send(ctx, chatID, "❌ Burn ini milik user lain — hanya pemilik wallet yg bisa klaim.", backHome())
        return
    }
    if b.Status != "pending" { ... }

    a.send(ctx, chatID, "♻️ Mengecek attestation...", nil)
    attn := cctp.GetAttestationOnce(ctx, a.Cfg.IrisBase(), uint32(b.SourceDomain), b.BurnTx)
    if attn.AlreadyMinted { /* MarkCompleted + ✅ sudah selesai */ return }
    if !attn.Ready {
        ageMin := int((time.Now().Unix() - b.CreatedAt) / 60)
        hint := "Coba lagi dalam 1-2 menit."
        if ageMin > 10 {
            hint = "Burn ini sudah tua (>10 mnt) tapi masih pending — rute forwarding kemungkinan sedang gangguan."
        }
        a.send(ctx, chatID, fmt.Sprintf("⏳ Attestation belum siap.\nStatus: %s\nUmur: %d mnt\n\n%s", attn.Status, ageMin, hint), backHome())
        return
    }
    // ... SubmitReceiveMessage on Arc ...
    a.send(ctx, chatID, "✅ Berhasil diklaim! Mint tx: ...", backHome())
}
```

## showIrisStatus (bridge.go) — domain scanning
Scans all 6 CCTP domains (ETH 0, AVAX 1, OP 2, ARB 3, BASE 4, POL 6) via `GetAttestationOnce`.
For each domain: if status != "belum terindeks Iris" → display full result (chain, ready/minted emoji, attestation hex, message hex) and return.
If none found → "Tx tidak ditemukan di Iris (semua chain)."

## Bot Commands (app.go — Run())
```go
{Command: "claim", Description: "Klaim manual bridge (input tx hash)"},
{Command: "iris", Description: "Cek status burn di Iris (tanpa claim)"},
```

## Bridge Keyboard (keyboard.go)
```
[🎯 Arm Snipe] [♻️ Klaim]
[🔍 Cek Iris] [📡 Rute] [🏠 Home]
```

## Rules
- **100% manual.** `showClaim` does NOT render per-burn buttons. All claim paths go through pending "claimtx" → user pastes tx hash → doClaim.
- Async + progress pattern: toast → goroutine → per-step `a.send` → guard + recover.
- `context.Background()` for manual input (new goroutine), `context.WithoutCancel(ctx)` for callback dispatch.
- **UserID guard** in doClaim: `b.UserID != userID` → reject cross-user claims.
- **No debug `log.Printf`** in production code.
- **Rebuild after every change.** Stale binary = features disappear.
