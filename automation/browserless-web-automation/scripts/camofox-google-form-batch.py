#!/usr/bin/env python3
"""Batch Google Form submission through Camofox CLI.

Usage:
  python3 camofox-google-form-batch.py [START_INDEX [END_INDEX]]

Files (adjust paths in CONFIG):
  mapping.json  -> [{"set": N, "handle": "...", "address": "0x..."}, ...]
  reasons.json  -> {"<set>": "unique reason string", ...}
  results.json  -> written with per-entry status

Each entry: close tab -> open fresh form -> snapshot -> fill -> tick ->
submit -> verify confirmation page. No blind retries; stops on first
non-confirmed status so partial results are inspectable.
"""
import json, re, subprocess, sys, time
from pathlib import Path

CAMOFOX = "camofox"
FORM_URL = "https://docs.google.com/forms/d/e/<FORM_ID>/viewform"
MAPPING_PATH = "/root/projects/<name>/mapping.json"
REASONS_PATH = "/root/projects/<name>/reasons.json"
RESULTS_PATH = "/root/projects/<name>/results.json"

REASONS = json.loads(Path(REASONS_PATH).read_text())

CONFIRM_RE = re.compile(
    r"odpowied\u017a zosta\u0142a zapisana|Your response has been recorded|"
    r"odpowied\u017a zosta\u0142a zarejestrowana",
    re.I,
)
FAIL_RE = re.compile(
    r"data-validation-failed|Nie uda\u0142o si\u0119|There was a problem|This form",
    re.I,
)


def run(*args, timeout=60):
    r = subprocess.run([CAMOFOX, *args], capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def get_refs(snapshot):
    """Map form field labels to Camofox refs from a snapshot dump.

    Form-specific: adjust the label matchers to the target form. The generic
    pattern is `(textbox|checkbox|radio|button|link) "label" [eN]`.
    """
    refs = {}
    for m in re.finditer(r'(?:textbox|checkbox|radio|button|link) "([^"]*)" \[(e\d+)\]', snapshot):
        label = m.group(1).strip()
        ref = m.group(2)
        if label.startswith("Drop X handle"):
            refs["handle"] = ref
        elif label.startswith("Drop EVM wallet"):
            refs["wallet"] = ref
        elif label.startswith("Why HypzClub"):
            refs["reason"] = ref
        elif label.startswith("Yes") and "checkbox" in m.group(0):
            refs["yes"] = ref
        elif label.startswith("Done"):
            refs["done"] = ref
        elif label.startswith("I understand"):
            refs["understand"] = ref
        elif label.startswith("Prze\u015blij") and "button" in m.group(0):
            refs["submit"] = ref
    return refs


def submit_one(entry):
    handle, address, set_no = entry["handle"], entry["address"], entry["set"]
    reason = REASONS.get(str(set_no), "")
    run("close")  # camofox caps open tabs; ignore close errors
    rc, _, _ = run("open", FORM_URL)
    if rc != 0:
        return "error_open"
    time.sleep(2.0)
    rc, snap, _ = run("snapshot")
    if rc != 0:
        return "error_snapshot"
    refs = get_refs(snap)
    need = ["handle", "wallet", "reason", "yes", "done", "understand", "submit"]
    missing = [k for k in need if k not in refs]
    if missing:
        return f"error_missing_refs:{','.join(missing)}"
    fill = f'[{refs["handle"]}]="{handle}" [{refs["wallet"]}]="{address}" [{refs["reason"]}]="{reason}"'
    rc, _, _ = run("fill", fill)
    if rc != 0:
        return "error_fill"
    for key in ("yes", "done", "understand"):
        rc, _, _ = run("click", refs[key])
        if rc != 0:
            return f"error_click_{key}"
    rc, _, _ = run("click", refs["submit"])
    if rc != 0:
        return "error_submit_click"
    time.sleep(3.0)
    rc, snap2, _ = run("snapshot")
    if rc != 0:
        return "error_snapshot_after"
    if CONFIRM_RE.search(snap2):
        return "confirmed"
    if FAIL_RE.search(snap2):
        return "failed_page"
    return "unknown_after_submit"


def main():
    mapping = json.loads(Path(MAPPING_PATH).read_text())
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end = int(sys.argv[2]) if len(sys.argv) > 2 else len(mapping)
    results = []
    for i, entry in enumerate(mapping[start:end], start=start):
        status = submit_one(entry)
        results.append(
            {"index": i, "set": entry["set"], "handle": entry["handle"],
             "address": entry["address"], "status": status}
        )
        print(f"[{i+1}/{len(mapping)}] set={entry['set']} handle={entry['handle']} status={status}", flush=True)
        if status != "confirmed":
            break  # stop on first hard failure; no blind retries
        time.sleep(1.5)
    Path(RESULTS_PATH).write_text(json.dumps(results, indent=2))
    ok = sum(1 for r in results if r["status"] == "confirmed")
    print(f"DONE confirmed={ok} total_attempted={len(results)}", flush=True)


if __name__ == "__main__":
    main()
