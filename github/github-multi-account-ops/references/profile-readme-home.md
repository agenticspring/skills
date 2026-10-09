# GitHub Profile README on home Overview

## Goal
Show a rich landing block on `https://github.com/<login>` Overview without forcing visitors to open a repo card first.

## Required shape
1. Public repo named **exactly** the username: `<login>/<login>`
2. `README.md` on default branch root
3. GitHub renders it in a `profile-readme` box on Overview

## Agent checklist
1. Confirm token scopes: need `repo` for the special repo; need `user` for bio/location PATCH.
2. Create public `login/login` if missing (`auto_init` OK).
3. Write/update `README.md` (Contents API or git push).
4. Verify:
   - `GET /repos/<login>/<login>` → `private=false`
   - raw README 200
   - home HTML has `profile-readme` **and** content markers from README
5. If only Popular repositories shows the special repo and Overview lacks the embed:
   - wait / hard refresh
   - ask user (logged in as that account) to open the special repo and click **Share to profile** if present
   - do not keep regenerating PNG cards as a substitute

## User preference (Dez)
- “Tampilan home profile” = real GitHub Overview, not a PNG share-card.
- Want original identity, not a clone of another agent profile.

## Sample secondary account
- `agenticspring` / `GITHUB_TOKEN_2`
- Home: https://github.com/agenticspring
- Special repo: https://github.com/agenticspring/agenticspring
