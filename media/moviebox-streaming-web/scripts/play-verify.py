#!/usr/bin/env python3
"""Playwright click-through play verification for MovieBox watch pages.

Why this exists: the cloud browser tool renders empty/about:blank on
iframe-heavy pages, and Dez requires a REAL click test ("Pastikan kau klik
video play nya"), not just curl-200s. This script loads the watch page,
waits for the player iframe, clicks the video center (play), reads playback
state (paused/currentTime/readyState), tests pause->play again (ad-trap),
and counts ad-network hits. It also screenshots the instant the iframe
appears — because provider anti-bot (2embed/vidsrc) can blank the page
shortly after (pitfall 25), so the screenshot may be the only visual proof.

Usage (through the `terminal` tool):
    playwright install chromium        # once
    python3 scripts/play-verify.py [URL] [PROVIDER_TAG] [WAIT_SECONDS]

Example:
    python3 scripts/play-verify.py https://moviebox-wine-ten.vercel.app/watch/movie/557 p0 25

Known limits (be honest in the report):
- From a datacenter IP, provider anti-bot may blank the page after the iframe
  appears (window.top = about:blank). If iframe_found_at is set but the body
  then empties, that's anti-bot, not a dead app — say so and ask the user to
  confirm the final click from their residential IP.
- 2embed's player logs console noise ("You don't have permission to use
  DEVTOOL!", console.clear/table spam). That noise is actually PROOF the
  player loaded before any blank.
- A clean parent probe is NOT proof the provider player is ad-free (popups
  inside a cross-origin nested iframe are invisible to the parent); the
  durable anti-ad guarantee is serving that provider through /api/embed-proxy.
"""
import sys, time, json
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://moviebox-wine-ten.vercel.app/watch/movie/557"
TAG = sys.argv[2] if len(sys.argv) > 2 else "play"
WAIT = int(sys.argv[3]) if len(sys.argv) > 3 else 25

STEALTH = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
window.chrome = window.chrome || { runtime: {} };
Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
"""

AD_RE = ["adsterra","popads","popcash","doubleclick","googlesyndication","exoclick",
         "juicyads","monetag","tagivi","llvpn","propellerads","ad-maven","onclckmn",
         "shopee","play.google","blibli","tokopedia"]

out = {"tag": TAG, "url": URL}
ads = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
        "--no-sandbox", "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
    ctx.add_init_script(STEALTH)
    page = ctx.new_page()
    try:
        s = ctx.new_cdp_session(page)
        s.send("Page.addScriptToEvaluateOnNewDocument",
               {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"})
    except Exception:
        pass
    page.on("request", lambda r: ads.append(r.url) if any(a in r.url.lower() for a in AD_RE) else None)

    page.goto(URL, timeout=30000, wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass

    # 1) wait for player iframe, screenshot the instant it appears (anti-bot may blank after)
    ifr = None
    for i in range(max(1, WAIT // 2)):
        time.sleep(2)
        try:
            if page.locator('iframe[title="player"]').count() > 0:
                ifr = page.locator('iframe[title="player"]').first
                out["iframe_found_at"] = i * 2
                try:
                    page.screenshot(path=f"/tmp/mb_{TAG}_iframe.png")
                except Exception:
                    pass
                try:
                    out["iframe_src"] = (ifr.get_attribute("src") or "")[:130]
                except Exception:
                    pass
                break
        except Exception:
            pass
    if not ifr:
        out["error"] = "no iframe; body=" + repr(page.inner_text("body")[:150])
        browser.close()
        print(json.dumps(out, indent=1))
        sys.exit(1)

    # 2) find <video> inside the iframe (provider takes time to init)
    video = None
    for i in range(max(1, WAIT // 2)):
        try:
            v = ifr.frame_locator("video").first
            v.wait_for(timeout=2000)
            video = v
            out["video_found_at"] = 2 + i * 2
            break
        except Exception:
            time.sleep(2)
    if not video:
        out["error"] = "no video in iframe; iframe_body=" + repr((ifr.inner_text() or "")[:150])
        browser.close()
        print(json.dumps(out, indent=1))
        sys.exit(1)

    # 3) click play, read state
    try:
        box = video.bounding_box()
        if box:
            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    except Exception as e:
        out["click_err"] = str(e)[:100]
    time.sleep(6)
    st = video.evaluate("(v) => ({paused: v.paused, currentTime: Math.round(v.currentTime*10)/10, readyState: v.readyState, duration: v.duration?Math.round(v.duration):0, err: v.error?v.error.message:null})")
    out["state"] = st
    out["play_ok"] = (not st["paused"]) or st["currentTime"] > 0

    # 4) pause -> play again (ad-trap probe)
    time.sleep(2)
    try:
        box = video.bounding_box()
        if box:
            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            time.sleep(2)
            s1 = video.evaluate("(v) => ({paused: v.paused, currentTime: Math.round(v.currentTime*10)/10})")
            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            time.sleep(5)
            s2 = video.evaluate("(v) => ({paused: v.paused, currentTime: Math.round(v.currentTime*10)/10})")
            out["pause"] = s1
            out["replay"] = s2
            out["pause_play_ok"] = (not s2["paused"]) or s2["currentTime"] > s1["currentTime"]
    except Exception as e:
        out["pause_err"] = str(e)[:100]

    out["ads_seen"] = list(dict.fromkeys(ads))[:8]
    try:
        page.screenshot(path=f"/tmp/mb_{TAG}.png")
    except Exception:
        pass
    browser.close()

print(json.dumps(out, indent=1))
