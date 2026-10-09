# Grok CLI — device-auth login & 9Router grok-cli injection

Session-proven flow (2026-08-08). All browserless.

## 1. Install official CLI

```bash
curl -fsSL https://x.ai/cli/install.sh | bash
# grok 1.0.0 (3cd0d0cbce) → ~/.grok/bin/grok + ~/.grok/bin/agent, symlink ~/.local/bin/grok
export PATH="$HOME/.local/bin:$PATH"
```

## 2. Login via device-auth (no browser)

```bash
grok login --device-auth
```

Output:
```
To sign in, open this URL in your browser:
  https://accounts.x.ai/oauth2/device?user_code=QNY6-D7HQ
Confirm this code in your browser:
  QNY6-D7HQ
Waiting for authorization...
```

User code format: **9 chars `XXXX-XXXX`** (e.g. `QNY6-D7HQ`, `FXJF-AX6K`, `2GHB-EV6J`).

### Approve with session cookie (the key discovery)

```
POST https://auth.x.ai/oauth2/device/approve
Content-Type: application/x-www-form-urlencoded
Cookie: sso={session_cookie_JWT}
body:  user_code={USER_CODE}&action=allow
→ 303 → Location: https://accounts.x.ai/oauth2/device/done
```

- Discovered from Next.js payload of `/oauth2/device/consent?user_code=...`:
  `approveUrl: "https://auth.x.ai/oauth2/device/approve", userCode: "..."` (node `$L42`).
- `action` must be `allow`. Other values (`approve`, `authorize`, `confirm`, `grant`, `yes`, `accept`) → `400 Invalid action`. Wrong field name (`userCode`) → `400 Missing user_code`.
- JSON body → `415 Form requests must have Content-Type: application/x-www-form-urlencoded`.
- curl_cffi session needs `sso` cookie on BOTH `accounts.x.ai` and `auth.x.ai` domains, plus a prior GET to `https://accounts.x.ai/` to establish the session.

### Result

`~/.grok/auth.json`:
```json
{
  "https://auth.x.ai::{uuid}": {
    "key": "eyJ...", "auth_mode": "...", "user_id": "...", "email": "...",
    "first_name": "...", "last_name": "...", "principal_type": "...",
    "refresh_token": "...", "expires_at": "...", "oidc_issuer": "...", "oidc_client_id": "..."
  }
}
```

### Pitfall: user_code regex

Device codes are 9 chars. `[A-Z0-9]{3}-[A-Z0-9]{3}` matches a WRONG inner substring of
`user_code=FXJF-AX6K` → you'd approve `XJF-AX6` and get `400 Missing user_code`.
Parse the standalone "Confirm this code in your browser:" line with
`[A-Z0-9]{3,6}-[A-Z0-9]{3,6}` (and `cat -A` to check for ANSI codes around the line).

## 3. CLI usage (non-tty)

```bash
grok -p "What is 17*23?"                     # single-turn; prints to stdout
grok -p "..." --always-approve               # execute tools
grok -p "..." --output-format streaming-messages-json  # events: init (tools list), assistant tool_use, user tool_result, result
grok models                                  # free tier: only grok-4.5
grok -m grok-4-1-thinking-1129               # rejected: "unknown model id" (needs plan)
GROK_PROXY_URL=http://user:pass@host:port grok ...   # proxy
```

- TUI (`grok "prompt"` bare) fails in non-tty: `Error: No such device or address (os error 6)` → use `-p`.
- Tool calling works: init event lists 27 tools (run_terminal_command, read_file, search_replace,
  list_dir, grep, kill_command_or_subagent, todo_write, spawn_subagent, web_search, web_fetch,
  image_gen, image_edit, image_to_video, reference_to_video, write, ...). With `--always-approve`,
  `run_terminal_command` executes (`echo $((6 * 7))` → `42`), and the model continues with the result.
- Verified cost: ~$0.009/request (grok-4.5, ~11.3k input tokens, 314 output).

## 4. 9Router grok-cli provider injection

Provider exists in 9Router (v0.5.18): id `grok-cli`, alias `gcli`, aliases `grok-build`/`gb`,
display "Grok CLI (Grok Build)".
OAuth: clientId `b1a00492-073a-47ea-816f-4c329264a828`,
deviceCodeUrl `https://auth.x.ai/oauth2/device/code`,
tokenUrl `https://auth.x.ai/oauth2/token`, scope `openid profile email offline_access grok-cli:access api:access conversations:read conversations:write`, referrer `grok-build`.

### Flow

```bash
TOKEN=$(echo -n "$(cat ~/.9router/machine-id)9r-cli-auth$(cat ~/.9router/auth/cli-secret)" | sha256sum | cut -c1-16)
```

1. Start device flow:
   ```
   GET /api/oauth/grok-cli/device-code   (x-9r-cli-token: $TOKEN)
   → {device_code, user_code, verification_uri, verification_uri_complete, expires_in:1800, interval:5, codeVerifier}
   ```
2. Approve user_code with session cookie (section 2) → 303.
3. Poll:
   ```
   POST /api/oauth/grok-cli/poll   (x-9r-cli-token, Content-Type: application/json)
   body: {"deviceCode": "<device_code>", "codeVerifier": "<codeVerifier>"}
   → {"success":true,"connection":{"id":"...","provider":"grok-cli"}}
   ```
   Poll is POST with JSON body — GET or `?device_code=` query → `400 Unknown action`.

### Usage after injection

- Model id at `/v1/models`: **`gcli/grok-4.5`** (prefix = alias `gcli`).
- Chat: `POST /v1/chat/completions` with `Authorization: Bearer <key from GET /api/keys>`
  (the x-9r-cli-token is NOT accepted for /v1 — `401 Invalid API key`).
  `/v1/models` itself works without auth on localhost.
- Verified: 3 connections injected (one per farmed account) → round-robin balances requests.
  `gcli/grok-4.5`: 17*23 → 391 ✅; 123*456 → 56088 (step-by-step) ✅;
  17*23+45*12 → 931 ✅. Supports `reasoning_effort` high/medium/low/xhigh; 500k context;
  `reasoning_effort` can be passed in the request body.

### Reusable scripts (session artifacts, adjust paths)

- `/tmp/grok_cli_flow2.py` — start `grok login --device-auth`, parse code from log, approve via session, wait for auth.json.
- `/tmp/grok_9router_flow2.py` — device-code → approve → poll for ONE account.
- `/tmp/grok_9router_flow3.py` — loop over accounts[1..n], inject each.
