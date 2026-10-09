# Cloning + rebranding a pure-Functions Vercel app (nonthon-main.zip → SpringMovie)

Session 2026-08-04. Dez provided `nonthon-main.zip` and asked to replace ALL of
SpringMovie with it, keeping only Sakura Noir style and no Nonthon/NXR names.

## App shape (NOT Next.js)

The zip is a **pure Vercel Functions** app, no framework build:

```
api/index.js        serves src/app.html (Node handler, default export)
api/{login,logout,stream,subs,sub,dracin,dracin-id,dracin-img,nxrstream}.js
lib/{auth,localize,nxr-crypto}.js
src/app.html        the whole SPA (inline CSS + JS)
tools/dev-server.mjs  local routing emulator
vercel.json         rewrites / → /api/index, functions.includeFiles src/**
```

package.json has NO build script for Next; `vercel dev` + `tools/dev-server.mjs`
are the local paths.

## Rebrand recipe (validated locally)

1. Extract zip safely (check `zipfile` entry names for `..` / absolute paths first).
2. Rename files: `api/nxrstream.js` → `api/springstream.js`,
   `lib/nxr-crypto.js` → `lib/spring-crypto.js`; update imports + dev-server route.
3. Global string replacements across `.js/.mjs/.json/.html/.example/.gitignore`:
   `Nonthon→SpringMovie`, `nonthon→springmovie`, `NXRStream→SpringStream`,
   `NxrHunt Labs→SpringMovie`, `/api/nxrstream→/api/springstream`,
   `nxr-crypto.js→spring-crypto.js`.
4. In `src/app.html`, also replace internal identifiers that still read "nxr"
   (`nav-nxr`, `nxrState`, `nxrApi`, `nxrSubSelect`, `NXR-VIP SERVER`, …) so a
   plain `grep -i nxr` comes back clean.
5. Palette swap (Sakura Noir): `--bg:#09070d --surface:#151018
   --surface-hover:#221522 --primary:#e692af --primary-hover:#f5a9c5
   --border:#3a2532`.
6. Open-access conversion:
   - `api/index.js`: drop `isAuthed` gate, always `send(loadApp())`,
     keep `applySecurityHeaders(res, {html:true})` and CSP.
   - `lib/auth.js`: simplify to `isAuthed()=>true`, `requireAuth()=>true` +
     security headers; keep helper names so all api handlers keep working.
   - `api/login.js` / `api/logout.js`: return `{ok:true, open:true}`.
   - Delete `tools/hash-password.mjs`, `tools/verify-auth.mjs`,
     `tools/verify-dracin.mjs`; `.env.example` → secret-free.
7. Sync into repo preserving `.git`/remote:
   `tar` backup first, then `rsync -a --delete --exclude='.git' src/ dest/`.
8. Verify: `node --check` every `.js`; run `tools/dev-server.mjs <port>`;
   check root HTML has no gate and no forbidden strings; hit each API action.

## Vercel deploy saga — RESOLVED 2026-08-04

- Symptom: GitHub status shows `Vercel Deployment failed`, live site still
  serves the OLD Next.js shell (`_next/` present), while local app works.
- Log captured from user: `npm run vercel-build` → "Couldn't find any `pages`
  or `app` directory" → the saved **Framework Preset is still Next.js**.
- `"framework": "other"` in vercel.json is INVALID (target_url pointed at
  project-configuration docs ⇒ config validation error; "other" is not an
  accepted id). Remove it.
- **WORKING FINAL FIX (user confirmed live):**
  1. `vercel.json`: `"buildCommand": "npm run vercel-build"` (keep rewrites +
     `functions.includeFiles: "src/**"`).
  2. `package.json`: add `"vercel-build"` (and `"build"`) scripts that only
     run syntax checks, e.g. `node --check api/index.js && node --check
     api/dracin.js && node --check api/springstream.js`.
  3. Push as the Vercel-linked account (`agenticspring`) — commit author AND
     committer must match or Vercel rejects the deploy.
- After the push, confirm live by fetching the root HTML: no `_next/`, brand
  title, palette color present.
- No-token deploy-state check that works: GitHub commit status API
  `GET /repos/{owner}/{repo}/commits/{sha}/status` (state, description,
  `dpl_...` id, target_url). target_url = docs/project-configuration ⇒ config
  validation; target_url = deployment page ⇒ build failure.
