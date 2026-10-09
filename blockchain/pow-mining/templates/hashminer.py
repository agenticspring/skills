#!/usr/bin/env python3
"""
Hashwood Python Miner — fast keccak256 PoW miner.
Uses pycryptodome C-accelerated keccak256 (~80x faster than Node.js reference).
Usage: python3 hashminer.py <challenge_hex> <address_hex> <target_hex|dec> [threads]
Output: nonce_hex digest_hex

CRITICAL — nonce byte order:
The 32-byte nonce field must have the 8-byte nonce RIGHT-JUSTIFIED (last 8 bytes)
with 24 leading zero bytes: 0x000000000000000000000000000000000000000000000000xxxxxxxxxxxxxxxx
Left-justifying produces wrong hashes that checkMintSolution() rejects.
"""
import sys, os
from multiprocessing import Process, Value, Array, Lock
from Crypto.Hash import keccak

MSG_LEN = 84  # challenge(32) + address(20) + nonce(32)

def keccak256(data):
    k = keccak.new(digest_bits=256)
    k.update(data)
    return k.digest()

def worker(challenge, address, target_bytes, start_nonce, end_nonce,
           found, found_nonce, found_digest, lock):
    msg = bytearray(MSG_LEN)
    msg[:32] = challenge
    msg[32:52] = address

    for nonce in range(start_nonce, end_nonce):
        if found.value:
            return
        # CRITICAL: nonce goes in LAST 8 bytes (right-justified), NOT the first 8
        msg[76:84] = nonce.to_bytes(8, 'big')
        msg[52:76] = b'\x00' * 24
        d = keccak256(bytes(msg))
        if d <= target_bytes:
            with lock:
                if not found.value:
                    found.value = 1
                    found_nonce.value = nonce
                    found_digest[:32] = d[:32]
            return

def main():
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <challenge_hex> <address_hex> <target> [threads]")
        sys.exit(1)

    challenge = bytes.fromhex(sys.argv[1].removeprefix('0x'))
    address = bytes.fromhex(sys.argv[2].removeprefix('0x'))
    target_str = sys.argv[3].split()[0]

    if target_str.startswith('0x'):
        target_bytes = bytes.fromhex(target_str[2:].zfill(64))
    else:
        target_bytes = int(target_str).to_bytes(32, 'big')

    nthreads = int(sys.argv[4]) if len(sys.argv) > 4 else os.cpu_count() or 4
    BATCH = 500_000
    import random

    found = Value('b', 0)
    found_nonce = Value('Q', 0)
    found_digest = Array('B', [0]*32)
    lock = Lock()

    while not found.value:
        base = random.randint(0, 2**63)
        range_per = BATCH // nthreads
        procs = []
        for i in range(nthreads):
            sn = base + i * range_per
            p = Process(target=worker, args=(challenge, address, target_bytes,
                        sn, sn + range_per, found, found_nonce, found_digest, lock))
            procs.append(p)
            p.start()
        for p in procs:
            p.join()

    print(f"{found_nonce.value:x} {bytes(found_digest[:32]).hex()}")

if __name__ == '__main__':
    main()
