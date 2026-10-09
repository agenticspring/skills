#!/usr/bin/env python3
"""Consolidate drip-minted NFTs from Set START..END to Set 1 (Robinhood 4663).

Funds gas into each owner wallet, transfers every token via
safeTransferFrom(owner -> Set1), then sweeps the remainder back.

CRITICAL: safeTransferFrom calldata is from + to + tokenId. `from` is the
OWNER wallet (Set N), `to` is Set 1. Reversed args revert
ERC721IncorrectOwner (0x177e802f).

Invoke: python3 consolidate-nfts.py <start-set> <end-set>
Requires /dev/shm/drip-pk-<n> files from the cascade run.
"""
import json, os, subprocess, sys, time, urllib.request
from pathlib import Path

for line in Path('/root/.hermes/.env').read_text(errors='ignore').splitlines():
    if line.startswith('ALCHEMY_API_KEY='):
        os.environ['ALCHEMY_API_KEY'] = line.split('=', 1)[1]
RPC = 'https://robinhood-mainnet.g.alchemy.com/v2/' + os.environ['ALCHEMY_API_KEY']
CONTRACT = '0xa185814414aa3D39c9A0B73A373E00C8C04Cb384'
TARGET = '0xBff994004E9558A8e7e4CD0D817884dC7ff8e65d'
GAS_BUF = 0.000006
FUND = 0.00005
STF = '0x42842e0e'   # safeTransferFrom(address,address,uint256)
BAL_SEL = '0x70a08231'   # balanceOf(address)
TOKEN_SEL = '0x2f745c59'  # tokenOfOwnerByIndex(address,uint256)
START = int(sys.argv[1]) if len(sys.argv) > 1 else 2
END = int(sys.argv[2]) if len(sys.argv) > 2 else 10

def rpc(method, params):
    req = urllib.request.Request(RPC, data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(), headers={'content-type':'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=20))['result']

def nonce(a): return int(rpc('eth_getTransactionCount',[a,'pending']),16)
def bal(a): return int(rpc('eth_getBalance',[a,'latest']),16)/1e18
def call(data,to=CONTRACT):
    try: return int(rpc('eth_call',[{'to':to,'data':data},'latest']),16)
    except Exception: return None

def wait_receipt(tx, maxwait=90):
    for _ in range(maxwait):
        try:
            rec = rpc('eth_getTransactionReceipt',[tx])
            if rec: return int(rec['status'],16), int(rec['blockNumber'],16)
        except Exception: pass
        time.sleep(1)
    return None, None

def send_eth(pk, addr, to, amount):
    r = subprocess.run(['cast','send','--rpc-url',RPC,'--private-key',pk,
                        '--nonce',str(nonce(addr)),'--json',to,'--value',format(int(amount*1e18),'#x')],
                       capture_output=True, text=True, timeout=120)
    try:
        d = json.loads(r.stdout.strip()); tx = d.get('transactionHash') or d.get('hash')
    except Exception: tx = None
    if not tx: return None, r.stderr[-200:]
    st, blk = wait_receipt(tx)
    return tx, f'status={st} block={blk}'

def send_tx(pk, addr, to, data):
    r = subprocess.run(['cast','send','--rpc-url',RPC,'--private-key',pk,
                        '--nonce',str(nonce(addr)),'--json',to,data],
                       capture_output=True, text=True, timeout=120)
    try:
        d = json.loads(r.stdout.strip()); tx = d.get('transactionHash') or d.get('hash')
    except Exception: tx = None
    if not tx: return None, r.stderr[-200:]
    st, blk = wait_receipt(tx)
    return tx, f'status={st} block={blk}'

def tokens_of(addr):
    ids = []
    b = call(BAL_SEL + addr[2:].lower().rjust(64,'0'))
    if not b: return ids
    for i in range(b):
        tid = call(TOKEN_SEL + addr[2:].lower().rjust(64,'0') + format(i,'064x'))
        if tid is not None: ids.append(tid)
    return ids

addrs = {}
for i in range(START, END+1):
    f = Path(f'/dev/shm/drip-pk-{i}')
    if not f.exists(): print(f'Set{i} pk missing (run drip-race-mint first)'); sys.exit(1)
    r = subprocess.run(['cast','wallet','address','--private-key',f.read_text().strip()],capture_output=True,text=True,check=True)
    addrs[i] = r.stdout.strip()

pk1 = Path('/dev/shm/drip-pk-1').read_text().strip()
moved = 0
for i in range(START, END+1):
    addr = addrs[i]; pk = Path(f'/dev/shm/drip-pk-{i}').read_text().strip()
    ids = tokens_of(addr)
    print(f'Set{i} has {len(ids)} tokens: {ids[:5]}{"..." if len(ids)>5 else ""}', flush=True)
    if not ids: continue
    tx, info = send_eth(pk1, TARGET, addr, FUND)
    print(f'  fund {FUND} ETH -> Set{i} tx={tx[:16] if tx else None} {info}', flush=True)
    if not tx: print('  fund failed'); continue
    for tid in ids:
        # from = owner (addr), to = TARGET. Order matters!
        data = STF + addr[2:].lower().rjust(64,'0') + TARGET[2:].lower().rjust(64,'0') + format(tid,'064x')
        tx2, info2 = send_tx(pk, addr, CONTRACT, data)
        if tx2:
            moved += 1
            print(f'  token {tid} -> Set1 tx={tx2[:16]} {info2}', flush=True)
        else:
            print(f'  token {tid} FAILED {info2}', flush=True)
    b = bal(addr)
    if b > GAS_BUF + 0.000001:
        tx3, info3 = send_eth(pk, addr, TARGET, b - GAS_BUF)
        print(f'  sweep {b-GAS_BUF:.8f} -> Set1 tx={tx3[:16] if tx3 else None} {info3}', flush=True)

print('MOVED', moved, 'tokens to Set1', flush=True)
