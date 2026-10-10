---
name: agentx
description: Drive X/Twitter from the CLI (read, post, DM, lists, communities, Grok, scheduling, analytics). Use when an agent needs to read or act on X/Twitter. Every command prints one JSON envelope.
version: 1.0.0
author: DezXBT
license: Private
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Twitter, X, Social-Media, CLI, Agent, Grok, DM, Post]
    related_skills: [xurl, x-premium-gift]
---

# agentx — X/Twitter agent control surface

`agentx` is a single Go binary. Every command prints **one JSON envelope** to stdout, so parse stdout as JSON and check `.ok`. Build: `go build -o agentx ./cmd/agentx`.

## Envelope (always this shape)
```json
{"ok":true,"schema_version":"1","data":<any>,"pagination":{"nextCursor":"…"},"rateLimit":{…}}
{"ok":false,"schema_version":"1","error":{"code":"…","message":"…"}}
```
Rules: check `.ok` first. List data → `.data` is an array + `.pagination.nextCursor`. Single object → `.data` is an object. On error read `.error.code` (machine) + `.error.message` (human). Exit code ≠0 on error. Output is **compact single-line JSON by default** (token-efficient); add `--pretty` only when a human reads it.

## Setup (once)
```
agentx account add --name NAME --auth-token <auth_token> --ct0 <ct0>
```
Cookies come from a logged-in browser (`auth_token` + `ct0`). Env fallback: `TWITTER_AUTH_TOKEN`, `TWITTER_CT0`. Store: `$AGENTX_HOME/accounts.json` (default `~/.agentx`, mode 0600). Multi-account: add several, pick with `-a NAME`. `account login --name N --username U` (pass via `$TWITTER_PASSWORD`) does user/pass→cookies but X blocks login from datacenter IPs — prefer cookies.

## Global flags (may precede or follow the subcommand)
`-a NAME` account · `-n N` max items · `--cursor C` page cursor · `--pretty` human-readable JSON · `--account`/`--count` long forms.
IDs: any `<id>` also accepts a full tweet/list/community URL. Handles: with or without `@`.

## Commands (one line each)

READ
```
feed [--latest] [-n N] [--cursor C]      home timeline
search [--type Top|Latest] <query>       search
user <handle>  |  user --id <id>         profile
me                                       own profile
posts <handle> [-n N]                    a user's tweets
media <handle|id> [-n N]                 user's photos/videos
tweet <id>                               single tweet (zero-auth FxTwitter fallback)
thread <id>                              tweet + replies
article <id> [--markdown]                long-form X Article
analytics <id>                           metrics + engagement rate
likes <handle> | bookmarks | mentions    tweet lists
followers <handle> | following <handle>  user lists
retweeters <id> | likers <id>            who RT'd/liked (likers: author-only by X)
list <id> | list members <id>            List tweets / members
community posts <id> [--latest] | community info <id>
notifications [all|mentions|verified] | unread     (alias: notif)
trends [woeid] | trends locations        trending (Indonesia woeid=23424846)
scheduled | drafts                       your queued/draft tweets
settings                                 your privacy settings
```

WRITE (state-changing; reversible ones noted)
```
post <text> [--media f [--alt txt]] [--thread]    tweet (>280 → long-form, Premium)
reply <id> <text> [--media f] | quote <id> <text> [--media f]
poll <text> --option A --option B [--option C|D] [--duration MIN]
vote <id> <choice 1-4>
like/unlike  retweet/unretweet  bookmark/unbookmark  delete  <id>
pin/unpin <id>                                    pin tweet to profile
bookmark <id> --folder <id>                       bookmark into folder
follow/unfollow  mute/unmute  block/unblock  <handle>
edit <id> <text>                                  Premium
draft <text> | draft delete <id>
schedule <unix|+30m|+2h|+1d> <text> | unschedule <id>
profile [--name N] [--bio B] [--location L] [--url U]
avatar <img> | banner <img>
settings [--protected b] [--dms-from all|following] [--discoverable-email b] [--geo b]
topic follow|unfollow <topic_id>
list create <name> [--desc T] [--private] | list delete <id>
list add|remove <listid> <handle|id> | list subscribe|unsubscribe <id>
community join|leave <id> | community create <name>   (create is permanent)
bookmarks folder create <name> | delete <id>          (Premium)
dm send <handle> <text> [--media f]
```

GROK (AI)
```
grok <prompt>                            text answer (live web search built in)
grok image <prompt> [--out file]         generate image(s), download to file(s)
```

UTILITIES
```
download <id|url> [--out f] [--all]       save tweet media / a direct URL
watch <mentions|search <q>> [--interval 60s] [--once]   NDJSON stream of new tweets
account list|remove <n>|default [n]|check [n]
```

## Pagination
List commands return `.pagination.nextCursor`. Pass it back via `--cursor` for the next page. `-n N` caps items in the response (note: the cursor still points past the full fetched page, so for exact paging use the cursor, not a tiny `-n`).

## Error codes (`.error.code`)
`not_authenticated` bad/expired cookies · `not_found` · `invalid_input` · `rate_limited` (see `.rateLimit`) · `query_id_error` X rotated a GraphQL id → set `AGENTX_QID_<Operation>=<id>` env or update constants · `network_error` · `api_error` x.com rejected (message has detail) · `account_error`.

## Gotchas
- **Premium-gated** (work only on X Premium accounts; routing is correct, x.com returns a clear error otherwise): `edit`, note/long-form `post` (>280), `bookmarks folder` writes.
- **Account-eligibility**: `community create` needs an eligible account.
- **likers**: X returns the liker list only to the tweet's author; empty for others (retweeters is public).
- **grok image**: needs image-gen quota (free tier is limited/daily); errors clearly when the quota is spent.
- **DM**: only classic (unencrypted) DMs via `dm send/list/download`. X's new **XChat is end-to-end encrypted and out of scope** (keys are device-only, non-extractable).
- **Rate limit**: `.rateLimit` carries `x-rate-limit-*`; back off when `remaining` is low.
- `AGENTX_UTLS=1` sends a Chrome JA3 TLS fingerprint (HTTP/2) for stealth.
- Writes are real and public — confirm intent before posting/following/etc.
- **X Premium Gift Exploit** — Payment validation bypass via Stripe Bank Transfer. See `x-premium-gift` skill for full automation details. Key constraints: donor must be >1 day old, **donor CAN gift multiple times** (not limited to 1), some targets are ineligible (not a donor limit issue). Premium activates before payment validation.

## Media File Organization

**ALWAYS save downloaded media to organized folders:**

```
/root/media/
├── photos/      ← Twitter photos, screenshots
├── videos/      ← Twitter videos, clips
└── grok/        ← Grok AI generated images
```

**Rules:**
- Photos → `/root/media/photos/` (`.jpg`, `.png`, `.webp`)
- Videos → `/root/media/videos/` (`.mp4`, `.mov`)
- Grok generated → `/root/media/grok/` (`.jpg`, `.png`)
- Use descriptive filenames: `{author}_{tweetid}.{ext}` or `{prompt_short}.{ext}`
- NEVER save media to `/root/` directly — always use subfolders

**Examples:**
```bash
# Download tweet photo
agentx download 123456 --out /root/media/photos/amelie_123456.jpg

# Download tweet video  
agentx download 789012 --out /root/media/videos/mangolinx_789012.mp4

# Generate Grok image
agentx grok image "cyberpunk cat" --out /root/media/grok/cyberpunk_cat.jpg

# Quick curl download
curl -s -o /root/media/photos/user_123.jpg "https://pbs.twimg.com/media/xxx.jpg"
```

## Image Generation & Sending to User
When user asks to generate images with Grok:
```bash
agentx grok image "prompt" --out /root/media/grok/descriptive_name.jpg
```
Then include `MEDIA:/root/media/grok/descriptive_name.jpg` in response. **Do NOT call vision_analyze** on generated images — send directly. User explicitly prefers this workflow.

## Downloading & Sending Tweet Media
```bash
# Download via agentx (use /root/media/ subfolders!)
agentx download <tweet_id> --out /root/media/photos/author_id.jpg
agentx download <tweet_id> --out /root/media/videos/author_id.mp4

# Or curl the pbs.twimg.com URL directly (faster, no auth needed)
curl -s -o /root/media/photos/photo.jpg "https://pbs.twimg.com/media/XXXXX.jpg"
```
Send with `MEDIA:/root/media/photos/photo.jpg` in response.

## Typical flows
- Read a user's latest: `agentx posts elonmusk -n 20`
- Reply: `agentx reply <id> "nice"` · Quote with image: `agentx quote <id> "look" --media pic.jpg`
- Thread: `agentx post --thread "long text…"` · Poll: `agentx poll "Q?" --option A --option B`
- Schedule: `agentx schedule +2h "later"` then `agentx scheduled`
- Ask Grok: `agentx grok "USD to IDR today?"` · Image: `agentx grok image "a dragon" --out d.png`
- Paginate: `agentx feed -n 40` → take `nextCursor` → `agentx feed --cursor <c>`
- Download tweet media: `agentx download <tweet_id> --out /path/to/file.mp4`
## Pitfalls & Learnings

- **x.com answers HTTP 200 for REJECTED operations.** The failure signal is *inside* the
  body (`errors[]`, or an operation-specific `message`/empty result), so a write can
  "succeed" while doing nothing. Fixed in `DezXBT/AgentX` commit `2319e40`
  (2026-10-10), which now checks: `TopicFollow`/`TopicUnfollow` (empty `topic_id`/`name` ⇒
  `not_found`), `CommunityByRestId`/`CommunityTweetsTimeline`
  (`{"__typename":"CommunityUnavailable"}` ⇒ `not_found`).
  ⚠️ **That commit's `pin`/`unpin` check was WRONG and was corrected in `c15c545`** — do not
  reinstate it. Treating any non-empty `pin_tweet.message` as a failure breaks real pins, because
  x.com uses the `message` field for BOTH outcomes and exposes no usable boolean
  (`added_tweet_to_highlights` is `false` in the success body too):
  | op | outcome | body |
  |---|---|---|
  | pin | ok | `{"pin_tweet":{"added_tweet_to_highlights":false,"message":"post pinned successfully"}}` |
  | pin | fail | `{"pin_tweet":{"added_tweet_to_highlights":false,"message":"post is not valid for pinning"}}` |
  | unpin | ok | `{"unpin_tweet":{"message":"post unpinned successfully"}}` |
  | unpin | fail | `{"unpin_tweet":{"message":"no pinned post changes required"}}` |
  So: match the success text exactly and fail closed on anything else. Verify a pin out of band via
  the profile's `pinned_tweet_ids_str` (use `AGENTX_DUMP_RAW`), never from `ok:true` alone.

  **`delete <tweet>` cannot be verified client-side**: x.com returns the identical
  `{"delete_tweet":{"tweet_results":{}}}` for a successful delete and for one it ignores
  (confirmed against a real delete). Do not "fix" that with a non-empty-result check — it
  would break real deletes.
- **Debug raw traffic with `AGENTX_DUMP_RAW=<file>`** (added in `2319e40`): appends each raw
  x.com response body. It is the only way to see whether a 200 actually did anything.
  Confirm cleanups by re-reading state (timeline/search), not by trusting `ok:true`.
- **A tweet now reports its reply linkage** (added 2026-10-10, commit `2ced4e7`): `isReply`,
  `inReplyToId`, `inReplyToUser`, `conversationId` — filled from graphql
  (`legacy.in_reply_to_status_id_str` / `in_reply_to_screen_name` / `conversation_id_str`), REST v1.1
  (same names) and FxTwitter (`replying_to_status` / `replying_to`). Before this the only hint that a
  post was a reply was the `@handle` text prefix. Semantics: `conversationId` is the **root** tweet of
  the thread, so it equals the tweet's own `id` for a thread starter. Verify a reply landed with
  `agentx tweet <reply_id>` → `inReplyToId` must equal the parent id; `agentx thread <parent_id>`
  must list the reply.
- **Verifying each public write (recipe, exercised live 2026-10-10 on the burner `kawinvrai`).**
  Every write needs a **read-back** check; `ok:true` alone proves nothing:
  | Write | Read-back that actually proves it |
  |---|---|
  | `post "…"` | `tweet <new_id>` returns text+author; `me` → `tweetsCount` +1 |
  | `reply <id> "…"` | `tweet <new_id>` → `inReplyToId == <id>`; `thread <id>` lists it. **Replies to others do NOT appear in `posts <handle>`** (profile timeline excludes replies) — that absence is correct, not a bug |
  | `retweet <id>` | `retweeters <id>` contains your handle; a new `RT @…` entry appears in `posts <handle>` |
  | `bookmark <id>` | `bookmarks -n 40` contains the id |
  | `like <id>` | **`likes <ownhandle>`** contains the id (this is the reliable one). `likers <id>` is author-only, so it is **empty for someone else's post** — useless as a read-back |
  | `bookmark <id>` | `bookmarks -n 40` contains the id |
  | cleanup (`delete`/`unretweet`/`unbookmark`/`unlike`) | `tweet <id>` → `not_found`; `retweeters <id>` no longer lists you; `bookmarks` / `likes <handle>` no longer contain it; `me` → `tweetsCount` back to its original value (exercised end-to-end 2026-10-10: 6 → 9 after post+reply+RT, back to 6 after cleanup) |
  Cleanup after a test: `delete <post_id>`, `delete <reply_id>`, `unretweet <id>`, `unbookmark <id>`, `unlike <id>`.
  **There is no way to delete a DM** — a test `dm send` to yourself is permanent.
- **`-a <unknown>` now returns `account_error`** (commit `84599fe`), not `api_error` — it used to
  silently fall back to the zero-auth FxTwitter backend. Test the FxTwitter path on purpose with
  `AGENTX_HOME=/tmp/empty agentx tweet <id>` (no accounts ⇒ `source: "fxtwitter"`).
- **A poll is readable back** (added 2026-10-10, commit `dd3a558`). `Tweet.Poll` carries
  `choices[{label,count}]`, `endsAt`, `durationMinutes`, `final`, `selected`. x.com ships a poll as
  a **card**, not a typed object, so the parser reads `card.legacy.binding_values`
  (`name` starts with `poll`) and decodes `choice<N>_label`, `choice<N>_count`,
  `end_datetime_utc`, `duration_minutes`, `counts_are_final`, `selected_choice`. `selected` is the
  only proof your own `vote` registered — X keeps `choice<N>_count` at 0 and
  `counts_are_final=false` until it publishes the tally, so a 0/0 count does **not** mean the vote
  failed. Non-poll tweets and non-poll cards carry no `poll` field.
- **Coverage notes from the full sweep (2026-10-10).**
  - `watch <mode> --once` **emits the current matches and exits** — it does *not* seed silently (only
    the non-`--once` loop does). Empty output therefore means "no matches", not a broken stream.
    Burner with 0 followers has no mentions; prove the path with
    `agentx watch search "<query>" --once` (emits NDJSON).
  - `likers <id>` is **author-only** → empty for someone else's tweet. To verify your own like, read
    `likes <your-handle>`.
  - `bookmarks folder create` / `bookmark --folder` are **Premium-gated**: the failure is
    `api_error: Authorization: User … not authorized to use bookmark collections`. Correct, not a bug.
  - `article <id>` needs a **real X Article id** — a bogus numeric id fails with
    `api_error: strconv.ParseInt … value out of range` (the id is simply not a tweet id).
  - `post --thread` auto-splits >280 chars into a real thread (returns the id list); `post --media f
    --alt t` uploads media (the returned text gains a `t.co` link); `grok image` works and writes a
    JPEG (free tier ~100/day); `grok <prompt>` answers with live web search.
  - `block`/`unblock` and `follow`/`unfollow` report `done:true`; verify **follow** via
    `following <handle>`, but there is **no blocked-list command**, so a block can only be confirmed
    by the response.
  - Not exercisable on a non-Premium burner: `edit`, long-form `post` (>280) and bookmark folders
    (Premium-gated), `community create` (permanent), `account login` (X blocks datacenter IPs),
    `account add`/`remove` (needs a second account), `dm download` (a test `dm send` can never be
    deleted), `article` (needs the *tweet* id of an article post — see below), and
    `topic follow`/`unfollow` (no topic id is discoverable from any command surface — `topic_id`
    appears in no response body).
- **Profile-mutating writes ARE testable non-destructively** (done 2026-10-10): capture the current
  state, write, verify by re-reading, restore, re-verify.
  - `profile --name/--bio/--location/--url`: **empty values are ignored** (`profile --location ""` ⇒
    `invalid_input` usage), so only mutate fields that already hold a value, or you cannot restore
    them.
  - `settings [--protected b] [--dms-from all|following] [--discoverable-email b] [--geo b]`: read
    current values with a plain `agentx settings`, flip, then flip back.
  - `avatar <img>` / `banner <img>`: back up the originals first — `profile_image_url_https` with the
    `_normal` suffix stripped, and `profile_banner_url` **+ `/1500x500`** (without the suffix you get a
    600×200 thumbnail). The CDN URL changes on re-upload (new media id / timestamp) but the image is
    byte-identical: compare pixels (`PIL.ImageChops.difference`), not URLs.
- **Community join/leave semantics** (bodies captured 2026-10-10). `community info <id>` reports
  `joinPolicy`, `isMember`, `role` — use it to pick an **open** community (`joinPolicy: "Open"`) when
  testing `join`; a restricted one fails with a GraphQL `DependencyError: Dependency: Unspecified`
  (agentx reports it correctly, `ok:false`). The `community_join`/`community_leave` responses carry an
  `actions` object describing the state **after** the call, so a successful leave reads
  `leave_action_result: CommunityLeaveActionUnavailable / "Not a member."` and the body is
  **byte-identical whether you were a member or not** — `done:true` is correct in both cases and
  need not be distinguished.
- **`list subscribe` is idempotent**: subscribing twice returns the *same* body (`list_subscribe_v3`
  with the list metadata and `"following":true`). There is no command that lists your
  subscriptions, so that body flag is the only read-back.
- **`article <id|url>` wants the TWEET id of a post that carries an article** (looked up via
  `TweetResultByRestId`). An `x.com/i/article/<id>` id is **not** a tweet id and returns `not_found`
  with body `{"data":{"tweetResult":{}}}`.
- **`download --all --out DIR` used to ignore DIR** (fixed `b3301c9`) and dumped every file into the
  cwd. `--out` now means a *file* only when exactly one file is written to it and the path is not a
  directory; otherwise it is a destination directory, created if missing. Verify downloads by listing
  the target directory — the `saved:` field echoed a bare name when the bug was live, which is easy to
  misread as success.
- **Never probe a PUBLIC write against a real target.** A "bad id" is not safe for
  `reply`/`quote` — tweet id `1` exists, so `quote 1 "x"` really posts. Verify public writes
  by posting to your own account and deleting it, or use an id that cannot exist
  (`999999999999999999999`); scheduled tweets *do* fire, so `unschedule` everything you
  created.
- **`x-client-transaction-id` needs an AUTHENTICATED home-page fetch** (fixed 2026-10-10, upstream `DezXBT/AgentX` commits `19b7825` + `2319e40`; binary rebuilt + installed here). The generator derives its keys from the `,<idx>:"ondemand.s"` chunk map, which x.com **only serves to a session with cookies** — the logged-out page (41 KB shell) has no such entry, so generation fails and, because `setHeaders` only aborts writes, the symptom is: *every* write (`post`, `reply`, `like`, `bookmark`, `draft`, `dm send`, `grok`) fails with `api_error: generate x-client-transaction-id`, while reads look fine because they go out **unsigned**. Do not misread the follow-on 404s on `SearchTimeline`/`Followers` as stale query ids — they are the missing header (both old and new ids work once signed). Diagnose with: `strings /usr/local/bin/agentx | grep -i transaction` (the Go binary is **not stripped**), or clone the public source. Rebuild + install:
  ```bash
  git clone https://github.com/DezXBT/AgentX.git && cd AgentX   # dezxbt/agentx redirects here
  go build -o agentx ./cmd/agentx                              # go >= 1.22
  cp -a /usr/local/bin/agentx /usr/local/bin/agentx.bak-$(date +%F) && install -m755 agentx /usr/local/bin/agentx
  ```
  Backup binary from the fix: `/usr/local/bin/agentx.bak-2026-10-10`. Source clone: `/root/projects/agentx`.
- **`gh` CLI required at startup** — binary checks `exec.LookPath("gh")` and exits with `ERROR: gh CLI not found.` if missing. Install: `apt install gh` or `curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg`. `gh auth login` is NOT required — tokens from `data/tokens.txt` are used directly for GitHub API calls; `gh` is only a fallback when no tokens file exists.
- **Grok images: NEVER call vision_analyze** — The vision model often returns 402 (insufficient balance). When user asks to generate images with Grok, generate and send directly via `MEDIA:`. Do NOT try to analyze/inspect the generated image first. User explicitly prefers this workflow.
- **External CDN links expire** — Links like `cdn.mp4ko.de`, `dood.stream`, `aceiymg.com`, `vdko.de` are external hosting, NOT Twitter CDN. They expire, get geo-blocked, or return tiny error pages. Use `agentx download <id>` for Twitter-hosted media (pbs.twimg.com, video.twimg.com) which handles auth properly.
- **Discord video delivery limits** — Videos >~10MB may fail silently via Discord bot attachment. Workaround: compress with ffmpeg before sending:
  ```bash
  ffmpeg -i input.mp4 -vf "scale=360:-2" -c:v libx264 -crf 30 -preset ultrafast -c:a aac -b:a 48k -movflags +faststart output.mp4
  ```
  Typical: 20MB → 8-9MB. Under 8MB is safe for all Discord servers.
- **`agentx download` vs curl** — Use `agentx download <id>` for Twitter-hosted media (pbs.twimg.com, video.twimg.com — handles auth). External CDN links need raw `curl -L` and often expire/blocked.
- **Rate limits** — Feed/search: 150-500 req/window. Grok image gen: 100/day. Check `.rateLimit.remaining` in responses.
- **Burner account setup** — When user provides `auth_token` + `ct0`, add with: `agentx account add --name burner --auth-token <token> --ct0 <ct0>`. Verify with `agentx me --pretty` before proceeding.
