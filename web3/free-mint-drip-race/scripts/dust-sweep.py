#!/usr/bin/env python3
"""Sweep dust balances Set START..END -> Set 1 at minimum gas (Robinhood FCFS).

Robinhood uses FCFS sequencing, so no priority tip is needed. Gas price =
pending baseFeePerGas * 1.10, retried on base-fee bumps. Sends balance - fee
exactly, leaving only unspendable dust.

Invoke: python3 dust-sweep.py <start-set> <end-set>
Requires /dev/shm/drip-pk-<n> files.
"""
import json, os, subprocess, sys, time, urllib.request
from pathlib import Path

for line in Path('/root/.hermes/.env').read_text(errors='ignore').splitlines():
    if line.startswith('ALCHEMY_API_KEY='):
        os.environ['ALCHEMY_API_KEY'] = line.split('=', 1)[1]
RPC = 'https://robinhood-mainnet.g.alchemy.com/v2/' + os.environ['ALCHEMY_API_KEY']
TARGET = '0xBff994004E9558A8e7e4CD0D817884dC7ff8e65d'
GAS_ETH = 21000
START = int(sys.argv[1]) if len(sys.argv) > 1 else 2
END = int(sys.argv[2]) if len(sys.argv) > 2 else 10

def rpc(method, params):
    req = urllib.request.Request(RPC, data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(), headers={'content-type':'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=20))['result']

def nonce(a): return int(rpc('eth_getTransactionCount',[a,'pending']),16)
def bal(a): return int(rpc('eth_getBalance',[a,'latest']),16)/1e18
def gas_price():
    gp = int(rpc('eth_gasPrice',[]),16)
    try:
        p = rpc('eth_getBlockByNumber',['pending',False])
        base = int(p.get('baseFeePerGas','0x0'),16)
        gp = max(gp, int(base*1.10))
    except Exception: pass
    return gp

def wait_receipt(tx, maxwait=90):
    for _ in range(maxwait):
        try:
            rec = rpc('eth_getTransactionReceipt',[tx])
            if rec: return int(rec['status'],16)
        except Exception: pass
        time.sleep(1)
    return None

addrs = {}
for i in range(START, END+1):
    f = Path(f'/dev/shm/drip-pk-{i}')
    if not f.exists(): print(f'Set{i} pk missing'); sys.exit(1)
    r = subprocess.run(['cast','wallet','address','--private-key',f.read_text().strip()],capture_output=True,text=True,check=True)
    addrs[i] = r.stdout.strip()

swept = 0.0
for i in range(START, END+1):
    addr = addrs[i]
    b = bal(addr)
    gp = gas_price()
    fee = GAS_ETH * gp / 1e18
    if b <= fee + 1e-15:
        print(f'Set{i} bal {b:.10f} <= fee {fee:.10f}, skip', flush=True)
        continue
    amt = b - fee
    pk = Path(f'/dev/shm/drip-pk-{i}').read_text().strip()
    for attempt in range(3):
        r = subprocess.run(['cast','send','--rpc-url',RPC,'--private-key',pk,
                            '--nonce',str(nonce(addr)),'--gas-price',str(gp),
                            '--json',TARGET,'--value',format(int(amt*1e18),'#x')],
                           capture_output=True, text=True, timeout=120)
        try:
            d = json.loads(r.stdout.strip()); tx = d.get('transactionHash') or d.get('hash')
        except Exception: tx = None
        if tx:
            st = wait_receipt(tx)
            if st == 1:
                swept += amt
                print(f'Set{i}->Set1 {amt:.10f} tx={tx[:20]} status=1', flush=True)
            else:
                print(f'Set{i} tx={tx[:20]} status={st}', flush=True)
            break
        else:
            err = r.stderr
            if 'max fee per gas less than block base fee' in err:
                try:
                    p = rpc('eth_getBlockByNumber',['pending',False])
                    gp = int(int(p.get('baseFeePerGas','0x0'),16)*1.10)
                except Exception: pass
                print(f'Set{i} base fee bumped to {gp}, retry {attempt+1}', flush=True)
                time.sleep(1)
                continue
            print(f'Set{i} FAILED {err[-160:]}', flush=True)
            break
    else:
        print(f'Set{i} gave up after 3 attempts', flush=True)

print(f'SWEPT {swept:.8f} ETH total, Set1 bal {bal(TARGET):.8f}', flush=True)
