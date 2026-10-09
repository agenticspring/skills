# /iris Command — Domain-Scanning Iris Status Checker

## Entry points
1. **`/iris` command** (registered in `SetMyCommands`) → sets pending `"iristx"`, prompts for tx hash
2. **`[🔍 Cek Iris]` button** in bridge keyboard (`bridge:iris` callback) → same as above

## Dispatch (`dispatch.go`)
```go
case "/iris":
    a.setPending(userID, "iristx")
    a.send(ctx, chatID, "🔍 Kirim tx hash burn untuk dicek status Iris-nya (contoh: 0x1234...abcd):", nil)
    return
```

## Bridge keyboard callback (`callbacks.go`)
```go
case data == "bridge:iris":
    a.setPending(userID, "iristx")
    a.send(ctx, chatID, "🔍 Kirim tx hash burn untuk dicek status Iris-nya (contoh: 0x1234...abcd):", nil)
```

## Pending handler (`callbacks.go` — `handlePendingExtra`)
```go
case pending == "iristx":
    a.clearPending(userID)
    tx := strings.TrimSpace(text)
    if !strings.HasPrefix(tx, "0x") || len(tx) < 66 {
        a.send(ctx, chatID, "❌ Tx hash tidak valid. Harus dimulai dengan 0x dan panjang benar.", nil)
        return
    }
    a.showIrisStatus(ctx, userID, chatID, tx)
```

## Core function (`bridge.go` — `showIrisStatus`)
Scans all known CCTP domains (0-6, skipping 5=unused) with `GetAttestationOnce`, returns as soon as a domain responds (non-"belum terindeks"). Output format:
```
<b>⏳ Iris Status</b> — <code>0xf964…ad9b</code>
Chain: <b>Avalanche</b> (domain 1)
Status: <code>pending_confirmations</code>
Ready: <b>false</b> · AlreadyMinted: <b>false</b>

Attestation: <code>PENDING…</code>
Message: <code></code>
```

Domains scanned: 0=ETH, 1=AVAX, 2=OP, 3=ARB, 4=BASE, 6=POL.
Emoji: ✅ (AlreadyMinted), 🟢 (Ready), ⏳ (pending).

## Why domain scanning?
The user may not remember which source chain a burn originated from. `showIrisStatus` brute-force scans 6 domains — the first that doesn't return "belum terindeks Iris" is the correct one.

## Register in bot commands
```go
{Command: "iris", Description: "Cek status burn di Iris (tanpa claim)"},
```

## Keys
- `AttestationStatus.Status` is never empty — fills "belum terindeks Iris (coba lagi nanti)" for nil results.
- `AttestationStatus.Attestation` is set even when PENDING. Use `ShortHex(attn.Attestation, 10, 6)` for display.
- `AttestationStatus.Message` is empty unless Ready.
