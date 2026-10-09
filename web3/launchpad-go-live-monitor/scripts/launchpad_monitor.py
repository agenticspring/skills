#!/usr/bin/env python3
"""Launchpad go-live / contract-file change watchdog.

Watchdog pattern for cronjob(no_agent=true): prints ONLY on change.
Empty stdout = silent (nothing delivered); non-empty stdout is delivered
verbatim by the scheduler.

Monitors three surfaces:
  1. SITE_URL homepage HTML (CSP nonces stripped before hashing)
  2. GitHub latest commit SHA for a contracts file path
  3. Raw contracts file content hash (new launcher/strategy/factory registrations)

First run seeds the baseline and stays silent. Subsequent runs diff and report.
Edit the CONFIG block for the target. Store at ~/.hermes/scripts/<name>.py.
"""
import hashlib, json, os, re, urllib.request

# ---------- CONFIG ----------
SITE_URL = "https://example.trade"
GH_REPO = "org/repo"
GH_PATH = "path/to/contracts.ts"
STATE = os.path.expanduser("~/.hermes/scripts/example_state.json")
# ----------------------------

GH_RAW = f"https://raw.githubusercontent.com/{GH_REPO}/main/{GH_PATH}"
GH_COMMITS = f"https://api.github.com/repos/{GH_REPO}/commits?path={GH_PATH}&per_page=1"
UA = {"User-Agent": "Mozilla/5.0"}

def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")

def main():
    state = {}
    if os.path.exists(STATE):
        try:
            state = json.load(open(STATE))
        except Exception:
            state = {}
    changes = []
    new_state = {}

    # 1. Site HTML — strip CSP nonces (random per request) or every poll fires
    try:
        html = get(SITE_URL)
        title_m = re.search(r"<title>([^<]*)</title>", html)
        title = title_m.group(1) if title_m else ""
        desc_m = re.search(r'name="description" content="([^"]*)"', html)
        desc = desc_m.group(1) if desc_m else ""
        teaser = "Coming soon" in html
        html = re.sub(r'nonce="[^"]+"', "NONCE", html)
        h = hashlib.sha256(html.encode()).hexdigest()[:16]
        old = state.get("site_hash")
        if old is not None and old != h:
            changes.append(
                f"{SITE_URL} CHANGED: title={title!r} desc={desc!r} "
                f"teaser={'YES' if teaser else 'NO (LIVE?)'}"
            )
        new_state["site_hash"] = h
        new_state["site_title"] = title
        new_state["site_desc"] = desc
        new_state["site_teaser"] = teaser
    except Exception:
        pass  # silent on fetch failure

    # 2. GitHub latest commit for the contracts file
    try:
        data = get(GH_COMMITS)
        commits = json.loads(data)
        if isinstance(commits, list) and commits:
            sha = commits[0]["sha"]
            date = commits[0]["commit"]["author"]["date"]
            msg = commits[0]["commit"]["message"].split("\n")[0]
            old = state.get("gh_sha")
            if old is not None and old != sha:
                changes.append(f"GitHub {GH_PATH} UPDATED: {sha[:10]} @ {date} — {msg}")
            new_state["gh_sha"] = sha
            new_state["gh_msg"] = msg
            new_state["gh_date"] = date
    except Exception:
        pass

    # 3. Raw file content hash — catches address registrations without a path commit
    try:
        raw = get(GH_RAW)
        rh = hashlib.sha256(raw.encode()).hexdigest()[:16]
        old = state.get("raw_hash")
        if old is not None and old != rh:
            changes.append(f"{GH_PATH} CONTENT changed (hash {old} → {rh})")
        new_state["raw_hash"] = rh
    except Exception:
        pass

    try:
        json.dump(new_state, open(STATE, "w"))
    except Exception:
        pass

    if changes:
        print("🔔 MONITOR — update terdeteksi:")
        for c in changes:
            print("•", c)
        print(f"\nDetail: {SITE_URL} | {GH_RAW}")

if __name__ == "__main__":
    main()
