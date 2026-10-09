#!/usr/bin/env python3
"""
Full Hashwood miner: fetch work → mine → submit → loop.
Wraps hashminer.py with RPC polling and cast TX submission.
"""
import subprocess, sys, os, time
from pathlib import Path

RPC = "https://rpc.mainnet.chain.robinhood.com"
CONTRACT = "0xD69be8d7c6d0e8216Dc2C151834E4150313260Cc"
MINER = "/root/hashwood-miner/hashminer.py"
NTHREADS = 6  # adjust to VPS core count
HERE = Path(__file__).parent

def load_pk():
    return HERE.joinpath(".env").read_text().strip()

def run_cast(*args):
    env = os.environ.copy()
    env["PATH"] = f"{Path.home()}/.foundry/bin:{env.get('PATH', '')}"
    r = subprocess.run(["cast"] + list(args), capture_output=True, text=True, timeout=15, env=env)
    return r.stdout.strip()

def get_work():
    c = run_cast("call", CONTRACT, "challengeNumber()(bytes32)", "--rpc-url", RPC)
    t = run_cast("call", CONTRACT, "miningTarget()(uint256)", "--rpc-url", RPC)
    return c, t

def mine(challenge, address, target):
    r = subprocess.run(
        [sys.executable, MINER, challenge, address[2:], target, str(NTHREADS)],
        capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        return None, None
    parts = r.stdout.strip().split()
    return parts[0] if len(parts) >= 2 else None, parts[1] if len(parts) >= 2 else None

def submit(nonce, digest, pk):
    return run_cast("send", CONTRACT, "mint(uint256,bytes32)", nonce, f"0x{digest}",
                    "--value", "50000000000000",
                    "--private-key", pk, "--rpc-url", RPC)

def main():
    pk = load_pk()
    addr = run_cast("wallet", "address", "--private-key", pk)
    print(f"=== Hashwood PyMiner ===\nAddress: {addr}\nThreads: {NTHREADS}\n")

    while True:
        try:
            challenge, target = get_work()
            print(f"[{time.strftime('%H:%M:%S')}] Work: {challenge[:18]}... target={target.split()[0][:12]}...")
            ts = time.time()
            nonce, digest = mine(challenge, addr, target)
            elapsed = time.time() - ts
            if nonce and digest:
                print(f"  ✓ Solution! nonce={nonce} ({elapsed:.1f}s)")
                tx = submit(f"0x{nonce}", digest, pk)
                print(f"  TX: {tx[:80]}...")
            else:
                print(f"  ✗ No solution")
                c2, _ = get_work()
                if c2 != challenge:
                    print(f"  → Challenge changed (someone else mined)")
        except KeyboardInterrupt:
            print("\nStopped."); break
        except Exception as e:
            print(f"  ! Error: {e}"); time.sleep(2)

if __name__ == "__main__":
    main()
