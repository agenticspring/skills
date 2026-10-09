#!/usr/bin/env python3
"""Generic launchpad change watchdog.

Watchdog contract: SILENT (empty stdout, exit 0) when nothing changed;
prints a diff report only on change. First run initializes the baseline
JSON and stays silent. Designed for `cronjob` no_agent=true.

Edit the CONFIG block for the target launchpad, then baseline with:
    python3 launchpad_monitor.py
"""
import hashlib, json, os, re, urllib.request

# ---- CONFIG: edit per target ----
SITE_URL   = "https://pools.trade"
GH_REPO    = "Uniswap/sdks"
GH_PATH    = "sdks/liquidity-launcher-sdk/src/addresses.ts"
STATE_FILE = os.path.expanduser("~/.hermes/scripts/launchpad_monitor_state.json")
# Optional: a vanity contract string to flag in raw content (lowercase)
WATCH_SUBSTR = "0000ffffbe8ef"
# -----------------------------------

UA = {"User-Agent": "Mozilla/5.0"}

def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")

def main():
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            state = json.load(open(STATE_FILE))
        except Exception:
            state = {}
    changes = []
    new_state = {}

    # 1. Site homepage: teaser -> live transition, title/desc change
    try:
        html = get(SITE_URL)
        title = "?"
        m = re.search(r"<title>([^<]*)</title>", html)
        if m:
            title = m.group(1)
        m = re.search(r'name="description" content="([^"]*)"', html)
        desc = m.group(1) if m else ""
        teaser = "Coming soon" in html
        h = hashlib.sha256(html.encode()).hexdigest()[:16]
        old = state.get("site_hash")
        if old is not None and old != h:
            changes.append(
                f"site CHANGED: title={title!r} desc={desc!r} "
                f"teaser={'YES' if teaser else 'NO (LIVE?)'}"
            )
        new_state["site_hash"] = h
        new_state["site_title"] = title
        new_state["site_desc"] = desc
        new_state["site_teaser"] = teaser
    except Exception:
        pass  # silent on fetch failure

    # 2. Latest commit SHA for the SDK addresses file
    try:
        data = get(f"https://api.github.com/repos/{GH_REPO}/commits?path={GH_PATH}&per_page=1")
        commits = json.loads(data)
        if isinstance(commits, list) and commits:
            sha = commits[0]["sha"]
            date = commits[0]["commit"]["author"]["date"]
            msg = commits[0]["commit"]["message"].split("\n")[0]
            old = state.get("gh_sha")
            if old is not None and old != sha:
                changes.append(f"GitHub {GH_PATH} UPDATED: {sha[:10]} @ {date} - {msg}")
            new_state["gh_sha"] = sha
            new_state["gh_msg"] = msg
            new_state["gh_date"] = date
    except Exception:
        pass

    # 3. Raw addresses file content hash + watched substring
    try:
        raw = get(f"https://raw.githubusercontent.com/{GH_REPO}/main/{GH_PATH}")
        rh = hashlib.sha256(raw.encode()).hexdigest()[:16]
        low = raw.lower()
        watch_hit = WATCH_SUBSTR in low
        old = state.get("raw_hash")
        if old is not None and old != rh:
            changes.append(
                f"raw {GH_PATH} CONTENT changed (hash {old} -> {rh}); "
                f"watch {WATCH_SUBSTR}: {watch_hit}"
            )
        new_state["raw_hash"] = rh
        new_state["watch_hit"] = watch_hit
    except Exception:
        pass

    try:
        json.dump(new_state, open(STATE_FILE, "w"))
    except Exception:
        pass

    if changes:
        print("MONITOR ALERT - update detected:")
        for c in changes:
            print("*", c)

if __name__ == "__main__":
    main()
