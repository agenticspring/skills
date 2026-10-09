#!/usr/bin/env python3
"""Sweep remaining dust from Set2..END back to Set 1, down to the last wei.

Uses explicit --gas-price (0.021 gwei) so even 0.000007 ETH balances can tx.
Skips wallets whose balance can't cover fee + value.
"""
import json, os, re, subprocess, sys, time, urllib.request, urllib.error, tempfile
from pathlib import Path

def rpc_url():
    for line in Path('/root/.hermes/.env').read_text(errors='ignore').splitlines():
        if line.startswith('ALCHEMY_API_KEY='):
            return 'https://robinhood-mainnet.g.alchemy.com/v2/' + line.split('=',1)[1].strip()
    return 'https://rpc.mainnet.chain.robinhood.com'

RPC = os.environ.get('BABIES_RPC', rpc_url())
TARGET = '0xBff994004E9558A8e7e4CD0D817884dC7ff8e65d'
END = int(sys.argv[1]) if len(sys.argv) > 1 else 100
START = int(sys.argv[2]) if len(sys.argv) > 2 else 2
GAS_P = 0.021e9          # explicit low gas price
GAS_TX = 21000
FEE = GAS_TX * GAS_P / 1e18   # ~0.00000044
KEEP = FEE * 1.15

def log(m): print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)

def rpc(method, params):
    req = urllib.request.Request(RPC, data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(), headers={'content-type':'application/json','user-agent':'Mozilla/5.0'})
    for attempt in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=20))['result']
        except urllib.error.HTTPError as e:
            if e.code == 403 and attempt < 2: time.sleep(1); continue
            raise
    raise RuntimeError('rpc failed')

def n(h):
    try: return int(h,16)
    except: return h
def nonce(a): return n(rpc('eth_getTransactionCount',[a,'pending']))
def bal(a): return int(rpc('eth_getBalance',[a,'latest']),16)/1e18

def wait_receipt(tx, maxwait=60):
    for _ in range(maxwait):
        try:
            rec = rpc('eth_getTransactionReceipt',[tx])
            if rec: return int(rec['status'],16)
        except Exception: pass
        time.sleep(1)
    return None

def sweep(pk, a):
    b = bal(a)
    if b <= KEEP + 1e-18:
        return None, f'bal {b:.10f} <= fee {KEEP:.10f}'
    send = b - KEEP
    nonce_v = nonce(a)
    r = subprocess.run(['cast','send','--rpc-url',RPC,'--private-key',pk,
                        '--nonce',str(nonce_v),'--json',TARGET,
                        '--value',format(int(send*1e18),'#x'),
                        '--gas-price',format(int(GAS_P),'#x')],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return None, (r.stderr or r.stdout)[-150:]
    try:
        d = json.loads(r.stdout.strip()); tx = d.get('transactionHash') or d.get('hash')
    except Exception:
        return None, 'parse fail'
    st = wait_receipt(tx)
    return tx, f'status={st} sent={send:.10f}'

# load phrases
wfile = Path('/root/.hermes/.credintial/.springwallet')
phrases = []
for line in wfile.read_text().splitlines():
    w = line.strip().split()
    if not w or w[0].startswith('#') or w[0].lower() in ('set',): continue
    if len(w) in {12,15,18,21,24}:
        phrases.append(' '.join(w))
        if len(phrases) >= END: break

def derive_pk(idx):
    t = tempfile.NamedTemporaryFile('w', dir='/dev/shm', delete=False)
    t.write(phrases[idx-1]+'\n'); t.close(); os.chmod(t.name,0o600)
    r = subprocess.run(['cast','wallet','private-key','--mnemonic',t.name], capture_output=True, text=True)
    os.unlink(t.name)
    pk = r.stdout.strip()
    if not re.fullmatch(r'0x[0-9a-fA-F]{64}', pk): raise RuntimeError(f'bad pk {idx}')
    return pk

def addr_of(pk):
    return subprocess.run(['cast','wallet','address','--private-key',pk], capture_output=True, text=True, check=True).stdout.strip()

log(f'dust sweep Set{START}..{END} -> {TARGET} (fee~{KEEP:.8f})')
moved = 0.0
ok = 0
for i in range(START, END+1):
    try:
        pk = derive_pk(i)
        a = addr_of(pk)
    except Exception as e:
        log(f'Set{i} derive fail {str(e)[:60]}'); continue
    b = bal(a)
    if b < 1e-15:
        continue
    tx, info = sweep(pk, a)
    if tx:
        moved += b - KEEP
        ok += 1
        log(f'Set{i} swept {b:.10f} {tx[:16]} {info}')
    else:
        log(f'Set{i} skip ({b:.10f}) {info}')
log(f'DONE swept_wallets={ok} total_eth={moved:.8f}')
