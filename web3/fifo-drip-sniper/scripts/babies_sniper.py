#!/usr/bin/env python3
"""
RWA FLYWHEEL BABIES free-mint sniper — Robinhood Chain (4663).

Mechanic, verified on-chain 2026-08-21:
  mintFree() 0x8ab53447, value 0, FREE_PER_WALLET=1.
  Gate is a global drip: block.timestamp >= lastFreeMintAt + mintInterval (3s now).
  Winner is the first eligible tx in the FIRST block of the boundary second.
  Sequencer is FIFO by arrival (Arbitrum Nitro Orbit) — priority fee buys nothing:
  observed winners paid 0.001 gwei while a 1.0-gwei spam army reverted around them.

Timing (measured on this chain, not guessed):
  eth_sendRawTransaction admission is ~340ms and the tx lands ~4-5 blocks after the
  head at send time, so the send must happen BEFORE the boundary. Measured here:
  the first block of chain second B is produced at wall ~B+0.35s. Default centre
  fires at B-210ms and brackets around it; the tuner then walks the centre using
  where the shots actually landed (block ts vs boundary second).
"""
import http.client, json, os, re, sys, threading, time, urllib.parse, urllib.request
from collections import deque
from eth_account import Account

HOME = os.path.expanduser("~")
D = os.path.join(HOME, "babies")
WALLETS_FILE = os.environ.get("BABIES_WALLETS", os.path.join(D, "wallets.json"))
STOP_FILE = os.path.join(D, "STOP")

CA = "0xfCe5F08D3167863ad8D85735bbE8Ec973dc32bCC"
CHAIN_ID = 4663
DATA = "0x8ab53447"                      # mintFree()
SEL_LAST = "0xfca4b80e"                  # lastFreeMintAt()
SEL_IV   = "0x0e726e6b"                  # mintInterval()
SEL_OPEN = "0x24bbd049"                  # mintOpen()
SEL_REM  = "0x55234ec0"                  # remaining()
SEL_FREE = "0x389fcf06"                  # freeMinted(address)

GAS_LIMIT = 250_000
MAX_FEE = int(os.environ.get("BABIES_MAXFEE", 50_000_000))   # 0.05 gwei, base is ~0.020
PRIORITY_FEE = 0                                             # FIFO chain: tips buy nothing
MIN_BALANCE_WEI = int(os.environ.get("BABIES_MINBAL", 60_000_000_000_000))  # 0.00006 ETH

CENTRE = float(os.environ.get("BABIES_CENTRE", "-210"))      # ms, relative to boundary second
SPREAD = [float(x) for x in os.environ.get("BABIES_SPREAD", "-80,-40,0,40").split(",")]
ACTIVE = int(os.environ.get("BABIES_ACTIVE", "4"))           # wallets firing per window
TARGET = int(os.environ.get("BABIES_TARGET", "100"))         # stop after this many babies
TUNE = os.environ.get("BABIES_TUNE", "1") == "1"

# Public RPC works. A paid endpoint (dRPC/Alchemy/etc) is steadier under load —
# put it in BABIES_RPC. Reads are ~30ms either way; the write path is the sequencer's
# ~340ms admission and no RPC shortens that.
RPC = os.environ.get("BABIES_RPC", "https://rpc.mainnet.chain.robinhood.com")
U = urllib.parse.urlparse(RPC)
HOST, PATH = U.netloc, (U.path or "/")
H = {"content-type": "application/json", "connection": "keep-alive",
     "user-agent": "Mozilla/5.0"}
_pl = threading.Lock()

def log(m):
    with _pl:
        t = time.time()
        print("[%s.%03d] %s" % (time.strftime("%H:%M:%S", time.localtime(t)),
                                int(t * 1000) % 1000, m), flush=True)

def rpc_batch(batch, timeout=25):
    r = urllib.request.Request(RPC, data=json.dumps(batch).encode(), headers=H)
    with urllib.request.urlopen(r, timeout=timeout) as f:
        return json.load(f)

def call(sel, arg_addr=None):
    d = sel + (("0" * 24 + arg_addr[2:].lower()) if arg_addr else "")
    return {"jsonrpc": "2.0", "id": 0, "method": "eth_call", "params": [{"to": CA, "data": d}, "latest"]}

class Shooter:
    """One TLS connection, one shot, response always read (v6's silent-drop lesson)."""
    def __init__(self):
        self.c = None; self.ok = 0; self.rej = 0; self.last_err = ""
    def _conn(self):
        if self.c is None:
            self.c = http.client.HTTPSConnection(HOST, 443, timeout=15)
            self.c.request("POST", PATH, json.dumps(
                {"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}), H)
            self.c.getresponse().read()
        return self.c
    def send(self, body):
        try:
            c = self._conn()
            c.request("POST", PATH, body, H)
            d = json.loads(c.getresponse().read())
        except Exception as e:
            try: self.c.close()
            except Exception: pass
            self.c = None
            self.last_err = "%s: %s" % (type(e).__name__, e); self.rej += 1
            return None
        if "error" in d:
            self.rej += 1; self.last_err = str(d["error"].get("message"))[:90]
            return None
        self.ok += 1
        return d.get("result")

def main():
    if not os.path.exists(WALLETS_FILE):
        log("no wallet file at %s — run babies_gen.py N first" % WALLETS_FILE); return
    ws = json.load(open(WALLETS_FILE))
    pool = [{"addr": w["address"], "pk": w["private_key"], "nonce": 0, "bal": 0} for w in ws]
    log("=" * 78)
    log("BABIES sniper — %d wallets, %d firing/window, shots at %s ms" %
        (len(pool), ACTIVE, [CENTRE + s for s in SPREAD]))
    log("RPC host %s" % HOST)
    log("=" * 78)

    # initial sync: balances, nonces, who already has a baby
    def sync(items):
        b = []
        for i, w in enumerate(items):
            b.append({"jsonrpc": "2.0", "id": i * 3, "method": "eth_getBalance", "params": [w["addr"], "latest"]})
            b.append({"jsonrpc": "2.0", "id": i * 3 + 1, "method": "eth_getTransactionCount", "params": [w["addr"], "latest"]})
            c = call(SEL_FREE, w["addr"]); c["id"] = i * 3 + 2
            b.append(c)
        res = {}
        for k in range(0, len(b), 150):
            for x in rpc_batch(b[k:k + 150]): res[x["id"]] = x
        done = []
        for i, w in enumerate(items):
            w["bal"] = int(res[i * 3].get("result") or "0x0", 16)
            w["nonce"] = int(res[i * 3 + 1].get("result") or "0x0", 16)
            fm = res[i * 3 + 2].get("result")
            if fm and int(fm, 16) >= 1: done.append(w)
        return done

    done = sync(pool)
    for w in done: pool.remove(w)
    wins = len(done)
    ready = [w for w in pool if w["bal"] >= MIN_BALANCE_WEI]
    log("wallets: %d total | %d already minted | %d funded and ready" % (len(ws), wins, len(ready)))
    if not ready:
        log("nothing funded — fund the wallets first, aborting"); return

    centre = CENTRE
    fired = deque(maxlen=600)      # (hash, offset, boundary, wallet)
    checked = set()
    land = deque(maxlen=60)        # landed_block_ts - boundary, for the tuner
    shooters = [Shooter() for _ in range(ACTIVE * len(SPREAD))]
    for s in shooters:
        try: s._conn()
        except Exception: pass
    rr = 0; window = 0; last_sync = 0

    while True:
        if os.path.exists(STOP_FILE):
            log("STOP file present, halting"); break
        if wins >= TARGET:
            log("target %d reached" % TARGET); break

        st = {x["id"]: x for x in rpc_batch([
            dict(call(SEL_LAST), id=1), dict(call(SEL_IV), id=2),
            dict(call(SEL_OPEN), id=3), dict(call(SEL_REM), id=4)])}
        try:
            last_free = int(st[1]["result"], 16)
            interval = int(st[2]["result"], 16)
            is_open = int(st[3]["result"], 16) == 1
            remaining = int(st[4]["result"], 16)
        except Exception as e:
            log("state read failed: %s" % e); time.sleep(0.5); continue
        if not is_open or remaining == 0:
            log("mint closed or sold out (open=%s remaining=%d)" % (is_open, remaining)); break

        boundary = last_free + interval
        offs = [centre + s for s in SPREAD]
        now = time.time()
        # if the boundary already passed, the slot is open right now: fire immediately
        if boundary + min(offs) / 1000.0 - now < 0.05:
            due_base = now + 0.05
            offs = [0.0 for _ in SPREAD]
        else:
            due_base = boundary

        ready = [w for w in pool if w["bal"] >= MIN_BALANCE_WEI]
        if not ready:
            log("all funded wallets exhausted"); break
        batch_w = [ready[(rr + i) % len(ready)] for i in range(min(ACTIVE, len(ready)))]
        rr = (rr + len(batch_w)) % max(1, len(ready))

        jobs = []
        for wi, w in enumerate(batch_w):
            for k, off in enumerate(offs):
                sg = Account.sign_transaction(
                    {"to": CA, "value": 0, "gas": GAS_LIMIT, "maxFeePerGas": MAX_FEE,
                     "maxPriorityFeePerGas": PRIORITY_FEE, "nonce": w["nonce"] + k,
                     "chainId": CHAIN_ID, "data": DATA, "type": 2}, w["pk"])
                raw = sg.raw_transaction.hex(); raw = raw if raw.startswith("0x") else "0x" + raw
                h = sg.hash.hex(); h = h if h.startswith("0x") else "0x" + h
                body = json.dumps({"jsonrpc": "2.0", "id": 1,
                                   "method": "eth_sendRawTransaction", "params": [raw]})
                jobs.append((wi * len(offs) + k, off, body, h, w))

        def shoot(idx, off, body, h, w):
            due = due_base + off / 1000.0
            dt = due - time.time()
            if dt > 0.002: time.sleep(dt - 0.0015)
            while time.time() < due: pass
            if shooters[idx].send(body) is not None:
                fired.append((h, off, boundary, w["addr"]))

        ths = [threading.Thread(target=shoot, args=j) for j in jobs]
        for t in ths: t.start()
        for t in ths: t.join(timeout=6)
        for w in batch_w:
            w["nonce"] += len(offs)
            w["bal"] -= 30_000 * 25_000_000 * len(offs)   # rough revert cost, resynced below

        # receipts: did we land in the boundary block, early, or late?
        pend = [(h, o, b, a) for h, o, b, a in list(fired) if h not in checked][:80]
        if pend:
            try:
                res = rpc_batch([{"jsonrpc": "2.0", "id": i, "method": "eth_getTransactionReceipt",
                                  "params": [h]} for i, (h, _, _, _) in enumerate(pend)])
                blocks = {}
                for i, (h, o, b, a) in enumerate(pend):
                    r = res[i].get("result")
                    if not r: continue
                    checked.add(h)
                    blocks[h] = (r, o, b, a)
                if blocks:
                    bns = sorted({int(r["blockNumber"], 16) for r, _, _, _ in blocks.values()})
                    bres = {x["id"]: x for x in rpc_batch(
                        [{"jsonrpc": "2.0", "id": n, "method": "eth_getBlockByNumber",
                          "params": [hex(n), False]} for n in bns])}
                    for h, (r, o, b, a) in blocks.items():
                        bn = int(r["blockNumber"], 16)
                        bts = int(bres[bn]["result"]["timestamp"], 16)
                        land.append((bts - b, o))
                        if int(r["status"], 16) == 1:
                            wins += 1
                            log("*** WIN #%d *** %s  tx %s blk %d idx %s (fired %+.0fms, landed sec %+d)"
                                % (wins, a, h[:16], bn, int(r["transactionIndex"], 16), o, bts - b))
                            for w in list(pool):
                                if w["addr"] == a: pool.remove(w)
            except Exception:
                pass

        # tuner: walk the centre so shots land in the boundary second, not before or after
        if TUNE and len(land) >= 24:
            early = sum(1 for d, _ in land if d < 0)
            late = sum(1 for d, _ in land if d > 0)
            on = len(land) - early - late
            if early > late + 6 and on < len(land) * 0.5:
                centre += 25; land.clear(); log("tuner: too early -> centre %+.0fms" % centre)
            elif late > early + 6 and on < len(land) * 0.5:
                centre -= 25; land.clear(); log("tuner: too late -> centre %+.0fms" % centre)

        window += 1
        if window - last_sync >= 20:
            last_sync = window
            gone = sync(pool)
            for w in gone:
                pool.remove(w); wins += 1
                log("*** WIN (found on sync) *** %s — total %d" % (w["addr"], wins))

        if window % 10 == 0:
            acc = sum(s.ok for s in shooters); rej = sum(s.rej for s in shooters)
            errs = [s.last_err for s in shooters if s.last_err]
            on = sum(1 for d, _ in land if d == 0)
            log("w%-5d wins=%d pool=%d remaining=%d iv=%ds centre=%+.0fms sent=%d rej=%d onTarget=%d/%d%s"
                % (window, wins, len(pool), remaining, interval, centre, acc, rej, on, len(land),
                   ("  err=" + errs[-1]) if errs else ""))

    log("done — %d babies, %d wallets left in pool" % (wins, len(pool)))

if __name__ == "__main__":
    main()
