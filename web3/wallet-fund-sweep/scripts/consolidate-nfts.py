#!/usr/bin/env python3
"""Consolidate ALL BABIES NFTs + ETH dust to Set 1.

For each wallet Set2..100:
  1. If it owns NFTs (tokenOfOwnerByIndex), safeTransferFrom each to Set 1.
  2. Sweep ALL remaining ETH balance (minus real transfer fee) to Set 1.
Runs until nothing left to move (balance <= fee).
"""
import json, os, re, subprocess, sys, time, urllib.request, urllib.error, tempfile
from pathlib import Path

def rpc_url():
    for line in Path('/root/.hermes/.env').read_text(errors='ignore').splitlines():
        if line.startswith('ALCHEMY_API_KEY='):
            return 'https://robinhood-mainnet.g.alchemy.com/v2/' + line.split('=',1)[1].strip()
    return 'https://rpc.mainnet.chain.robinhood.com'

RPC = os.environ.get('BABIES_RPC', rpc_url())
CA = '0xfCe5F08D3167863ad8D85735bbE8Ec973dc32bCC'
TARGET = '0xBff994004E9558A8e7e4CD0D817884dC7ff8e65d'   # Set 1
END = int(sys.argv[1]) if len(sys.argv) > 1 else 100
GAS_TX = 21000
SEL_TOBI = '0x2f745c59'    # tokenOfOwnerByIndex(address,uint256)
SEL_STF  = '0x42842e0e'    # safeTransferFrom(address,address,uint256)

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
def call(data,to=CA):
    try: return rpc('eth_call',[{'to':to,'data':data},'latest'])
    except Exception: return None

def gas_price():
    try:
        b = rpc('eth_getBlockByNumber',['pending',False])
        return int(b['baseFeePerGas'],16) * 11 // 10
    except Exception:
        return 20_000_000

def wait_receipt(tx, maxwait=120):
    for _ in range(maxwait):
        try:
            rec = rpc('eth_getTransactionReceipt',[tx])
            if rec: return int(rec['status'],16)
        except Exception: pass
        time.sleep(1)
    return None

def broadcast(pk, addr, to, data, value=0):
    r = subprocess.run(['cast','send','--rpc-url',RPC,'--private-key',pk,
                        '--nonce',str(nonce(addr)),'--json',to,
                        '--data',data] + (['--value',format(int(value*1e18),'#x')] if value else []),
                       capture_output=True, text=True, timeout=120)
    try:
        d = json.loads(r.stdout.strip()); tx = d.get('transactionHash') or d.get('hash')
    except Exception: tx = None
    if not tx: return None, (r.stderr or r.stdout)[-200:]
    st = wait_receipt(tx)
    return tx, f'status={st}'

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

def nft_ids(a):
    """Return token ids owned by a via tokenOfOwnerByIndex."""
    ids = []
    i = 0
    while i < 20:  # hard safety cap
        data = SEL_TOBI + a[2:].lower().rjust(64,'0') + format(i,'064x')
        r = call(data)
        if r is None or r == '0x':
            break
        ids.append(n(r)); i += 1
    return ids

log(f'consolidate: Set2..{END} -> {TARGET}')
nfts_moved = 0
eth_moved = 0.0
for i in range(2, END+1):
    pk = derive_pk(i)
    a = addr_of(pk)
    ids = nft_ids(a)
    b = bal(a)
    if not ids and b < 0.0000012:
        continue  # nothing to move
    log(f'Set{i} {a[:12]} nft={ids} eth={b:.8f}')

    # 1) transfer NFTs
    for tid in ids:
        data = SEL_STF + a[2:].lower().rjust(64,'0') + TARGET[2:].lower().rjust(64,'0') + format(tid,'064x')
        tx, info = broadcast(pk, a, CA, data)
        if tx:
            nfts_moved += 1
            log(f'  nft #{tid} -> Set1 {tx[:16]} {info}')
        else:
            log(f'  nft #{tid} FAIL {info}')

    # 2) sweep ETH: all minus real fee
    b = bal(a)
    gp = gas_price()
    keep = max(GAS_TX * gp / 1e18 * 2.0, 0.0000012)
    if b > keep + 1e-15:
        amt = b - keep
        tx, info = broadcast(pk, a, TARGET, '0x', int(amt*1e18))
        if tx:
            eth_moved += amt
            log(f'  eth {amt:.8f} -> Set1 {tx[:16]} {info}')
        else:
            log(f'  eth sweep FAIL {info}')
    else:
        log(f'  eth {b:.8f} <= fee {keep:.8f} — cannot tx, keep')

log(f'DONE nfts_moved={nfts_moved} eth_moved={eth_moved:.8f}')
