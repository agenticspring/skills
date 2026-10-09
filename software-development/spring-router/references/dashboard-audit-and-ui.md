# Dashboard audit and UI rebuild reference

## 9Router live audit (Chromium, read-only)

Target: `http://127.0.0.1:20128/dashboard`. The 9Router process was left running; no restart, kill, database write, or settings mutation was performed.

Authenticated shell observed:

- Light cream background with pale grid.
- Coral/orange brand accent and blue-gray text.
- Rounded white cards and a persistent left navigation shell.
- Main navigation: Endpoint & Key, Providers, Combos, Usage, Quota Tracker, Token Saver, CLI Tools.
- System navigation: Media Providers, Proxy Pools, Skills, Console Log, 9Remote, 9English, Settings.
- Global controls included dark mode, language, compact/grid control, and update notice.

Feature findings:

- Providers are grouped into custom, OAuth, free-tier, and API-key providers. Cards show connection states and counts, plus search, add compatible provider, and Test All actions.
- Combos support Fallback, Round Robin, Fusion (parallel models plus judge; N+1 calls), and capacity auto-switch for media-capable requests.
- Endpoint & Key contains local endpoint, tunnel/Tailscale controls, API-key creation/list/copy/delete, and a Require API key toggle.
- Quota Tracker has provider/account filters, active/off/expiring filters, auto-refresh, per-connection quota actions, and pagination.
- Token Saver exposes RTK/tool-output compression, Headroom, prompt compression, and output compression modes.
- CLI Tools exposes configuration cards for Claude Code, Codex, OpenCode, Hermes, Cursor, Cline, and other clients with state labels.
- Proxy Pools exposes import/deploy/add/edit/delete/test operations; credentials must never be surfaced by spring-router.
- Skills exposes copyable links for chat, image, TTS, STT, embeddings, web search, and web fetch.

## Spring-router design rules

Reuse the operational information architecture, not 9Router's visual treatment. Keep spring-router local-only and custom:

- Desktop: compact left sidebar.
- Mobile: horizontal nav.
- Sections: Overview, Providers, Routing, Endpoint & Keys.
- Palette: charcoal background, sakura pink, purple, teal; avoid cream/coral 9Router styling.
- Redact access/refresh tokens, account emails, proxy credentials, raw prompts, and sensitive quota values.
- Keep the CLI short: ASCII separator, short labels, 4–5 actions, no box-drawing or emoji-heavy centering. Narrow terminals must not wrap.

## Verification recipe

1. `gofmt -w` and `go build` the Go project.
2. Serve the embedded dashboard on localhost.
3. Use Chromium/Playwright if Camofox is unavailable.
4. Check desktop and ~390px mobile viewport.
5. Click every nav section and inspect console errors.
6. Verify `/health`, `/api/status`, `/v1/models`.
7. Keep 9Router read-only throughout the audit.
