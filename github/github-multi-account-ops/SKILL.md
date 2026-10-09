---
name: github-multi-account-ops
description: Dual GitHub PAT storage and 401 triage, secondary-account profile home polish, and private repo creation/push without persisting or clobbering credentials.
version: 1.0.0
author: spring
license: MIT
platforms: [linux]
---

# GitHub Multi-Account Ops

Use when the user provides a second GitHub PAT, wants dual-account storage, or asks to polish a GitHub **home profile** (not a share-card image).

## Dual token storage

Primary stays:
```text
GITHUB_TOKEN=<primary>
```

Secondary:
```text
GITHUB_TOKEN_2=<secondary>
GH_TOKEN_2=<secondary>   # alias
```

Rules:
1. Validate first with `GET https://api.github.com/user` — print **login + scopes only**, never full token.
2. Never overwrite primary when adding secondary.
3. Store only in Hermes env; never Obsidian/vault/repo.
4. After chat paste of a PAT, recommend rotation if exposed.

### Triage when the stored tokens stop working

A wall of `401 Unauthorized` across every call is usually **stale credentials**, not a broken
workflow. Work the list before asking the user for anything:

1. `GET https://api.github.com/user` per token. `401` on `/user` is definitive — the token is
   revoked or expired. Do not keep retrying or re-deriving; retries cannot fix a 401.
2. **Check `~/.git-credentials` too.** It is a third credential store, outside `.env`, and carries
   its own (often older) token. Parse `https://user:pass@host` and test the `pass` the same way —
   in the worked case it was dead alongside both env tokens, which is why every push path failed.
3. Only after all stores are dead, ask for a fresh PAT — and say which account it must belong to.
   Validate the replacement with `/user` and print **login + name only**.

### An absent `X-Oauth-Scopes` header is NOT "no permissions"

Fine-grained PATs do not emit `X-Oauth-Scopes`, so a header-less response looks identical to a
scope-less classic token. Never infer capability from the header — **probe the capability**:
`GET /orgs/<name>` (`404` = a user account, so repos go under `POST /user/repos`) and then just
attempt the real operation. In the worked case the header was absent yet the token created a
private repo and pushed to it fine, and clarifying that a *classic* PAT only needs `repo` (not
broad `user` scope) removed an unnecessary round-trip.

### Publishing mechanics live in another skill — do not duplicate them here

Tokenless push (one-shot `x-access-token` URL → strip the remote → assert `.git/config` holds no
`ghp_`), private-repo creation, post-push visibility verification, and remote-blob secret scans are
owned by **`private-source-repository-release`**. This skill covers *credential/account state*; that
one covers *publishing*. When actually shipping a repo, follow that skill.

### Classic scopes

| Goal | Scopes |
|---|---|
| Repo create/push/release | `repo`, `workflow`, `read:org` |
| Optional full manage | `gist`, `delete_repo` |
| Edit name/bio/location/blog/twitter | **`user`** |

Without `user`, `PATCH /user` returns 404/Not Found even though `GET /user` works.

## Home profile polish (user preference)

When user says **“tampilan home profile” / “profile akun”**:
1. **Not** a generated PNG share-card unless they explicitly want media.
2. Update profile fields via `PATCH /user` when token has `user` scope:
   - name, bio, location, blog, twitter_username, hireable
3. Create/update special public profile README repo: `login/login`
   - public repo required for overview README
   - write polished `README.md` via Contents API
4. Verify:
   - raw README URL 200
   - `https://github.com/<login>` loads
   - note GitHub overview cache can lag a few minutes

### Profile README shape (proven)

Centered header, badges, About, Stack, Currently Building, Principles, Connect. Keep it clean, no secrets.

## Secondary account known ops sample

- Secondary login: `agenticspring`
- Profile README repo: `agenticspring/agenticspring`
- Home: `https://github.com/agenticspring`
- Portfolio: `agenticspring/agentic-portofolio` → `agenticspring.dev`
- Agent-theme copy is valid when user requests it for this account

## Pitfalls

- Answering “home profile” with a PNG card is wrong for this user — they want the real GitHub overview.
- Token with only `repo` cannot update bio/location; add `user`.
- Do not print PATs in logs, commits, or vault notes.
- Prefer dual env keys over swapping remotes mid-session unless asked.
- Secondary public face may intentionally use **agent theme** (`agenticspring`); primary stays security/Web3 pro (`<HANDLE_REDACTED>`).
- Do not list forks as selected public work on either account.

## Companion

- Bundled `github-auth` for base PAT/SSH setup (do not edit bundled skill).
- `github-repo-management` for create/push/release mechanics.
- `github-profile-home` for Overview README + tone/banner details (prefer that skill for home-page cosmetics).
- Portfolio/domain flow: `github-profile-home/references/agenticspring-portfolio-vercel.md`
