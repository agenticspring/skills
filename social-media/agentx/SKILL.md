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

- **`x-client-transaction-id` needs an AUTHENTICATED home-page fetch** (fixed 2026-10-10, upstream `DezXBT/AgentX` commit `6fb20da`; binary rebuilt + installed here). The generator derives its keys from the `,<idx>:"ondemand.s"` chunk map, which x.com **only serves to a session with cookies** — the logged-out page (41 KB shell) has no such entry, so generation fails and, because `setHeaders` only aborts writes, the symptom is: *every* write (`post`, `reply`, `like`, `bookmark`, `draft`, `dm send`, `grok`) fails with `api_error: generate x-client-transaction-id`, while reads look fine because they go out **unsigned**. Do not misread the follow-on 404s on `SearchTimeline`/`Followers` as stale query ids — they are the missing header (both old and new ids work once signed). Diagnose with: `strings /usr/local/bin/agentx | grep -i transaction` (the Go binary is **not stripped**), or clone the public source. Rebuild + install:
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
