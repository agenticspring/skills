---
name: spring-trade-bot
description: Build, audit, and extend <HANDLE_REDACTED>'s spring-trade Go trading bot (Telegram UI + ARC/NOXA trading + CCTP bridge). Covers PnL card rendering, live-preview config UX, and the discuss-first workflow the user requires. Load this for ANY task touching /root/spring-trade (card rendering, settings UI, trade/sell logic, bridge).
---

# spring-trade-bot

Go trading bot for <HANDLE_REDACTED>. Repo: `github.com/<HANDLE_REDACTED>/spring-trade` (private). Source at `/root/spring-trade/`.
Binary `spring-trade`, DB `spring-trade.db`, runs in `screen -S spring-trade`. Telegram bot `@Eloncolibot`.

## Architecture (high level)
- `cmd/bot` — entrypoint.
- `internal/card` — PnL card PNG renderer (fogleman/gg, 1536×864). **No vision on the agent model — verify layouts by math, not by looking.**
- `internal/tg` — Telegram handlers, settings menus, callbacks.
- `internal/trade` — swap/quote/NOXA token logic.
- `internal/usercfg` — per-user settings (`Cfg` struct + `Key*` constants + `Load`).
- `internal/store` — SQLite positions/settings.

## PnL Card subsystem (most active area)
Render entry: `card.Render(PnLData, presetKey, bgImg, Template, FontType, colorTheme)`.
- 4 templates: `classic`, `compact`, `minimal`, `pro`.
- 6 color themes: `default`, `neon`, `gold`, `ice`, `hacker`, `white` (map `card.ColorThemes`).
- 3 fonts: `bold`, `regular`, `mono`.
- 6 bg presets `bg1..bg6` + custom uploaded PNG per user (`bgPath`).

### Live-preview config UX (REQUIRED pattern)
User rule: when changing a card config (template/font/color/bg), the result must be **immediately visible** — do NOT hide it behind a separate "Preview" button. AND it must be **smooth / non-spammy**: never spawn a new message on every config change.

**Anti-spam rule (HARD, from a user correction):** changing config must EDIT the existing preview photo in place — NOT send a new photo + new text picker each time. The original design did `editOrSend`/new-photo on every setter and the picker reused `editOrSend`, which failed on a photo message and silently spawned new messages → the chat filled with duplicate cards/buttons. Fix = message recycling via session-tracked IDs.

Implementation pattern (current, correct — `pnlcard.go` + `app.go`):
- `Session` struct carries `PreviewMsgID int` (the live card photo) and `PickerMsgID int` (the transient text picker). Both default 0.
- `showCardSettings(ctx, chatID, userID)` (NOTE: no `msgID` arg) re-renders the card and:
  - if `sess.PreviewMsgID == 0` → `sendPhoto` (new), store the returned ID;
  - else → `editPhoto(ctx, chatID, PreviewMsgID, …)` (in-place update, no new message).
- `editPhoto` uses `bot.EditMessageMedia` with `models.InputMediaPhoto{Media:"attach://preview.png", MediaAttachment: bytes.NewReader(png)}`; `sendPhoto` returns `msg.ID` for tracking.
- Picker sub-menus (Template/Font/Color/Background) go through `showPicker(ctx, chatID, userID, text, rows)` which RECYCLES `sess.PickerMsgID` (edit the same text message; only send new if ID==0 or the edit errors). Never call `editOrSend` on a photo message.
- Every setter callback (`card:tmpl:*`, `card:font:*`, `card:color:*`, `bg:set:*`, `bg:reset`) does: set setting → `dismissPicker(ctx, chatID, userID)` (deletes the picker text via `DeleteMessage`, resets `PickerMsgID=0`) → `showCardSettings(ctx, chatID, userID)` (edits the SAME photo). Result: picker vanishes, photo updates, zero new messages.
- `handlePhotoUpload` after saving does USER'S PHOTO FIRST, then dismiss picker, then show card. **Order matters (user correction):** `a.Bot.DeleteMessage(chatID, photoMsgID)` FIRST → `dismissPicker` → `showCardSettings`. User sees their photo disappear, then the card updates — clean transition. Incorrect order (dismiss first) causes visual jump. Signature: `handlePhotoUpload(ctx, userID, chatID, photoMsgID int, photo []models.PhotoSize)`. The `photoMsgID` comes from `update.Message.ID` at the call site in `dispatch.go`.
- `card:settings` from the main settings menu: edit the old text message into a one-line tombstone ("lihat preview di bawah 👇"), then `showCardSettings` (first time sends a new photo, subsequent times edits it).
- `sendCardPreview` (`bg:preview`) is the ONE explicit "send a fresh photo" path; it sets `PreviewMsgID` so later edits target it.
- **`bg:upload` MUST use `showPicker`, NOT `a.send`, AND must keep `setPending("bgupload")`.** Two bugs hit this in one session: (a) switching from `a.send` to `showPicker` accidentally dropped the `setPending("bgupload")` line — this caused uploaded photos to bypass `handlePhotoUpload` entirely and fall through to the default "💡 Kirim alamat token..." handler. (b) `handlePhotoUpload` only deleted the picker prompt but NOT the user's original photo message → the photo lingered in chat. Fix: pass `photoMsgID` (from `update.Message.ID`) to `handlePhotoUpload`, call `a.Bot.DeleteMessage(chatID, photoMsgID)` after saving. The final clean state after bg upload is: ONLY the updated preview card visible. The upload prompt (tracked via `PickerMsgID`) auto-deletes via `dismissPicker`, and the user's photo is explicitly deleted.

Keep this pattern for any new card config option. If you add a new setting, wire its setter the same way (dismiss picker → edit same photo). Any message that should disappear after a user action MUST go through `showPicker` (not `a.send`) so it's tracked and deletable.

### Custom Background Gallery
User requested: "tambahkan tempat penyimpanan custom foto background yg udah di add user. Jadi nanti user bisa gampang pilihnya."

Each uploaded background is saved to BOTH the active slot AND a numbered gallery slot:
- `bgPath(userID)` → `data/bg/{userID}.png` — active background (always overwritten on upload)
- `bgPathN(userID, n)` → `data/bg/{userID}_{n}.png` — gallery slot N (0-based, never overwritten)
- `KeyPnlBgNext` tracks the next gallery index (stored as integer string setting, starts at 0, incremented per upload)
- `loadBackground(userID, presetKey)` — supports `"custom"` (active file) and `"custom:N"` (gallery slot N)
- `showBgGallery(ctx, chatID, userID)` — lists all saved backgrounds as `[📸 BG #1]` … `[📸 BG #N]` buttons with ✅ for currently active. Each button sets `bg:set:custom:N`.
- `showBackgroundMenu` shows `📂 My Gallery (N)` button only when `bgGalleryCount(userID) > 0`
- `handleBgCallback` routes `bg:gallery` → `showBgGallery`
- `usercfg.KeyPnlBgNext` constant added to `usercfg.go`

Note: `GetSetting` returns 3 values `(string, bool, error)` — don't assign to 2 vars.

### Layout audit workflow (no vision available)
When the user asks to "audit" a card or you change layout:
1. Write a temporary `*_test.go` in `internal/card` that calls `Render` for each template × theme (incl. extreme/negative values) and `os.WriteFile`s PNGs to `/tmp/cardcheck/`.
2. Run it, then verify **mathematically**: for each element compute `x + approxWidth` (≈ `len(text) * fontSize * 0.6`) and `y + height`; assert ≤ 1536 / 864 and no two boxes intersect. The agent model (hy3:free) has NO vision — do not call `vision_analyze` on the PNGs, it returns "no vision support".
3. Delete the temp test before commit unless it adds lasting value.

### Long-running callback actions (bridge claim, etc.) — async + feedback pattern
When a button triggers work that takes >2s (network poll, on-chain tx), NEVER call it synchronously inside `routeCallback`/`handle*Callback`. The symptom the user hit: clicking "♻️ Klaim" appeared to do nothing — the callback was answered (spinner gone) but `doClaim` blocked the handler for 10–30s before any message appeared, and a second click double-fired.

Correct pattern (see `references/claim_flow.md`):
1. In the callback handler, `a.answer(ctx, cq.ID, "⏳ Memproses…")` immediately (toast), then `go a.doClaim(context.WithoutCancel(ctx), userID, chatID, arg)`. Use `context.WithoutCancel` so the request context dying doesn't kill the goroutine.
2. `doClaim` sends a progress message at EVERY step (`Mengecek attestation…` → `Attestation siap, kirim tx` → `⛽ Menunggu konfirmasi` → `✅ Berhasil (tx hash)`). Each step is a separate `a.send` so the user always sees motion.
3. **Reentrancy guard:** `App.claimMu sync.Mutex` + `claiming map[string]bool` (keyed by burnTx). At start, if `claiming[burnTx]` is true → send "sedang diproses" and return; otherwise set true + `defer delete`. Prevents double-submit / wasted gas.
4. **Crash safety:** wrap the goroutine body in `defer func(){ if r:=recover(); r!=nil { a.send(...,"❌ Klaim crash: %v",...) } }()` so a panic still tells the user instead of going silent.
5. Handle `FindBurnByTx` returning `(nil, nil)` explicitly (not `err != nil || b == nil` in one branch) so a DB error is reported distinctly from "not found".

### Debugging "silent button / no message" reports
When the user says a button did nothing, do NOT assume the code is broken. Build a throwaway
`cmd/<name>/main.go` that constructs the real `App` and calls the handler directly with
`log.Printf` at every `a.send`, run it with env from `~/.hermes/.env`, and curl the upstream API
(Iris `/v2/messages/{domain}?transactionHash=...`) to see the true status. One session's
"claim does nothing" was actually a correct "pending_confirmations" message the user ignored.
Full recipe in `references/debug_button_silent.md`.

### Inline Keyboard UX (current, preferred — replaces text pickers)

**User directive:** "gua mau improve... user pencet misal template nanti langsung di arahkan ke confignya. jadi tombol template, background, font, color akan hilang di gantikan tombol config template. tapi ingat gambar pnl card kan tetap akan ada."

Config submenus now edit the SAME photo's inline keyboard — no text pickers. The photo stays visible, only the buttons change.

Implementation (`pnlcard.go`):
- `editCardKeyboard(ctx, chatID, userID, rows)` — calls `bot.EditMessageReplyMarkup` on `sess(userID).PreviewMsgID`. Edits ONLY the keyboard, photo + caption unchanged. Returns immediately if `PreviewMsgID == 0`.
- Main card keyboard: `[📐 Template] [🖼 Background]` / `[🔤 Font] [🎨 Color]` / `[← Settings] [🏠 Home]`
- Template submenu: `[✅ Classic] [Compact] [Minimal] [Pro]` / `[‹ Card Settings] [🏠 Home]` — selection saves setting + calls `showCardSettings` (re-renders card, returns to main keyboard)
- Font submenu: `[✅ Bold] [Regular] [Mono]` / `[‹ Card Settings] [🏠 Home]`
- Color submenu: 2 rows of 3 themes each with checkmark / `[‹ Card Settings] [🏠 Home]`
- Background submenu: `[bg1]-[bg6]` / `[🖼 Upload] [📂 Gallery]` / `[↺ Reset]` / `[‹ Card Settings] [🏠 Home]`
- `card:bg` callback → `editCardKeyboard` to bg rows. Background upload + gallery still use pickers (need text input). `bg:set:` and `bg:reset:` now call `showCardSettings` directly (inline pattern).
- This eliminates ALL text pickers for Template/Font/Color/Background presets. Only bg upload prompt + gallery list remain as text pickers.
- **Visual:** photo stays in place, keyboard transitions are instant. No new messages spawned. User sees live card preview while browsing config options.

**Navigasi dari foto harus pakai `card:back`/`card:home` — `navHome`/`navBack("settings")` GAGAL.** Ketika keyboard foto inline mencoba navigate via `navHome` (callback `"main"`) atau `navBack("settings")`, handler `showHome`/`showSettings` dipanggil dengan `msgID` dari foto. Mereka mencoba `a.edit()` (EditMessageText) ke PESAN FOTO → gagal silent (karena `a.edit()` sudah tidak fallback ke send). Hasil: tombol tidak bereaksi — user klik tapi tidak terjadi apa-apa. Fix: buat handler `card:back` (panggil `showSettings(ctx, chatID, 0, userID)`) dan `card:home` (panggil `showHome(ctx, chatID, 0, userID, false)`) — keduanya kirim PESAN BARU karena foto tidak bisa diedit jadi teks. **SEMUA** inline keyboard rows (cardTmplRows, cardFontRows, cardColorRows, showBgInlineRows, dan showCardSettings main) harus pakai `btn("🏠 Home", "card:home")` dan `btn("‹ Settings/Card Settings", "card:back"/"card:settings")`, bukan `navHome`/`navBack`.

**Button audit checklist:** `references/button_audit.md` — complete callback→handler mapping, dispatch flow diagram, dan checklist untuk verifikasi semua tombol. Load ini sebelum melakukan full button audit.

### Critical Pitfalls: editPhoto fallback and a.edit() spam

- **Correct editPhoto signature:** `func (a *App) editPhoto(ctx Context, chatID int64, userID int64, msgID int, png []byte, caption string, kb ReplyMarkup)`. When `EditMessageMedia` fails (msg deleted, not a photo), the fallback to `sendPhoto` MUST update `sess(userID).PreviewMsgID = newID`. Without this, `showCardSettings` keeps trying to edit the old (deleted) msgID → fails silently → sends yet another new photo → **cascade of duplicate card previews**. User symptom: "🎨 PnL Card — lihat preview di bawah" tombstone appears alone, no photo, or multiple duplicate photos pile up. This also fixes the `/start` → Settings → PnL Card bug.
- **`a.edit()` MUST NEVER fallback to `a.send()`.** When `EditMessageText` fails, the old fallback silently sent a NEW text message. This caused spam on every "Segarkan saldo" click. Fix: remove fallback, log error instead.
- **`editOrSend()` MUST do its OWN `EditMessageText` + fallback — NOT delegate to `a.edit()`.** After `a.edit()` was stripped of its fallback, `editOrSend()` (in `wallet.go`) broke because it was calling `a.edit()`. When user clicked gwei/tslip picker from a photo message, the edit failed silently and no picker appeared. Fix: `editOrSend` now does its own `a.Bot.EditMessageText()` call and falls back to `a.send()` on failure. The two functions serve different purposes: `a.edit()` = pure-in-place-edit (for refresh/update scenarios where spam is worse than silence), `editOrSend()` = navigate-or-create (for menu transitions where showing something is mandatory).
- **Gallery delete with shift:** `deleteBgFromGallery` must (1) remove file slot N, (2) move last file into slot N, (3) decrement `KeyPnlBgNext`. Without shift+decrement, counter stays unchanged → gallery shows same stale items (bug: "tiap pencet tong sampah balik lagi").
- **Parallel deletes for smooth transitions:** After bg upload, delete user photo + dismiss picker in parallel goroutines (`context.WithoutCancel`). Call `showCardSettings` immediately — don't wait.

### NFT card UX — reference-first scope
When the user asks for a new NFT surface that should resemble the existing Spring Trade token card, do not begin with the full transaction lifecycle. Ship the short vertical slice first:

For an isolated Telegram review, use `references/nft-review-runtime.md`: a dedicated bot identity, explicit reviewer allowlist, public wallet labels only, `read_only`/`signer=false`/`broadcaster=false`, a clearly labeled test-only eligibility override, startup verification, and token rotation after review if the token was exposed.

1. Accept a pasted NFT contract or OpenSea asset URL.
2. Resolve/read a compact NFT snapshot: collection/name, token ID, chain, contract, floor/best listing, and observation time.
3. Evaluate the configured wallet set and keep only wallets whose eligibility is explicit and current.
4. Render `BUY` only when at least one wallet is eligible; render no BUY keyboard when zero wallets qualify.
5. On BUY, edit the existing card into wallet-label buttons such as `Phrase 1`/`Phrase 2`; these are display labels only, never seed phrases or signer material.
6. On wallet selection, show a concise preparation preview. Do not call a signer, broadcaster, or execution adapter from the eligibility UI.

Keep the first implementation visually and operationally similar to the reference token card. Do not make the user read the entire safety model before seeing the NFT information. Preserve the safety boundary in code: the compact UI may be simple, but any later execution must re-enter the durable intent, policy, journal, pause/kill-switch, and reconciliation pipeline. Callback action IDs may contain wallet-label separators such as `-`; validate them with a bounded allowlist and test the parser. Recycle/edit the current message where possible instead of spawning a message per button transition. See `references/nft-card-ux.md` for the exact view/callback contract.

### Collection URL and natural-paste workflow

For Spring Trade-style NFT review, treat user text as the primary entry point: accept a bare EVM CA, OpenSea asset URL, or OpenSea collection URL without requiring `/nft`. Normalize to an explicit target kind (`contract`, `asset`, or `collection`) before lookup. A collection lookup must not fail just because inventory is empty or sold out: keep collection name, contract/chain, total supply, minted or unique count, sold-out status, floor, payment currency, and listing count when available. Render colored compact action rows only when the relevant evidence exists: `BUY` for eligible wallet + current listing, `SWEEP FLOOR` for eligible wallet + current collection listings; otherwise omit the action button and keep the information card.

Register command prefixes through Telegram `setMyCommands` (`/start`, `/nft`, `/status`, `/help`) for discoverability, but also handle natural pasted CA/URL text. The natural-text handler must ignore unrelated text and slash commands, edit a loading message in place, and surface lookup errors without spawning duplicate messages. Test the parser, sold-out fallback, action visibility, compact keyboard row layout, command registration, and a real read-only API fixture. Keep BUY/SWEEP callbacks in preparation-only UI until they explicitly re-enter the execution boundary.

### Original pitfalls (still active)
- **ONE language only.** User explicitly rejected mixed Indonesian/English labels ("Kenapa ada double bahasa? Pake salah 1 aja"). Card UI text is **English** (Invested/Now/Entry/Current/MCap/Hold). Code comments may stay Indonesian; user-facing card strings must be English.
- **No spam on config change (HARD).** User: "Kenapa ketika habis edit config selalu spawn tombol lagi di bawahnya? Buat lebih smooth tidak spam." The live-preview must EDIT the same photo in place — track `Session.PreviewMsgID` + `PickerMsgID`, recycle via `editPhoto`/`showPicker`, and `dismissPicker` (DeleteMessage) the picker after a choice. NEVER use a naive `editOrSend`/`sendPhoto` per setter — editing text onto a photo message fails silently and spawns duplicates. Re-using the wrong message type (text-edit on a photo, or photo-edit on text) is the root cause of the spam.
- **Compact/Minimal/Pro were redesigned** because the original layouts overlapped (stats grid ran off the panel, triangle/PnL collided). Current safe layout: Compact = PnL top + 2-col grid below; Minimal = centered single column; Pro = header bar + PnL left + 2-col detail grid right + vertical split line. Keep spacing explicit.

## Build / test / deploy
- Go 1.24. `export PATH=/usr/local/go/bin:$PATH` (PEP 668 env, no system go on PATH).
- Build: `go build -o spring-trade ./cmd/bot`. Test: `go test ./...`.
- **NEVER run two instances.** Telegram allows only ONE active `getUpdates` per bot token. A second instance triggers `Conflict: terminated by other getUpdates request` and BOTH die.
- **pkill can kill the parent shell.** Running `pkill -9 -f './spring-trade'` on the same command line as other commands (e.g. `pkill -9 ...; screen -dmS ...`) kills the terminal session if it matches the process pattern. Use TWO separate terminal calls: first `pkill`, then verify process is dead, THEN start the new screen. Or separate with `|| true` to prevent the whole script from dying.
- **Rebuild before restart — stale binary is the #1 source of "feature not working" reports.** User reported `/iris` non-functional and claim having no feedback — both were correct in source but the running binary was from a prior commit. After ANY code patch, ALWAYS: `go build -o spring-trade ./cmd/bot` BEFORE starting the bot. Never assume the on-disk binary matches the source.
- **Environment & Token Isolation (CRITICAL — learned the hard way in this session)**: Screen sessions inherit the Hermes agent's `TELEGRAM_BOT_TOKEN`. The project's `./.env` (89674962...BJEU for @Eloncolibot) is ignored if the var is already set in the parent environment. This caused the bot to respond as the Hermes bot instead of the spring-trade bot, leading to "Lo salah pake bot tele besti" and "Gua run sendiri aja".
  **Correct start command (guaranteed project token):**
  ```bash
  cd /root/spring-trade
  pkill -9 -f './spring-trade'
  screen -S spring-trade -X quit 2>/dev/null
  screen -wipe
  TOK=$(grep '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2-)
  KEY=$(grep '^MASTER_ENCRYPTION_KEY=' .env | cut -d= -f2-)
  screen -dmS spring-trade bash -c "
    export TELEGRAM_BOT_TOKEN='$TOK'
    export MASTER_ENCRYPTION_KEY='$KEY'
    cd /root/spring-trade
    exec ./spring-trade 2>&1 | tee bot.log
  "
  sleep 3
  pgrep -fa './spring-trade' | grep -v bash   # must show exactly 1 binary
  grep -c Conflict bot.log                    # must be 0
  ```
  Always verify the token in the process environment (`tr '\0' '\n' < /proc/PID/environ | grep TELEGRAM_BOT_TOKEN`). See `references/env_isolation.md` for full diagnosis and alternatives (unset + source, env -i, etc.).
- **"1 aja yg update terbarunya"** — always `git pull` or build from latest commit before starting. Never run stale binary.
- **Safe editing workflow (learned from repeated broken edits)**: Before major edits to `bridge.go`, `callbacks.go`, or `pnlcard.go`, run `git checkout -- file`. Use small targeted `patch` for one function at a time. Build immediately. If syntax broken ("tcase", duplicate case, unexpected name context), restore immediately with `git checkout -- file`. Never chain multiple sed commands in one turn — they compound errors. Restore from git is the first step, not the last resort.
- Commit only when user says so (memory: "NEVER commit without explicit command").

## Claim / Bridge Resume (manuale input tx hash — user redesign)

**User directive (HARD):** "Edit fitur claim jadi manual aja. Jadi user harus input tx hash." The claim feature is now **100% manual input** — no list of pending burns, no per-burn buttons, no "Claim Manual" sub-button. Every claim path routes the user to paste a tx hash.

**Current UX:**
- Clicking **♻️ Klaim** (button or `/claim` command) → `showClaim` prompts "Kirim tx hash burn yang mau diklaim" + sets pending `"claimtx"`. Shows pending count as info only ("📋 X burn pending di database").
- User pastes tx hash → validated (must start 0x, min 66 chars) → `go a.doClaim(context.Background(), …)` async.
- `/claim` command → same as above. Registered in `SetMyCommands`.
- `/iris <txhash>` → `showIrisStatus()` scans all 6 CCTP domains (ETH, AVAX, OP, ARB, BASE, POL). Found: status emoji + chain + ready/minted + attestation hex. Not found: "Tx tidak ditemukan di Iris".
- **Bridge keyboard** has `[🔍 Cek Iris]` button (`bridge:iris` callback) — sets pending `"iristx"`, user pastes tx → `showIrisStatus`.

**doClaim flow (async + progress + guard + userID filter):**
- Immediate toast via callback answer.
- Reentrancy guard per burnTx (`claiming` map).
- Recover panic → send error message.
- `FindBurnByTx` (supports any tx), then **userID guard**: if `b.UserID != userID` → "Burn ini milik user lain — hanya pemilik wallet yg bisa klaim".
- `GetAttestationOnce` → if `AlreadyMinted` mark completed; if `!Ready` give clear "pending_confirmations + age + hint" (hint changes if burn >10 min old: "rute forwarding kemungkinan sedang gangguan").
- If ready → `SubmitReceiveMessage` on Arc, `MarkCompleted`, send tx link.

**Key files:**
- `internal/tg/bridge.go`: `showClaim`, `doClaim`, `showIrisStatus`
- `internal/tg/callbacks.go`: `claim`/`claim:`/`bridge:iris` handlers; `pending == "claimtx"`/`"iristx"` in `handlePendingExtra`
- `internal/tg/dispatch.go`: `/claim`, `/iris` command handlers
- `internal/tg/keyboard.go`: `bridgeMenu` has `[🔍 Cek Iris]` and `[♻️ Klaim]`
- `internal/tg/app.go`: `SetMyCommands` includes `/claim` and `/iris`

**Pitfalls (updated):**
- **Claim flow must be 100% manual.** User explicitly removed the list-based claim UX. `showClaim` must NOT render per-burn buttons or `"claim:manual"` sub-button — just prompt + set pending. Do NOT reintroduce list-based claim.
- **Stale binary = features disappear (HARD).** User reported `/iris` "gak gabisa dipake" and claim "gak ada notifikasi." Both were correct in source but missing from the running binary because `go build` was not run after the last patch. After EVERY code change (especially adding new commands, callbacks, or handlers), ALWAYS rebuild AND restart the bot. Never assume the running binary matches source.
- **Token isolation (HARD).** Hermes agent's `TELEGRAM_BOT_TOKEN` leaks into screen sessions. Always extract from `./.env` and export explicitly before starting the bot. See `references/env_isolation.md`.
- **UserID guard in doClaim.** User requested "hanya user yg punya wallet yg bisa claim."
- **No debug `log.Printf`.** Production code must not contain debug logging; always remove before commit.
- **Safe editing:** before editing `bridge.go`/`callbacks.go` with sed, `git checkout -- file` first. Build immediately after every change. If syntax is broken, restore from git — do not chain more sed fixes.

## References
- `references/erc20_metadata_reliability.md` — strict-TDD pattern for distinguishing RPC errors from empty ERC20 metadata, bounded retry/recovery, all-or-nothing cache insertion, configured RPC fallback ownership, shared-worktree integrity, and focused race/ad-hoc verification.
- `references/position_accounting.md` — strict-TDD invariants for numeric parsing, transferred-inventory sell attribution, cumulative lifecycle PnL, wallet-filtered cost basis, caller integration, and targeted ad-hoc verification.
- `references/pnl_renderer_performance.md` — profile and optimize Go/fogleman-gg PnL renderers: pre-render gradients, direct-copy same-size images, normalize/cache custom backgrounds, fast PNG, race-safe font-face handling, render backpressure, Studio debounce, and bounded preview caching.
- `references/token_scan_performance.md` — benchmark and optimize slow token-card scans: eliminate duplicate detection, cache static metadata, parallelize factory/metrics/wallet RPCs, and add stage latency logs.
- `references/button_audit.md` — complete callback→handler matrix, dispatch flow diagram, dan audit checklist. Load before full bot button audit.
- `references/bg_gallery.md` — custom background gallery: storage layout, loadBackground with "custom:N" keys, showBgGallery menu, KeyPnlBgNext counter, and pitfall about GetSetting returning 3 values.
- `references/card_layout.md` — per-template coordinate map + bounds checklist used during the Compact/Minimal/Pro redesign.
- `references/claim_flow.md` — bridge claim async pattern (updated with manual tx input and wallet display).
- `references/iris_command.md` — full implementation recipe for `/iris <txhash>`: dispatch, pending handler, `showIrisStatus` domain-scanning function.
- `references/debug_button_silent.md` — how to prove a "button does nothing" report: throwaway cmd + log.Printf + curl upstream, with the exact `App` construction snippet.
- `references/iris_claim_status.md` — CCTP/Iris `/v2/messages` endpoint, `status` enum (`pending_confirmations` etc.), and the "burn valid but route stuck" diagnosis that looks like a dead button.
- `references/env_isolation.md` — exact commands to guarantee the project's `./.env` token is used (new, added in this session after repeated "wrong bot" reports).
