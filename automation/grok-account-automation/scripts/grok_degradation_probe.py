#!/usr/bin/env python3
"""Model degradation probe for Grok accounts.

A bfs:1 (bot-flagged) account is served a DOWNGRADED model (Grok-1/Grok-2)
even though the request says grok-4.5. The fastest way to detect this is to
ask the model its exact ID and check for a reasoning field.

Run against a 9Router grok-cli pool, or point TOKEN at a direct OAuth token
for a single account (then use cli-chat-proxy.grok.com directly).

Usage:
  python3 grok_degradation_probe.py            # uses 9Router /v1/chat/completions
"""
import json
import sqlite3
import subprocess
import sys
import base64

try:
    from curl_cffi import requests
except ImportError:
    import requests


def get_9router_key():
    TOKEN = subprocess.check_output(
        "echo -n \"$(cat ~/.9router/machine-id)9r-cli-auth$(cat ~/.9router/auth/cli-secret)\" | sha256sum | cut -c1-16",
        shell=True).decode().strip()
    r = requests.get("http://localhost:20128/api/keys",
                     headers={"x-9r-cli-token": TOKEN}, timeout=10)
    return r.json()["keys"][0]["key"]


def chat_completions(api_key, model, prompt, base="http://localhost:20128/v1/chat/completions"):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
    }
    r = requests.post(base, json=body,
                      headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                      timeout=180)
    try:
        d = r.json()
        msg = d.get("choices", [{}])[0].get("message", {})
        content = msg.get("content", "")
        reasoning = msg.get("reasoning") or msg.get("reasoning_content")
        return r.status_code, content, reasoning, d.get("model")
    except Exception:
        return r.status_code, r.text[:300], None, None


def decode_jwt(token):
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return None


def check_9router_pool():
    key = get_9router_key()
    print("=== Model identity probes via 9Router ===")
    for model in ["gcli/grok-4.5", "gcli/grok-4.5-high", "gcli/grok-4.5-medium", "gcli/grok-4.5-xhigh"]:
        st, content, reasoning, served = chat_completions(key, model, "What is your exact internal model ID and version? One sentence.")
        print(f"{model:24}: http={st} served_as={served} reasoning_field={'YES' if reasoning else 'no'}")
        print(f"    answer: {content[:140]!r}")

    print("\n=== Which connections are flagged (bfs in OAuth access token)? ===")
    db = sqlite3.connect("file:/root/.9router/db/data.sqlite?mode=ro", uri=True)
    rows = db.execute("SELECT data FROM providerConnections WHERE provider='grok-cli'").fetchall()
    db.close()
    for r in rows:
        d = json.loads(r[0])
        at = d.get("accessToken", "")
        p = decode_jwt(at) if at.startswith("eyJ") else None
        email = d.get("providerSpecificData", {}).get("email", "?")
        print(f"  {email:38} bfs={p.get('bfs') if p else '?'}")


def check_direct(token):
    """Probe a single OAuth access token directly against cli-chat-proxy.grok.com."""
    import os
    proxy_line = os.environ.get("GROK_PROXY", "<PROXY_IP_REDACTED>:3129:82v458jh2v0e:pnkxj33es7bkruq")
    parts = proxy_line.split(":")
    proxy_url = f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    proxy = {"http": proxy_url, "https": proxy_url}
    s = requests.Session(impersonate="chrome124")
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-grok-client-identifier": "9router",
        "x-grok-client-version": "0.5.18",
    })
    body = {
        "model": "grok-4.5",
        "input": "What is your exact internal model ID and version? One word. Format: MODEL=<id>",
        "reasoning": {"effort": "xhigh"},
        "stream": False,
    }
    rr = s.post("https://cli-chat-proxy.grok.com/v1/responses", json=body, timeout=120, proxies=proxy)
    d = rr.json()
    output = d.get("output", [])
    text = ""
    for o in output:
        for c in o.get("content", []):
            if c.get("type") == "output_text":
                text += c.get("text", "")
    print(f"direct probe: http={rr.status_code} model_field={d.get('model')} reasoning_echo={d.get('reasoning')}")
    print(f"  model self-ID: {text!r}")
    print("  DEGRADED if self-ID is 'unknown'/'grok-1'/'grok-2' or says grok-4.5 doesn't exist")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--direct" and len(sys.argv) > 2:
        check_direct(sys.argv[2])
    else:
        check_9router_pool()
