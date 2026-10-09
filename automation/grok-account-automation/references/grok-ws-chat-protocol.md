# Grok.com WebSocket chat protocol

Reverse-engineered 2026-08 from grok.com Next.js chunks (`0hs3cj1-3crlt.js`
GatewayConnectionManager, `13slx9hm9kihc.js` message-store).

## Why WS instead of REST

`POST https://grok.com/rest/app-chat/conversations/new` → 403
`{"code":7,"message":"Request rejected by anti-bot rules"}` even with valid
`sso` cookie, full request body, turnstile token in header/body, from both
proxy and direct IP. The REST chat path requires a Castle
`castle_request_token` minted by the client-side Castle SDK (feature flag
`ENABLE_CASTLE_CHAT_MINTING` adds `castle_request_token` to outbound events).
We could not mint that token outside a browser.

The WS gateway does NOT require castle and works with just the `sso` cookie.

## Connection

```
wss://grok.com/ws/mgw/?uid={userId}
Cookie: sso={session JWT from accounts CreateSession/CreateUserAndSession}
Origin: https://grok.com
```

userId from `GET https://grok.com/rest/auth/get-user` (cookie `sso`).
Proxy: `websocket.create_connection(url, http_proxy_host=..., http_proxy_port=...,
proxy_type="http", http_proxy_auth=(user, pass), sslopt={"cert_reqs": ssl.CERT_NONE})`.
Without `http_proxy_auth` you get CONNECT 407.

## Envelope

Every client event is wrapped: `{"session_id": "<sid>", "event": {...}}`.
Server events likewise carry `session_id` and `event.type`.

## Sequence that works

1. `{"event": {"type": "session.create", "session": {}}}` →
   read replies until `session.created`; capture `session_id` (also equals the
   conversation id when `conversation.attached` arrives with `mode: "new"`).
2. Wait for `conversation.attached` before sending items (otherwise item
   create gets no ack).
3. `{"session_id": sid, "event": {"type": "conversation.item.create",
   "event_id": "evt_msg_...", "item": {"type": "message", "role": "user",
   "content": [{"type": "input_text", "text": "..."}]}}}`

   **The working item shape is OpenAI-style `content: [{type:"input_text", text}]`.**
   The web app actually sends `x_grok: {client_message_id, input_chunks}` where
   input_chunks are protobuf-json of `chat.InputChunk` (oneof content →
   text → UserText → Text{text, channel}); trying those shapes made the model
   reply "your message got cut off" — the item text was not registered.
4. `{"session_id": sid, "event": {"type": "response.create", "event_id": "evt_resp_..."}}`
5. Read until `response.done`; accumulate `response.output_text.delta` →
   `event.delta`. Final text also in `response.output_text.done` / `content_part.done`.
6. Optional model override: add `"model": "grok-4-1-thinking-1129"` inside the
   `conversation.item.create` event (not the item).

## Event types observed (server → client)

- `session.created`, `conversation.attached`, `conversation.queue.updated`
- `conversation.item.added` (ack of our item)
- `response.created`, `response.output_item.added`, `response.content_part.added`
- `response.grok.output` — may carry `stream_error: {kind: "usage_limit_reached"}`
- `response.output_text.delta` / `.done`, `response.content_part.done`,
  `response.output_item.done`, `response.done`, `conversation.title.updated`,
  `response.persisted`

## Error signatures

- Envelope missing `event` field → `invalid_envelope: missing field 'event'`.
- Envelope missing `session_id` for session-scoped events →
  `invalid_envelope: session_id is required for session-scoped events`.
- `response.grok.output` with `stream_error.kind == "usage_limit_reached"` →
  free tier exhausted (~10 req / 2h). Not an account ban.
- Empty `response.output_text.done` with `stream_error` → limit, not a format issue.

## Model availability

`POST https://grok.com/rest/models` body `{"locale":"en-US"}` returns models
(works unauthenticated): `grok-3` (default free), `grok-420`, `grok-4-1-thinking-1129`
(reasoning), `grok-3-mini-companion`, plugins. The accounts.x.ai `ListModels` RPC
returns the wider catalog (grok-4.5, grok-4.20-multi-agent, grok-code-fast-1, etc.)
but those names are not all valid in the chat WS — stick to the `/rest/models` list
for chat `model` overrides.
