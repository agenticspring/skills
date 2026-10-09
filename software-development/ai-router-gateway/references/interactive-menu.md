# 9Router interactive menu — implementation reference

Reverse-engineered from `/usr/lib/node_modules/9router/src/cli/utils/input.js` (`selectMenu`) and `cli.js` (`showInterfaceMenu`). Go port lives in `spring-router/menu.go`.

## Behavior

- `selectMenu(title, items, defaultIndex, subtitle)` returns selected index; `-1` if stdin not a TTY.
- Render on every keystroke: `\x1b[2J\x1b[H` (clear+home), then:
  - `\n` + terracotta `=` × width(40) separator
  - `  <bright><terracotta>title</reset>`
  - `  <dim>subtitle</reset>` (e.g. `🚀 Server: <green>http://localhost:PORT</reset>`)
  - terracotta `=` separator
  - blank line, then items: selected = ` <reverse><bright>★ label</reset>`, unselected = `  ☆ label`
- Colors: terracotta `\x1b[38;2;217;119;87m`, reverse `\x1b[7m`, bright `\x1b[1m`, dim `\x1b[2m`, green `\x1b[32m`.
- Icons: `★` selected, `☆` unselected (Windows fallback `>`/` `).

## Key handling (Go, golang.org/x/term raw mode)

```go
oldState, _ := term.MakeRaw(int(os.Stdin.Fd()))
defer term.Restore(int(os.Stdin.Fd()), oldState)

buf := make([]byte, 3)
for {
    n, _ := os.Stdin.Read(buf)
    key := buf[:n]
    switch {
    case key[0] == 3:            // Ctrl+C
        return -2
    case key[0] == 13 || key[0] == 10: // Enter
        return selected
    case key[0] == 27 && n >= 3 && key[1] == 91:
        switch key[2] {
        case 65: selected--      // up
        case 66: selected++      // down
        }
    case key[0] == 113:          // q
        return -2
    case key[0] >= 49 && key[0] <= 57: // 1-9 quick select
        return int(key[0] - 49)
    }
}
```

## Menu flow (spring-router)

- Entry: `spring-router` with NO subcommand AND stdin is TTY → `runMenu`.
- Server starts in background FIRST (pidfile + health poll), then menu renders.
- Items: Web UI (open browser), Terminal UI (interactive chat REPL — placeholder), Hide to Background, Exit.
- Not a TTY (e.g. cron/systemd) → skip menu, print "running" and let the server run.

## 9Router parity notes

- 9Router shows `★ Update to vX.Y.Z (current: vX.Y.Z)` as first item when an update exists — shifts item indices by 1 (handled with an offset).
- 9Router keeps raw mode on for the whole TUI session (prime-once) to avoid macOS latency; suspend raw mode only for line-input prompts.
- Use `readline.emitKeypressEvents` + raw data fallback on macOS to prevent arrow-key escape leakage.
