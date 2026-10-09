#!/usr/bin/env python3
"""Probe an NFT contract and classify its mint mechanic (free/paid/closed).

Usage:
  python3 check-mint-free.py <contract-address> [wallet-address]

Reads on-chain state via Alchemy RPC (Robinhood default). Probes common
function names with computed selectors, decodes values, and prints a
classification summary. Read-only — never broadcasts.
"""
import json, os, sys, urllib.request
from pathlib import Path

def rpc_url():
    for line in Path('/root/.hermes/.env').read_text(errors='ignore').splitlines():
        if line.startswith('ALCHEMY_API_KEY='):
            return 'https://robinhood-mainnet.g.alchemy.com/v2/' + line.split('=', 1)[1].strip()
    raise SystemExit('ALCHEMY_API_KEY missing in /root/.hermes/.env')

RPC = rpc_url()
ZERO = '0x' + '00' * 20

def rpc(method, params):
    req = urllib.request.Request(RPC, data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(), headers={'content-type':'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=20))['result']

def call(to, data):
    try:
        return rpc('eth_call', [{'to': to, 'data': data}, 'latest'])
    except Exception:
        return 'REVERT'

def n(h):
    try: return int(h, 16)
    except: return None

try:
    from eth_utils.crypto import keccak
except ImportError:
    from eth_utils import keccak
def sel(name, ins):
    return '0x' + keccak(text=name + '(' + ','.join(ins) + ')')[:4].hex()

def main():
    if len(sys.argv) < 2:
        print('usage: check-mint-free.py <contract-address> [wallet]')
        return 2
    c = sys.argv[1].lower()
    w = (sys.argv[2] if len(sys.argv) > 2 else ZERO).lower()
    wpad = w[2:].rjust(64, '0')

    code_len = (len(rpc('eth_getCode', [c, 'latest'])) - 2) // 2
    print(f'contract {c} code_len={code_len}')

    probes = {}
    for fn in ['PRICE', 'mintPrice', 'price', 'MAX_SUPPLY', 'maxSupply', 'INITIAL_MAX_SUPPLY',
               'mintActive', 'mintOpen', 'phase', 'totalSupply', 'reserved', 'FREE_PER_WALLET',
               'mintInterval', 'lastFreeMintAt', 'mintableBy', 'mintedBy', 'freeMintsRemaining',
               'mintCost', 'walletLimit', 'MAX_PER_WALLET', 'remaining', 'freemintOpen', 'tailMinted']:
        ins = []
        if fn in ('mintedBy', 'freeMintsRemaining', 'mintableBy'):
            ins = ['address']
        elif fn == 'mintCost':
            ins = ['address', 'uint256']
        probes[fn] = sel(fn, ins) + (wpad if ins else '')

    reads = {}
    for fn, s in probes.items():
        r = call(c, s)
        if r != 'REVERT' and r and r != '0x':
            reads[fn] = r

    eth0 = reads.get('PRICE') or reads.get('mintPrice') or reads.get('price')
    ts = reads.get('totalSupply')
    mx = reads.get('MAX_SUPPLY') or reads.get('maxSupply') or reads.get('INITIAL_MAX_SUPPLY')
    active = reads.get('mintActive') or reads.get('mintOpen')

    print('\n-- state --')
    for fn, r in sorted(reads.items()):
        val = n(r)
        if fn in ('mintCost',):
            print(f'  {fn}: {val/1e18 if val is not None else r} ETH' if val else f'  {fn}: {r[:66]}')
        else:
            print(f'  {fn}: {val if val is not None else r[:66]}')

    print('\n-- classification --')
    if active is not None and n(active) == 0:
        print('MINT CLOSED / NOT OPEN (window off or phase=0)')
    if ts is not None and mx is not None and n(ts) >= n(mx):
        print(f'SOLD OUT ({n(ts)}/{n(mx)})')
    if eth0 is not None:
        price = n(eth0)
        if price == 0:
            print(f'PRICE 0 -> free mint by price (but check supply/window)')
        else:
            print(f'PRICE {price/1e18} ETH -> PAID MINT')
    if 'freeMintsRemaining' in reads:
        print(f'freeMintsRemaining(wallet) = {n(reads["freeMintsRemaining"])} (0 = no free slot)')
    if 'mintCost' in reads:
        mc = n(reads['mintCost'])
        print(f'mintCost(wallet,1) = {mc/1e18} ETH' if mc is not None else 'mintCost revert')
    if 'mintFree' in '':
        pass
    return 0

if __name__ == '__main__':
    sys.exit(main())
