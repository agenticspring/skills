#!/usr/bin/env python3
"""MINECAT-style round-PoW miner + claimer (Robinhood 4663).

Grinds keccak256(seed || addr || nonce8BE) < ticketTarget, submits via
submitWork(uint64) (value 0), then auto-claims when voucher/ticket becomes
claimable (pays mintPriceWei). Stops at wallet cap / --max-mints.

Usage:
  python3 minecat-auto.py [--max-mints 3]
  # Set CONTRACT / ADDR / PK_FILE / RPC before running.

Requires: pycryptodome, cast, /dev/shm/<pk> staged with the signer key.
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path
from multiprocessing import Pool
from Crypto.Hash import keccak as _keccak

CONTRACT = "0x6147a5244e890Ef8d41F82CA80455cE1bc658b5c"
ADDR = "0xBff994004E9558A8e7e4CD0D817884dC7ff8e65d"
PK_FILE = "/dev/shm/minecat-pk"
RPC = "https://robinhood-mainnet.g.alchemy.com/v2/<KEY>"
LOG = Path("/root/projects/spring-mint-bot/minecat-auto.log")


def log(m):
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {m}"
    print(line, flush=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def cast_call(sig, *args):
    cmd = ["cast", "call", CONTRACT, sig, "--rpc-url", RPC]
    cmd.extend(args)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError("call " + sig + ": " + (r.stderr or r.stdout)[-120:])
    return r.stdout.strip()


def current_round():
    return int(cast_call("currentRound()"), 16)


def round_seed(r):
    return bytes.fromhex(cast_call("roundSeed(uint256)", str(r))[2:])


def targets():
    return int(cast_call("ticketTarget()"), 16), int(cast_call("luckyTarget()"), 16)


def wallet_state():
    minted = int(cast_call("mintedBy(address)", ADDR), 16)
    tfr = int(cast_call("ticketFromRound(address)", ADDR), 16)
    voucher = int(cast_call("voucher(address)", ADDR), 16)
    return minted, tfr, voucher


def claimable(tfr, current):
    return tfr != 0 and current >= tfr


def grind(args):
    seed, addr_bytes, ticket, lucky, start, end, wid = args
    msg = bytearray(60)
    msg[0:32] = seed
    msg[32:52] = addr_bytes
    for nonce in range(start, end):
        msg[52:60] = nonce.to_bytes(8, "big")
        h = int.from_bytes(_keccak.new(digest_bits=256, data=bytes(msg)).digest(), "big")
        if h < ticket:
            return (nonce, h, h < lucky)
    return None


def send_tx(sel, args, value_wei=None):
    pk = Path(PK_FILE).read_text().strip()
    cmd = ["cast", "send", "--rpc-url", RPC, "--private-key", pk, CONTRACT, sel]
    cmd += [str(a) for a in args]
    if value_wei is not None:
        cmd += ["--value", str(value_wei)]
    cmd += ["--confirmations", "1", "--timeout", "120"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=150)
    return r.stdout + r.stderr


def try_claim():
    cur = current_round()
    minted, tfr, voucher = wallet_state()
    if not voucher and not claimable(tfr, cur):
        return False
    price = int(cast_call("mintPriceWei()"), 16)
    out = send_tx("claim()", [], value_wei=price)
    if "transactionHash" in out or "blockNumber" in out:
        log("CLAIM OK (paid " + str(price) + " wei)")
        return True
    log("claim result: " + out[-240:].replace("\n", " "))
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-mints", type=int, default=3)
    args = ap.parse_args()

    log(f"MINECAT auto miner+claimer for {ADDR} (target +{args.max_mints})")
    addr_bytes = bytes.fromhex(ADDR[2:])
    cores = max(2, (os.cpu_count() or 4) - 1)
    log(f"cores={cores}")

    while True:
        try:
            minted, tfr, voucher = wallet_state()
            cur = current_round()
            log(f"state minted={minted} ticketRound={tfr} voucher={voucher} round={cur}")
            if minted >= 5:
                log("wallet cap 5 reached — stop")
                return 0
            if minted >= args.max_mints:
                log(f"max-mints {args.max_mints} reached — stop")
                return 0

            if voucher or claimable(tfr, cur):
                log("claimable state detected — claiming")
                try_claim()
                time.sleep(3)
                continue

            r = current_round()
            seed = round_seed(r)
            if seed == b"\x00" * 32:
                log(f"round {r} not opened yet — openRound()")
                out = send_tx("openRound()", [])
                if "transactionHash" not in out and "blockNumber" not in out:
                    log("openRound result: " + out[-180:].replace("\n", " "))
                time.sleep(3)
                continue
            ticket, lucky = targets()
            log(f"round {r} seed={seed.hex()[:16]}… grinding")

            round_start = current_round()
            batch = 4_000_000
            pool = Pool(cores)
            tasks = [(seed, addr_bytes, ticket, lucky, i * batch, (i + 1) * batch, i) for i in range(cores)]
            sol = None
            try:
                for res in pool.imap_unordered(grind, tasks):
                    if res:
                        sol = res
                        pool.terminate()
                        break
                    if current_round() != round_start:
                        break
            finally:
                pool.close(); pool.join()

            if not sol:
                log("no solution this pass — continue")
                continue

            nonce, h, lucky_hit = sol
            if current_round() != round_start:
                log(f"round changed before submit (nonce {nonce}) — discard")
                continue
            log(f"SOLUTION nonce={nonce} lucky={lucky_hit} hash={h:064x}")
            out = send_tx("submitWork(uint64)", [nonce])
            if "transactionHash" in out or "blockNumber" in out:
                log("submitWork OK" + (" — LUCKY voucher" if lucky_hit else " — BUST ticket"))
            else:
                log("submitWork result: " + out[-240:].replace("\n", " "))
            time.sleep(2)
        except Exception as e:
            log(f"loop error: {str(e)[:160]}")
            time.sleep(3)


if __name__ == "__main__":
    sys.exit(main())
