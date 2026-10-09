#!/usr/bin/env python3
"""Full Hashwood miner wrapper: fetch work → mine → submit → loop"""
import subprocess, sys, os, time
from pathlib import Path

RPC = "https://rpc.mainnet.chain.robinhood.com"
CONTRACT = "0xD69be8d7c6d0e8216Dc2C151834E4150313260Cc"
MINER = "/root/hashwood-miner/hashminer.py"
NTHREADS = 6
HERE = Path(__file__).parent

def load_pk():
    return HERE.joinpath(".env").read_text().strip()

def run_cast(*args):
    env = os.environ.copy()
    env["PATH"] = f"{Path.home()}/.foundry/bin:{env.get('PATH', '')}"
    r = subprocess.run(["cast"] + list(args), capture_output=True, text=True, timeout=15, env=env)
    return r.stdout.strip()

def get_work():
    challenge = run_cast("call", CONTRACT, "challengeNumber()(bytes32)", "--rpc-url", RPC)
    target = run_cast("call", CONTRACT, "miningTarget()(uint256)", "--rpc-url", RPC)
    return challenge, target

def mine(challenge, address, target):
    r = subprocess.run(
        [sys.executable, MINER, challenge, address[2:], target, str(NTHREADS)],
        capture_output=True, text=True, timeout=300
    )
    if r.returncode != 0:
        return None, None
    parts = r.stdout.strip().split()
    if len(parts) < 2:
        return None, None
    return parts[0], parts[1]

def submit(nonce, digest, pk):
    r = run_cast("send", CONTRACT, f"mint(uint256,bytes32)", nonce, f"0x{digest}",
                 "--value", "50000000000000",
                 "--private-key", pk,
                 "--rpc-url", RPC)
    return r

def main():
    pk = load_pk()
    addr = run_cast("wallet", "address", "--private-key", pk)
    print(f"=== Hashwood PyMiner ===\nAddress: {addr}\nThreads: {NTHREADS}\nRPC: {RPC}\n")

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
                print(f"  ✗ Mining failed")
                nc, _ = get_work()
                if nc != challenge:
                    print(f"  → Challenge changed (someone else mined)")
        except KeyboardInterrupt:
            print("\nStopped."); break
        except Exception as e:
            print(f"  ! Error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
