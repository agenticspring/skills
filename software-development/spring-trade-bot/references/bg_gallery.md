# Custom Background Gallery — Implementation Reference

## User request
"tambahkan tempat penyimpanan custom foto background yg udah di add user. Jadi nanti user bisa gampang pilihnya."

## Architecture

### Storage
- `data/bg/{userID}.png` — active background (always overwritten on upload)
- `data/bg/{userID}_{0}.png`, `_{1}.png`, ... — gallery slots (never overwritten, append-only)
- `usercfg.KeyPnlBgNext = "PNL_BG_NEXT"` — tracks next gallery index (int stored as string)

### Key functions (all in `internal/tg/pnlcard.go`)

```go
// Active background path
func (a *App) bgPath(userID int64) string {
    return filepath.Join(a.Cfg.DataDir, "bg", fmt.Sprintf("%d.png", userID))
}

// Gallery slot N
func (a *App) bgPathN(userID int64, n int) string {
    return filepath.Join(a.Cfg.DataDir, "bg", fmt.Sprintf("%d_%d.png", userID, n))
}

// Read next gallery index
func (a *App) nextBgNum(userID int64) int {
    v, ok, _ := a.St.GetSetting(userID, usercfg.KeyPnlBgNext)
    if !ok { return 0 }
    n, err := strconv.Atoi(v)
    if err != nil || n < 0 { return 0 }
    return n
}

// Total saved backgrounds (same as next index since 0-based)
func (a *App) bgGalleryCount(userID int64) int {
    return a.nextBgNum(userID)
}
```

### Upload flow (in `handlePhotoUpload`)
```go
// Save to active slot
out, _ := os.Create(a.bgPath(userID))
png.Encode(out, img)
out.Close()

// Save to gallery slot
nextN := a.nextBgNum(userID)
galleryOut, _ := os.Create(a.bgPathN(userID, nextN))
png.Encode(galleryOut, img)
galleryOut.Close()
a.St.SetSetting(userID, usercfg.KeyPnlBgNext, strconv.Itoa(nextN+1))

// Then: delete user photo → dismiss picker → show card
```

### Background loading (modified `loadBackground`)
```go
func (a *App) loadBackground(userID int64, presetKey string) image.Image {
    if presetKey == "" || !strings.HasPrefix(presetKey, "custom") {
        return nil
    }
    var path string
    if presetKey == "custom" {
        path = a.bgPath(userID)                       // active
    } else {
        n, _ := strconv.Atoi(strings.TrimPrefix(presetKey, "custom:"))
        path = a.bgPathN(userID, n)                   // gallery slot
    }
    data, _ := os.ReadFile(path)
    img, _, _ := image.Decode(bytes.NewReader(data))
    return img
}
```

### Gallery menu (`showBgGallery`)
```go
func (a *App) showBgGallery(ctx context.Context, chatID int64, userID int64) {
    total := a.bgGalleryCount(userID)
    cur := a.curVal(userID, usercfg.KeyPnlBg)
    var rows [][]models.InlineKeyboardButton
    for i := 0; i < total; i++ {
        label := fmt.Sprintf("📸 BG #%d", i+1)
        if cur == fmt.Sprintf("custom:%d", i) { label = "✅ " + label }
        rows = append(rows, row(btn(label, "bg:set:custom:"+strconv.Itoa(i))))
    }
    rows = append(rows, row(navBack("settings:bg"), navHome))
    a.showPicker(ctx, chatID, userID,
        fmt.Sprintf("<b>📂 My Gallery</b>\n%d background tersimpan.", total), rows)
}
```

### Settings key
```go
// In internal/usercfg/usercfg.go
const KeyPnlBgNext = "PNL_BG_NEXT"
```

### Callback routing
- `bg:gallery` → `showBgGallery(ctx, chatID, userID)` (added in `handleBgCallback`)
- `bg:set:custom:0`, `bg:set:custom:1`, ... → sets `KeyPnlBg` to `"custom:N"` → `dismissPicker` → `showCardSettings`

### Pitfalls
- `GetSetting` returns `(string, bool, error)` — 3 values, not 2. Assign all three or use `GetSettingOr`.
- Gallery index is 0-based; display labels should be 1-based (`BG #1`, `BG #2`).
- `showBgGallery` must fall back to `showBackgroundMenu` if `total == 0` (edge case: settings desync).
