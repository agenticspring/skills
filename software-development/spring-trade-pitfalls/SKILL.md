---
name: spring-trade-pitfalls
description: Common bug patterns and fixes for spring-trade bot.
version: 0.1.0
author: Hermes
platforms: [linux]
metadata:
  hermes:
    tags: [SpringTrade, Pitfalls, Debugging, Go]
---

# Spring-Trade Pitfall Patterns

A living catalogue of bugs found and fixed in the spring-trade bot, with root causes and verified fix patterns. NOT a general development guide — use `spring-trade-bot` for architecture and normal workflows. Load this when debugging a regression or "button does nothing" report in the spring-trade bot.

## When to Use

- "There's a bug in the bot"
- "Button doesn't work / no response"
- "Message spawns duplicates"
- "Card preview disappeared"
- "Config change creates spam"
- "After upload the UI is messy"
- Any change to `editPhoto`, `a.edit`, `editOrSend`, `handlePhotoUpload`, `showCardSettings`, `showClaim`, `doClaim`

## Prerequisites

- Go 1.24+: `export PATH=/usr/local/go/bin:$PATH`
- Bot token + master key in `/root/spring-trade/.env`
- Source at `/root/spring-trade/`
- Binary built with `go build -o spring-trade ./cmd/bot`

## How to Run

Build and deploy through the `terminal` tool:

```bash
cd /root/spring-trade
export PATH=/usr/local/go/bin:$PATH
go build -o spring-trade ./cmd/bot
TOK=$(grep '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2-)
screen -dmS spring-trade bash -c "export TELEGRAM_BOT_TOKEN='$TOK'; cd /root/spring-trade; ./spring-trade 2>&1 | tee bot.log"
```

## Procedure

### 1. editPhoto fallback MUST update PreviewMsgID

**Symptom:** Card preview disappears; user sees only "🎨 PnL Card — lihat preview di bawah 👇" tombstone with no photo. Multiple duplicate card previews pile up on repeated config changes.

**Root cause:** `editPhoto` in `internal/tg/app.go` falls back to `sendPhoto` when `EditMessageMedia` fails (message deleted, not a photo, scrolled too far), but does NOT update `sess(userID).PreviewMsgID`. Next `showCardSettings` tries to `editPhoto` on the old (stale) `PreviewMsgID`, fails again, sends another new photo — cascade.

**Correct signature:** `func (a *App) editPhoto(ctx Context, chatID int64, userID int64, msgID int, png []byte, caption string, kb ReplyMarkup)`

**Fix:** When the fallback `sendPhoto` succeeds, set `a.sess(userID).PreviewMsgID = newID`.

```go
if err != nil {
    newID := a.sendPhoto(ctx, chatID, png, caption, kb)
    if newID != 0 {
        a.sess(userID).PreviewMsgID = newID
    }
}
```

**All callers** must pass `userID`: `a.editPhoto(ctx, chatID, userID, prevID, pngBytes, caption, kb)`.

### 2. a.edit() vs editOrSend() — NEVER mix their behaviors

**Symptom (a):** Clicking "🔄 Segarkan saldo" spawns a new home panel message every time.  
**Symptom (b):** Clicking gwei/slippage picker in the token card shows nothing — no picker appears.

**Root cause:** `a.edit()` and `editOrSend()` were conflated. `a.edit()` had a fallback to `a.send()` (causing symptom a). When that was removed to fix spam, `editOrSend()` — which calls `a.edit()` — lost ITS fallback too (causing symptom b). These are TWO DIFFERENT functions with different contracts.

**Correct behavior:**

| Function | Purpose | Fallback to `send`? |
|----------|---------|---------------------|
| `a.edit()` | In-place text update (refresh balance) | NO — silent on fail |
| `editOrSend()` | Menu navigation (gwei picker, token card) | YES — must show content |

**Implementation:** `a.edit()` stays without fallback. `editOrSend()` gets its OWN `EditMessageText` call with explicit fallback to `a.send()` — do NOT route through `a.edit()`.

```go
// CORRECT: editOrSend has its OWN EditMessageText + fallback
func (a *App) editOrSend(ctx context.Context, chatID int64, msgID int, text string, kb models.ReplyMarkup) {
    if msgID != 0 {
        _, err := a.Bot.EditMessageText(ctx, &bot.EditMessageTextParams{
            ChatID: chatID, MessageID: msgID, Text: text, ParseMode: htmlMode, ReplyMarkup: kb,
            LinkPreviewOptions: &models.LinkPreviewOptions{IsDisabled: ptr(true)},
        })
        if err == nil { return }
        // edit gagal → fallback KIRIM BARU (ini memang fungsinya "edit OR send")
    }
    a.send(ctx, chatID, text, kb)
}

// WRONG: routing through a.edit (no fallback → silent fail → "button does nothing")
func (a *App) editOrSend(ctx, chatID, msgID, text, kb) {
    if msgID != 0 {
        a.edit(ctx, chatID, msgID, text, kb)  // ← BUG: a.edit has no fallback
    } else {
        a.send(ctx, chatID, text, kb)
    }
}
```

**Verification:** After changing `editOrSend`, click "⛽ Gwei" in the token card. The picker MUST appear (even when the token card is a photo). If it doesn't appear, `editOrSend` is still routing through `a.edit`.

### 3. bg:upload MUST keep setPending("bgupload") even with showPicker

**Symptom:** After clicking "🖼 Upload" and sending a photo, user sees "💡 Kirim alamat token (CA) untuk panel beli/jual" — the photo falls through to the default handler.

**Root cause:** When `bg:upload` was refactored from `a.send()` to `showPicker()` (to enable auto-deletion), the `a.setPending(userID, "bgupload")` line was accidentally removed. `routeMessage` line 97 checks `s.Pending == "bgupload"` to route photos to `handlePhotoUpload`. Without it, the photo hits the default fallback.

**Fix:** Keep BOTH: `a.setPending(userID, "bgupload")` + `a.showPicker(...)`.

```go
case data == "bg:upload":
    a.setPending(userID, "bgupload")
    a.showPicker(ctx, chatID, userID, "🖼 Kirim satu foto...", [][]...)
```

### 4. handlePhotoUpload MUST delete the user's photo message

**Symptom:** After uploading a custom background, the user's original photo message remains in chat alongside the updated card preview.

**Root cause:** `handlePhotoUpload` only deleted the picker prompt (`dismissPicker`) but not the user's uploaded photo message. The photo's message ID was never passed to the handler.

**Fix:** Pass `update.Message.ID` from `dispatch.go` → `handlePhotoUpload`, then call `a.Bot.DeleteMessage(chatID, photoMsgID)` after processing. Delete in this order: user's photo FIRST, then dismissPicker, then showCardSettings. Use parallel goroutines for deletes (`context.WithoutCancel`) to keep the transition smooth.

```go
// dispatch.go — call site:
a.handlePhotoUpload(ctx, userID, chatID, update.Message.ID, update.Message.Photo)

// pnlcard.go — at end of handlePhotoUpload:
bgCtx := context.WithoutCancel(ctx)
go func() { a.Bot.DeleteMessage(bgCtx, &bot.DeleteMessageParams{...photoMsgID}) }()
go func() { /* dismiss picker */ }()
a.showCardSettings(ctx, chatID, userID) // don't wait
```

### 5. deleteBgFromGallery MUST decrement counter AND shift files

**Symptom:** Clicking 🗑️ on a gallery item shows the same gallery list again — the item appears undelieted.

**Root cause:** `deleteBgFromGallery` removed the file but did NOT decrement `KeyPnlBgNext`. `bgGalleryCount()` still returned the old count, so `showBgGallery` showed the same number of items.

**Fix:** Remove file, move the LAST gallery file into the deleted slot, decrement counter.

```go
func (a *App) deleteBgFromGallery(...) {
    total := a.nextBgNum(userID)
    // Remove slot N
    os.Remove(a.bgPathN(userID, n))
    // Shift: last → slot N
    last := total - 1
    if n < last {
        os.Rename(a.bgPathN(userID, last), a.bgPathN(userID, n))
    }
    // Decrement
    a.St.SetSetting(userID, usercfg.KeyPnlBgNext, strconv.Itoa(last))
    // Reset active if deleted
    ...
}
```

### 6. Photo messages CANNOT be edited into text

**Symptom:** "‹ Settings" and "🏠 Home" buttons in the PnL card inline keyboard do nothing when clicked.

**Root cause:** `navHome` and `navBack("settings")` are designed for TEXT messages. When clicked from a PHOTO message (the card preview), `showHome`/`showSettings` tries `EditMessageText` on a photo → fails → with the old `a.edit` fallback removed, nothing happens.

**Fix:** Use dedicated card-navigation callbacks that send NEW messages instead of editing the photo:

```go
case data == "card:back":
    a.showSettings(ctx, chatID, 0, userID)   // msgID=0 = send new
case data == "card:home":
    a.showHome(ctx, chatID, 0, userID, false) // msgID=0 = send new
```

All inline card keyboards MUST use `btn("🏠 Home", "card:home")` and `btn("‹ Settings", "card:back")` — never `navHome` or `navBack("settings")`.

### 7. claim:manual callback routes to input, NOT doClaim directly

**Symptom:** Clicking "➕ Claim Manual" shows "❌ Burn tidak ditemukan."

**Root cause:** The `claim:manual` callback ran `doClaim("manual")` directly, which tried `FindBurnByTx("manual")` — treating the literal string "manual" as a tx hash.

**Fix:** In the `claim:` handler, check `if burnTx == "manual"` FIRST, then route to `setPending("claimtx")` + prompt input — before the async `doClaim` call.

```go
case strings.HasPrefix(data, "claim:"):
    burnTx := strings.TrimPrefix(data, "claim:")
    if burnTx == "manual" {
        a.setPending(userID, "claimtx")
        a.send(ctx, chatID, "🔢 Kirim tx hash...", nil)
        return
    }
    go a.doClaim(...)
```

### 8. Inline keyboard UX replaces text pickers for card config

**Pattern:** Template/Font/Color/Bg config happens INLINE on the same photo message. Use `editCardKeyboard()` (calls `EditMessageReplyMarkup`) to change the keyboard without re-rendering the photo. Selection calls `showCardSettings()` which re-renders AND returns to the main 4-button keyboard.

```go
// Handler: show config inline
case data == "card:tmpl":
    a.editCardKeyboard(ctx, chatID, userID, a.cardTmplRows(userID))
//  → keyboard changes to [✅ Classic] [Compact] [Minimal] [Pro] + nav

// Handler: selection re-renders card
case strings.HasPrefix(data, "card:tmpl:"):
    a.St.SetSetting(userID, KeyPnlTemplate, value)
    a.showCardSettings(ctx, chatID, userID)
//  → photo re-renders with new template, keyboard returns to main 4 buttons
```

## Pitfalls

- **Stale binary is the #1 source of "feature not working" reports.** After any code change, ALWAYS rebuild AND restart. Two separate steps: `go build` first, verify `screen -ls`/`pgrep` second.
- **`pkill -9` can kill the terminal shell.** Use two separate `terminal` calls: one to kill, then verify dead, then start the new screen. Or separate with `|| true`.
- **`GetSetting` returns 3 values** `(string, bool, error)` — never assign to 2 vars.
- **Hermes agent's TELEGRAM_BOT_TOKEN leaks** into screen sessions. Always extract token explicitly from `/root/spring-trade/.env` before starting the bot.
- **Never start two instances.** Telegram only allows ONE active `getUpdates` per bot token. Two instances trigger `Conflict: terminated by other getUpdates request` and both fail.
- **`a.edit()` now has NO fallback.** Do not use it for menu navigation. Use `editOrSend()` when the content MUST appear.

## Verification

```bash
cd /root/spring-trade && export PATH=/usr/local/go/bin:$PATH
go build -o spring-trade ./cmd/bot && echo "BUILD OK"
go test ./... | grep -E "^(ok|FAIL)"
screen -ls  # must show exactly 1 spring-trade screen
pgrep -fa './spring-trade' | grep -v bash | wc -l  # must be 1
grep -c Conflict bot.log  # must be 0
```
