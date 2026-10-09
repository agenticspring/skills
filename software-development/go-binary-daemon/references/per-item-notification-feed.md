# Per-item notification feeds (when the user asks for one)

Default for any long-running worker is **event-driven** alerting: a win, a denied review, a
worker death, run completion, a threshold crossing. A per-iteration feed normally trains the
user to ignore the channel, which is worse than no channel.

**Dez is the explicit exception.** On the GoCollect validation run (2026-09-26) he overrode the
default in one line: *"tiap open tetap di kasih notif"* — one message per action, not just per
event. When he asks for a feed, deliver it. What follows is how to build it so it stays
trustworthy instead of becoming noise.

## Building a per-item feed on top of an existing watcher

Reuse the watcher's log reader, offsets and state file — do not write a second poller. The
watcher already dedupes and persists; a parallel tailer will double-post and drift.

1. **Match the result line, never the progress line.** Workers that rewrite a progress line with
   `\r` into one giant line will otherwise match nothing (or everything). Anchor on the result
   shape, and allow the trailing detail to be optional:

   ```python
   OPEN_RESULT_RE = re.compile(
       r"\[open (\d+)/(\d+)\]\s+(\S+)\s+->\s+(.+?)"
       r"(?:\s*\(pity=(\d+),\s*u=([0-9.]+)\))?\s*$")
   ```

   **Sanity-test the regex against real log lines before wiring it up** — including a negative
   case (`[walk] ->crate 195m walked=0m`, `[hb] ... opens=2`) to prove no false positives, and a
   synthetic winning line to prove the escalation branch fires. Run it as a throwaway check and
   read the captured groups out loud; a feed that silently matches nothing looks identical to a
   quiet run.

2. **Dedupe by hashing the raw line**, stored in the watcher's existing state list — so restarting
   the watcher does not replay history. Note that an offset-based reader only ever sees *new*
   bytes, which means an already-completed item is never re-sent; confirm that behaviour rather
   than assuming it.

3. **Prove it fired.** Do not report "notifications are configured" from code review. Grep the
   watcher's own log for the send confirmation and quote the raw line as evidence:

   ```
   2026-09-26 14:56:34 discord sent :: 📦 OPEN 3/24 — G1 | crate `891f095aa0bffff:1989343` | hasil: **empty** (pity=4, u=0.388)
   ```

   Only then is the feed verified. If nothing has fired yet, say that instead.

4. **Escalate format on a hit** (ordinary glyph for a routine result, jackpot glyph for a win)
   so the channel stays scannable — and keep the separate event-driven alerts **on top of** the
   feed rather than replacing them. Completion still deserves its own message.

5. **Cooldown per repeated error code** (~1 alert per code per 5 minutes). A rejection or retry
   storm will otherwise flood the channel and destroy the signal you just added. Let the
   threshold-crossing alerts keep their own, longer cooldowns.

## Transport notes

- Webhook URL lives in the shared secrets file, never in code, README, example config, or notes.
- Posting JSON with `curl`: **HTTP 204 is the success signal** — the body is empty, so
  body-sniffing reports false failures. Capture the status code, not the body.
- When the user asks for Discord, make it the primary path and keep any vendor transport as a
  fallback: read the shared env file, let an env var override it, and dispatch in one `send()`.
