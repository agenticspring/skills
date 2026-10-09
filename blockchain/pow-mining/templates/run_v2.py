#!/usr/bin/env python3
"""
Hashwood V2 Miner — web3.py persistent connection, private RPC, TX receipt checking.
~5x faster TX submission than subprocess cast (no process spawn overhead).

Usage:
  export PRIVATE_KEY=0x...
  python3 run_v2.py

Or: echo -n '0xPRIVATEKEY' > .env && python3 run_v2.py
"""
import subprocess, sys, os, time
from pathlib import Path
from web3 import Web3

# ── CONFIG ──
RPC = "https://rpc.mainnet.chain.robinhood.com"  # change to private RPC for speed
CONTRACT = "0xD69be8d7c6d0e8216Dc2C151834E4150313260Cc"
MINER = "/root/hashwood-miner/hashminer.py"
NTHREADS = 6
HERE = Path(__file__).parent

w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={'timeout': 10}))

# ── Function selectors (verify with: cast sig '<funcname>') ──
SELECTOR_CHALLENGE    = '0x8ae0368b'  # challengeNumber()
SELECTOR_TARGET       = '0x8a769d35'  # miningTarget()
SELECTOR_CHECK_SOL    = '0x9d7a7cc6'  # checkMintSolution(uint256,address)
SELECTOR_MINT         = '0x1801fbe5'  # mint(uint256,bytes32)

def load_pk():
    key = os.environ.get('PRIVATE_KEY') or HERE.joinpath('.env').read_text().strip()
    return key

def get_work():
    try:
        challenge = w3.eth.call({'to': CONTRACT, 'data': SELECTOR_CHALLENGE})
        target = w3.eth.call({'to': CONTRACT, 'data': SELECTOR_TARGET})
        return challenge.hex(), str(int.from_bytes(target, 'big'))
    except Exception as e:
        print(f"  ! RPC error: {e}")
        return None, None

def mine(challenge, address, target):
    r = subprocess.run(
        [sys.executable, MINER, challenge, address[2:], target, str(NTHREADS)],
        capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        return None, None
    parts = r.stdout.strip().split()
    if len(parts) < 2:
        return None, None
    return f"0x{parts[0]}", parts[1]  # nonce with 0x prefix

def check_solution(nonce_hex, addr):
    """web3 eth_call — instant, no subprocess overhead"""
    data = SELECTOR_CHECK_SOL + nonce_hex[2:].zfill(64) + addr[2:].lower().zfill(64)
    try:
        result = w3.eth.call({'to': CONTRACT, 'data': data})
        return int.from_bytes(result, 'big') == 1
    except:
        return False

def submit_tx(nonce_hex, digest_hex, pk):
    """Build + sign + send raw TX. Returns 'MINTED: hash' or 'REVERTED: hash' or 'FAIL: msg'"""
    acct = w3.eth.account.from_key(pk)
    addr = acct.address
    data = SELECTOR_MINT + nonce_hex[2:].zfill(64) + ("0x" + digest_hex)[2:].zfill(64)

    try:
        nonce = w3.eth.get_transaction_count(addr, 'pending')
        tx = {
            'to': CONTRACT,
            'value': 50000000000000,  # 0.00005 ETH
            'data': data,
            'nonce': nonce,
            'chainId': 4663,
            'gas': 50000,
            'maxFeePerGas': w3.to_wei(10, 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(0.1, 'gwei'),
        }
        signed = w3.eth.account.sign_transaction(tx, pk)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
        status = "MINTED" if receipt['status'] == 1 else "REVERTED"
        return f"{status}: {tx_hash[:20]}..."
    except Exception as e:
        return f"FAIL: {str(e)[:100]}"

def main():
    pk = load_pk()
    acct = w3.eth.account.from_key(pk)
    addr = acct.address

    print(f"=== Hashwood V2 — Fast TX ===")
    print(f"Address: {addr}")
    print(f"Connected: {w3.is_connected()}")
    print(f"Balance: {w3.from_wei(w3.eth.get_balance(addr), 'ether'):.6f} ETH\n")

    while True:
        try:
            challenge, target = get_work()
            if not challenge:
                time.sleep(2); continue
            print(f"[{time.strftime('%H:%M:%S')}] Work: {challenge[:18]}...")

            ts = time.time()
            nonce_hex, digest_hex = mine(challenge, addr, target)
            elapsed = time.time() - ts

            if nonce_hex and digest_hex:
                print(f"  ✓ Solution! nonce={nonce_hex} ({elapsed:.1f}s)")
                if check_solution(nonce_hex, addr):
                    print(f"  → {submit_tx(nonce_hex, digest_hex, pk)}")
                else:
                    print(f"  ✗ Expired (challenge changed)")
            else:
                print(f"  ✗ No solution")
        except KeyboardInterrupt:
            print("\nStopped."); break
        except Exception as e:
            print(f"  ! {e}"); time.sleep(1)

if __name__ == "__main__":
    main()
