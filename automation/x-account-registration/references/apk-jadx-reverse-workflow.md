# APK → endpoint reverse workflow (jadx), as used on X Android 12.23.1

Reusable recipe for pulling a mobile app's signup/recon API surface out of an APK.
Worked end-to-end on `com.twitter.android` (X 12.23.1-prod.01, Sep 2026).

## 1. Get and unpack

APKPure/`d.apkpure.com` links are Cloudflare-gated — `curl` returns 403. Either drive a
real browser session, or have the user download the XAPK manually and drop it in the
project dir. An `.xapk`/`.apks` is just a zip:

```bash
python3 - <<'EOF'
import zipfile, os
z = zipfile.ZipFile('App.xapk'); z.extractall('apk_extracted')
print([f for f in os.listdir('apk_extracted') if f.endswith('.apk')])
EOF
```

The base APK is the large `*.apk` (e.g. `com.twitter.android.apk`, 118 MB); `config.*.apk`
files are split resource/locale/ABI APKs. Unzip the base to get the `classes*.dex` set.

## 2. jadx — the flag that actually breaks the run

Download the release zip, unzip, use `bin/jadx`. **JVM memory is not an argument** — jadx
rejects `-Xmx2g` with `Unknown option: -Xmx2g` and then silently produces **0 files**,
which reads like a decode failure rather than a CLI error. Pass it via env instead:

```bash
export JADX_OPTS="-XX:MaxRAMPercentage=40.0"   # default is 70% — OOMs when run side by side
/tmp/jadx/bin/jadx -d out_dir classes.dex --no-res
```

`-Xmx` placement is the single most common way to waste a decode cycle here — always check
the output dir for actual `.java` count, not just the exit code.

## 3. Decode per-dex, sequentially on a small box

A big app has 8–12 dex files and a full-APK decode can run 15+ minutes or get OOM-killed.
Decoding **one dex per invocation** is dramatically faster per unit and lets you prioritise:

```bash
for d in classes.dex classes3.dex classes4.dex classes5.dex; do
  /tmp/jadx/bin/jadx -d "jadx_${d%.dex}" "$d" --no-res
done
```

On a ~8 GB box run them **sequentially** — parallel jadx invocations at the default 70%
heap get OOM-killed (`exit_code=-9`) and leave empty output dirs. ~30–60 s per dex.

## 4. Where the API surface actually lives

| You want | Grep target |
|---|---|
| Endpoint paths | Retrofit interfaces: `@retrofit2.http.o("/path")` → POST, `@retrofit2.http.f("/path")` → GET (confirm against real traffic — don't assume) |
| Request/response **wire field names** | generated Moshi adapters: `y.a(new String[]{...})` inside `*JsonAdapter.java` |
| Feature structure | package dirs (`com/x/login/subtasks/*`) |

The generated JSON adapters are the highest-value artifact: they list the exact snake_case
JSON keys the server expects, which is what you need for a working request. Thrift/`$$serializer`
classes frequently fail to decompile, but the `*JsonAdapter` for the same struct usually
still lands and gives you the field names anyway.

Working example (X onboarding, `com/x/http/k.java`):

```
POST /1.1/onboarding/task.json               (TaskRequest -> TaskResponse)
POST /1.1/onboarding/begin_verification.json (BeginVerificationRequest -> …)
GET  /i/users/email_available.json?email=&lang=
```
with `TaskRequest` JSON keys `flow_name, flow_token, subtask_inputs, input_flow_data,
sim_country_code, subtask_versions`, and base URL `https://api.x.com/`.

Quick endpoint sweep without decompiling — `strings` over every dex catches literal paths:

```bash
for d in classes*.dex; do strings -n 12 "$d" | grep -E '^/(i/|1\.1/|graphql/)'; done | sort -u
```

## 5. Static analysis is structure, not proof

Static gives you routes, models and *candidate* hosts. It does **not** give you the method,
headers, auth or runtime gating — an endpoint can be present in the binary and still be
refused by the server. Say so explicitly when reporting; never present a route found in a
dex as a working flow. Confirm by driving the real API and reading the response.

## 6. Host-side gotchas that cost real time

- **Guest tokens need cookies first.** `POST /1.1/guest/activate.json` returns 401 if you
  call it cold. `GET https://x.com/` first (it answers 401 but sets `guest_id`/`twid`), then
  activate succeeds. Don't read the 401 on the home request as "blocked".
- Bearer tokens live in the web JS bundle, not the app dex. The web bearer was unchanged
  from the previously-saved value — check the existing constant before assuming it rotated.
- The site's JS moved from `ondemand.s{N}.tls.js` to an `x-web/entry-client-*.js` loader
  whose real code is in separately-imported chunks (`x-web/x-web/assets/*.js`). Any helper
  that pattern-matches the old ondemand path breaks; fetch the loader and read its
  dependency list.
- Thrift/obfuscated client methods decompile to
  `throw new UnsupportedOperationException("Method not decompiled...")`. Don't burn time on
  them — the interface + adapter layer above is enough to reconstruct the wire format.
