# Profile README embed notes

## Special repository rules
- Public repo name must equal login exactly: `<HANDLE_REDACTED>/<HANDLE_REDACTED>`, `agenticspring/agenticspring`
- Root `README.md` on default branch (`main`)
- Optional `assets/banner.svg` linked from README

## Dual tokens (Hermes env)
- `GITHUB_TOKEN` → primary (`<HANDLE_REDACTED>`); often has `repo, workflow, read:org` only
- `GITHUB_TOKEN_2` → secondary (`agenticspring`); needs `user` for profile PATCH
- Store in `~/.hermes/.env` only; never print full tokens

## Scope matrix
| Action | Scope needed |
|---|---|
| Create/push special repo | `repo` |
| PATCH name/bio/location/blog/twitter/hireable | `user` |
| Without `user`, PATCH `/user` may 404 | explain + still ship README |

## Embed verification
Success markers on `GET https://github.com/<login>`:
- `profile-readme`
- `markdown-body`
- text from latest README commit

Not enough:
- raw.githubusercontent.com shows README
- special repo exists under Popular repositories only

## Lag / Share to profile
- Brand-new accounts may not auto-embed immediately
- Docs: older special repos may need manual **Share to profile**
- Mobile GitHub caches Overview; hard refresh/incognito
- User must be logged into the target account for Share to profile

## Tone (user-corrected)
- Default: professional human developer bio
- Reject AI-agent farm copy unless explicitly requested
- Match account work identity (<HANDLE_REDACTED> security/Web3 vs agenticspring clean public face)
