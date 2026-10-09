#!/usr/bin/env python3
"""Kill a runner the moment it is flagged, so a bad region/history contradiction
cannot burn the day's claim quota.

WHY THIS EXISTS
---------------
Many game runners retry a rejected action forever with no fail cap (`fails++`,
`sleep(3)`, loop) and their proxy-refresh path is a no-op on a static proxy. So a
single anti-cheat rejection silently burns requests and wall-clock indefinitely.
Observed: a wallet that was relocated between regions was rejected on every open
and the runner just kept retrying; the guard killed it 4 s after the first
rejection and the remaining daily quota stayed intact.

The guard is deliberately a SEPARATE process from the runner and from any
supervisor that restarts dead runners — see the skill's R5/R6. If a watchdog is
running, it will resurrect whatever this kills, so disable auto-restart (or kill
the watchdog) first.

USAGE
-----
    python3 anticheat_guard.py --log /path/slotG1.log \
        --flag suspicious_movement --flag "review DENIED" --flag "[STOP]" \
        --stop-cmd "systemctl --user stop gocollect-G1"

Exit codes: 0 clean/flags handled, 2 usage error.
Runs until a flag fires, the log reports a normal finish, or --timeout elapses.
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time

# Markers that mean "this run is finished, stop watching".
DONE_MARKERS = ("[done]", "daily limit reached", "quota exhausted")


def logline(path: str | None, msg: str) -> None:
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(line, flush=True)
    if path:
        try:
            with open(path, "a") as f:
                f.write(line + "\n")
        except Exception:
            pass


def find_pid(pattern: str) -> int | None:
    """Return the first PID whose cmdline matches, excluding our own process tree."""
    try:
        out = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True).stdout
    except Exception:
        return None
    me = {os.getpid(), os.getppid()}
    for tok in out.split():
        try:
            pid = int(tok)
        except ValueError:
            continue
        if pid in me:
            continue
        # never kill a shell wrapper that merely mentions the pattern
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                cmd = f.read().replace(b"\x00", b" ").decode(errors="replace")
        except Exception:
            continue
        if cmd.strip().startswith(("bash -c", "sh -c", "/bin/bash -c")):
            continue
        return pid
    return None


def kill_target(pid: int | None, stop_cmd: str | None, label: str) -> None:
    if stop_cmd:
        subprocess.run(stop_cmd, shell=True, capture_output=True, text=True)
        logline(None, f"{label}: ran stop-cmd: {stop_cmd}")
    if pid:
        for sig, name in ((signal.SIGTERM, "TERM"), (signal.SIGKILL, "KILL")):
            try:
                os.kill(pid, sig)
                logline(None, f"{label}: {name} pid={pid}")
            except ProcessLookupError:
                return
            time.sleep(2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", required=True, help="runner log to tail")
    ap.add_argument("--flag", action="append", default=[],
                    help="substring that means 'stop now' (repeatable)")
    ap.add_argument("--pid-pattern", default=None,
                    help="cmdline pattern of the runner to kill (default: derive from log name)")
    ap.add_argument("--stop-cmd", default=None, help="command to run before killing (e.g. systemctl stop)")
    ap.add_argument("--timeout", type=int, default=43200, help="seconds before the guard gives up")
    ap.add_argument("--guard-log", default=None, help="where to append the guard's own log")
    a = ap.parse_args()

    flags = a.flag or ["suspicious_movement"]
    label = os.path.basename(a.log)
    logline(a.guard_log, f"--- guard armed on {a.log}  flags={flags}  timeout={a.timeout}s ---")

    path = a.log
    start = time.time()
    pos = 0
    if os.path.exists(path):
        pos = os.path.getsize(path)
    else:
        pos = 0

    while time.time() - start < a.timeout:
        try:
            with open(path, "r", errors="replace") as f:
                if os.fstat(f.fileno()).st_size < pos:
                    pos = 0                      # rotated/truncated
                f.seek(pos)
                chunk = f.read()
                pos = f.tell()
        except FileNotFoundError:
            time.sleep(3)                        # runner hasn't written yet — wait quietly
            continue
        except Exception as e:
            logline(a.guard_log, f"read error {e}")
            time.sleep(3)
            continue

        if chunk:
            clean = chunk.replace("\r", "\n")
            for fl in flags:
                if fl in clean:
                    logline(a.guard_log, f"!! FLAGGED on `{fl}` — stopping {label} now")
                    pid = find_pid(a.pid_pattern) if a.pid_pattern else None
                    kill_target(pid, a.stop_cmd, label)
                    logline(a.guard_log, f"guard exiting; quota should be preserved")
                    return 0
            if any(d in clean for d in DONE_MARKERS):
                logline(a.guard_log, f"{label} finished normally — guard exiting")
                return 0
        time.sleep(2)

    logline(a.guard_log, f"guard timeout after {a.timeout}s — {label} may still be running")
    return 0


if __name__ == "__main__":
    sys.exit(main())
