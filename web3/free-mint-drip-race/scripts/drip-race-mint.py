#!/usr/bin/env python3
"""Drip free-mint cascade across Hermes wallet sets (Robinhood 4663).

Funds Set START from Set START-1 with FUND ETH, races the global drip to the
per-wallet free cap on each wallet, then forwards remaining balance to the
next wallet. Proven on FABLINGS (10 free/wallet, 3s global interval, 9 wallets).

Config: edit CONTRACT / MINTFREE / SEL_* / FUND / GAS_RESERVE per target.
Invoke: python3 drip-race-mint.py <start-set> <end-set>
"""
import json, os, subprocess, sys, time, urllib.request
from pathlib import Path

for line in Path('/root/.hermes/.env').read_text(errors='ignore').splitlines():
    if line.startswith('ALCHEMY_API_KEY='):
        os.environ['ALCHEMY_API_KEY'] = line.split('=', 1)[1]
RPC = 'https://robinhood-mainnet.g.alchemy.com/v2/' + os.environ['ALCHEMY_API_KEY']
CONTRACT = '0xa185814414aa3D39c9A0B73A373E00C8C04Cb384'   # FABLINGS items
MINTFREE = '0x8ab53447'          # mintFree() selector (compute via eth_utils!)
SEL_LAST = '0xfca4b80e'          # lastFreeMintAt()
SEL_IV = '0x0e726e6b'            # mintInterval()
CAP = 10                          # FREE_PER_WALLET
START = int(sys.argv[1]) if len(sys.argv) > 1 else 2
END = int(sys.argv[2]) if len(sys.argv) > 2 else 10
FUND = 0.0010
GAS_RESERVE = 0.00005

def rpc(method, params):
    req = urllib.request.Request(RPC, data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(), headers={'content-type':'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=20))['result']

def nonce(addr): return int(rpc('eth_getTransactionCount', [addr, 'pending']), 16)
def balance(addr): return int(rpc('eth_getBalance', [addr, 'latest']), 16) / 1e18
def call(data, to=CONTRACT):
    try: return int(rpc('eth_call', [{'to':to,'data':data}, 'latest']), 16)
    except Exception: return None
def now_chain(): return int(rpc('eth_getBlockByNumber',['latest',False])['timestamp'], 16)

def wait_receipt(tx, maxwait=90):
    for _ in range(maxwait):
        try:
            rec = rpc('eth_getTransactionReceipt', [tx])
            if rec: return int(rec['status'], 16), int(rec['blockNumber'], 16)
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
    if not tx: return None, r.stderr[-300:]
    st, blk = wait_receipt(tx)
    return tx, f'status={st} block={blk}' if st is not None else 'no-receipt'

def mint_max(pk, addr, label):
    minted = 0; attempts = 0
    while minted < CAP:
        attempts += 1
        for _ in range(2000):
            last = call(SEL_LAST); iv = call(SEL_IV)
            if last is not None and iv is not None and (last + iv) <= now_chain():
                break
            time.sleep(0.1)
        n = nonce(addr)
        r = subprocess.run(['cast','send','--rpc-url',RPC,'--private-key',pk,'--nonce',str(n),
                            '--json',CONTRACT,'mintFree()'], capture_output=True, text=True, timeout=120)
        try:
            d = json.loads(r.stdout.strip()); tx = d.get('transactionHash') or d.get('hash')
        except Exception: tx = None
        if tx:
            st, blk = wait_receipt(tx)
            if st == 1:
                minted += 1
                print(f'  {label} [{minted}/{CAP}] OK tx={tx[:20]} block={blk}', flush=True)
            else:
                print(f'  {label} nonce={n} REVERTED tx={tx[:20]}', flush=True)
        else:
            err = r.stderr
            if '53353903' in err or 'FreeWalletCapReached' in err:
                print(f'  {label} wallet cap reached', flush=True); break
            if '951b974f' in err or 'MintNotOpen' in err:
                print(f'  {label} mint closed', flush=True); break
            # DripNotReady -> lost race, retry
        if attempts > 500:
            print(f'  {label} attempt cap 500, minted={minted}', flush=True); break
    return minted

wfile = Path('/root/.hermes/.credintial/.springwallet')
phrases = []
for line in wfile.read_text().splitlines():
    w = line.strip().split()
    if not w or w[0].startswith('#') or w[0].lower() in ('set',): continue
    if len(w) not in {12,15,18,21,24}: continue
    phrases.append(' '.join(w))
    if len(phrases) >= END: break

def derive_pk(idx):
    import tempfile, re
    t = tempfile.NamedTemporaryFile('w', dir='/dev/shm', delete=False)
    t.write(phrases[idx-1]+'\n'); t.close(); os.chmod(t.name,0o600)
    r = subprocess.run(['cast','wallet','private-key','--mnemonic',t.name], capture_output=True, text=True)
    os.unlink(t.name)
    pk = r.stdout.strip()
    if not re.fullmatch(r'0x[0-9a-fA-F]{64}', pk):
        raise RuntimeError(f'bad pk for set {idx}')
    f = Path('/dev/shm') / f'drip-pk-{idx}'
    f.write_text(pk); os.chmod(f,0o600)
    return pk

def addr_of(pk):
    r = subprocess.run(['cast','wallet','address','--private-key',pk], capture_output=True, text=True, check=True)
    return r.stdout.strip()

pks = {i: derive_pk(i) for i in range(1, END+1)}
addrs = {i: addr_of(pks[i]) for i in range(1, END+1)}
print('wallets', {i: (a[:10]+'...') for i,a in addrs.items()}, flush=True)

for i in range(START, END+1):
    if i == START:
        tx, info = send_eth(pks[START-1], addrs[START-1], addrs[i], FUND)
        print(f'fund Set{START-1}->Set{i} {FUND} tx={tx} {info}', flush=True)
        if not tx: print('FUND FAILED', info, flush=True); sys.exit(1)
    else:
        bal = balance(addrs[i-1])
        if bal <= GAS_RESERVE:
            print(f'Set{i-1} balance {bal} too low, stop', flush=True); break
        amt = bal - GAS_RESERVE
        tx, info = send_eth(pks[i-1], addrs[i-1], addrs[i], amt)
        print(f'cascade Set{i-1}->Set{i} {amt:.8f} tx={tx} {info}', flush=True)
        if not tx: print('CASCADE FAILED', info, flush=True); sys.exit(1)
    print(f'minting Set{i} {addrs[i]}', flush=True)
    n = mint_max(pks[i], addrs[i], f'Set{i}')
    print(f'Set{i} minted {n}, balance {balance(addrs[i]):.8f}', flush=True)

print('ALL DONE', flush=True)
for i in range(START, END+1):
    print(f'Set{i} {addrs[i]} balance={balance(addrs[i]):.8f}', flush=True)
