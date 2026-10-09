# Grok CLI Responses API — observed shapes (cli-chat-proxy.grok.com)

Source: live probes against `https://cli-chat-proxy.grok.com/v1/responses` with a `grok-cli` OAuth access token (2026-08-09). This is what spring-router's `grokcli` provider speaks.

## Endpoint

- Base: `https://cli-chat-proxy.grok.com/v1`
- Chat: `POST /v1/responses` (OpenAI Responses API format, NOT chat/completions)
- Models: `GET /v1/models`
- User: `GET /v1/user?include=subscription`
- Billing: `GET /v1/billing?format=credits`

## Required headers

```
Authorization: Bearer {OAuth access_token}
Accept: application/json
Content-Type: application/json
x-xai-token-auth: xai-grok-cli
x-grok-client-identifier: spring-router
x-grok-client-version: 0.1.202      # <-- hard gate, see below
User-Agent: grok-pager/0.2.93 grok-shell/0.2.93 (linux; x86_64)
```

Optional identity headers (9Router sends them when known):
```
x-email: {account email}
x-userid: {userId | principalId}
x-grok-client-mode: headless
```

### Version gate (426 Upgrade Required)
`x-grok-client-version` must be ≥ 0.1.202. Lower values (e.g. `0.1.0`) return:

```json
{"error":"Your Grok CLI version (0.1.0) is outdated. Please update to version 0.1.202 or later via `grok update` or the installation documentation."}
```

Status 426, Content-Type application/json. 9Router ships 0.2.93 / 0.5.18 — always keep the header value ≥ 0.1.202.

## Request shape (OpenAI chat → Responses)

```json
{
  "model": "grok-4.5",
  "input": [
    {"role": "user", "content": [{"type": "input_text", "text": "12 times 12? Number only."}]}
  ],
  "reasoning": {"effort": "high"},
  "stream": true,
  "max_output_tokens": 100,
  "temperature": 0.7
}
```

- `reasoning.effort` accepts `low | medium | high | xhigh`. If omitted, server defaults to `high` (echoed back in response as `reasoning: {effort, summary}`).
- `max_output_tokens` is the Responses name for max_tokens; `max_tokens` alone is ignored.
- Some model IDs rejected: `grok-4.5-high`/`-xhigh`/`-reasoning` → 400, `grok-4.20`/`grok-latest` → 402, `grok-5` → 429. Only `grok-4.5` (and aliases mapped upstream to grok-4.5) works on this transport.

## Non-stream response (key fields)

```json
{
  "id": "65b3e867-...",
  "model": "grok-4.5",
  "object": "response",
  "output": [
    {
      "id": "msg_...",
      "role": "assistant",
      "type": "message",
      "status": "completed",
      "content": [
        {"type": "output_text", "text": "391", "logprobs": [], "annotations": []}
      ]
    }
  ],
  "reasoning": {"effort": "high", "summary": "detailed"},
  "usage": {
    "input_tokens": 216, "output_tokens": 490, "total_tokens": 706,
    "output_tokens_details": {"reasoning_tokens": 474},
    "cost_in_usd_ticks": 29556000
  },
  "status": "completed"
}
```

Extract answer text: join `output[].content[].text` where `type == "output_text"`.

## Stream SSE events

Content-Type: `text/event-stream`. Every event is two lines: `event: <type>` then `data: <json>`.

| event | data shape | action |
|---|---|---|
| `response.created` | envelope + `response.id`, `model` | send initial role chunk |
| `response.output_item.added` | `item` (message in_progress) | ignore |
| `response.content_part.added` | `part.type == output_text` | ignore |
| **`response.output_text.delta`** | `{"delta": "144", "output_index": 0, ...}` — **delta is a STRING** | emit content delta |
| `response.output_text.done` | `{"text": "144"}` | ignore (or final flush) |
| `response.content_part.done` / `output_item.done` | full text | ignore |
| `response.completed` | full response object incl. usage | emit finish_reason + `[DONE]` |
| `response.failed` / `error` | error info | emit error + `[DONE]` |

Critical gotcha: `response.output_text.delta`'s `delta` field is a **plain JSON string** (`"144"`), not an object. If you unmarshal into `struct{ Delta struct{Text string} }` you get empty content silently.

## Rate limiting / errors for flagged accounts

- 429 → `ErrRateLimited` (service applies backoff). Happens fast on `bfs:1` / solver-flagged farms.
- 5xx (502/503 in provider config retries) → `ErrUpstream`, retry via balancer.
- For `bfs:1` accounts the "response" still streams but model self-IDs as `unknown` / Grok-1/Grok-2 — reasoning `response.output_text.delta` content works, but true reasoning pathway is downgraded; `reasoning.summary: detailed` is echoed but no real CoT. See `grok-account-automation` skill for the full bfs story.