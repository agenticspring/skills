#!/usr/bin/env python3
"""
OpenSea drop auto-mint scheduler — backend-signed, ALL stages (public + WL/GTD).

Flow: cheap REST probe GET /drops/{slug} → when requested stage window opens →
parallel SIWE login per wallet → POST /drops/{slug}/mint (OpenSea signs voucher)
→ broadcast returned calldata with cast send → retry once.

Proven on Onchain Sketches (2026-08-30): works for signed_presale WL stages —
OpenSea's backend signs, you never need the creator's key.
Oversubscribed drops sell out in seconds — poll at 1-2 s or arm early.

Usage:
  python3 ocs_auto_mint.py --sets 1-10 --quantity 1 --stage wl --watch
  python3 ocs_auto_mint.py --sets 1-5 --quantity 1 --dry        # build only
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, '/tmp/opensea-eligibility-checker/scripts')
from opensea_eligibility import siwe_login
from eth_account import Account
Account.enable_unaudited_hdwallet_features()

SLUG = 'onchainsketches'  # override with --slug
MNE_PATH = '/root/.hermes/.credintial/.springwallet'
WALLETS_PATH = '/tmp/ocs_wallets.json'


def get_api_key():
    for line in open('/root/NFT-OPENSEA/opensea.env'):
        if line.startswith('OPENSEA_API_KEY='):
            return line.strip().split('=', 1)[1]
    return None


def get_pk(sets, n):
    return Account.from_mnemonic(sets[n]).key.hex()


def load_sets():
    sets = {}
    current = None
    with open(MNE_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = re.match(r'Set (\d+)', line)
            if m:
                current = int(m.group(1))
                sets[current] = None
            elif current and sets[current] is None:
                sets[current] = line
    return sets


def probe_drop_active(stage, stage_epochs, slug):
    """Cheap REST probe — no SIWE. Epoch check first, API label fallback."""
    now = int(time.time())
    lo, hi = stage_epochs.get(stage, (0, 0))
    if lo <= now <= hi:
        return True, f'{stage} window open'
    api_key = get_api_key()
    headers = {'X-API-KEY': api_key} if api_key else {}
    try:
        import httpx
        with httpx.Client(timeout=15, headers=headers) as c:
            r = c.get(f'https://api.opensea.io/api/v2/drops/{slug}')
            if r.status_code != 200:
                return False, f'HTTP_{r.status_code}'
            d = r.json()
            active = d.get('active_stage')
            if active and isinstance(active, dict):
                label = (active.get('label') or '').lower()
                stype = (active.get('stage_type') or '').lower()
                if stage == 'wl' and ('wl' in label or 'whitelist' in label):
                    return True, f'API active: {label}'
                if stage == 'public' and ('public' in label or 'sale' in stype):
                    return True, f'API active: {label}'
            return False, f'API stage not {stage}'
    except Exception as e:
        return False, f'error:{str(e)[:80]}'


def build_mint_tx(client, wallet_addr, quantity, slug):
    """POST /api/v2/drops/{slug}/mint → {to,data,value,chain} or error dict."""
    api_key = get_api_key()
    headers = {'X-API-KEY': api_key} if api_key else {}
    url = f'https://api.opensea.io/api/v2/drops/{slug}/mint'
    r = client.post(url, json={'minter': wallet_addr, 'quantity': quantity}, headers=headers)
    if r.status_code == 401:
        return {'error': 'AUTH_FAILED — check API key / SIWE session'}
    if r.status_code == 409:
        return {'error': f'NOT_ACTIVE: {r.text[:150]}'}
    if r.status_code == 422:
        return {'error': f'MINTED_OUT: {r.text[:150]}'}
    if r.status_code == 400:
        return {'error': f'BAD_REQUEST: {r.text[:200]}'}
    if r.status_code != 200:
        return {'error': f'HTTP_{r.status_code}: {r.text[:200]}'}
    try:
        body = r.json()
    except Exception:
        return {'error': 'NOT_JSON: ' + r.text[:200]}
    to, data, value = body.get('to'), body.get('data'), body.get('value')
    if not to or not data or value is None:
        return {'error': f'MISSING_FIELDS: {json.dumps(body)[:300]}'}
    return {'to': to, 'data': data, 'value': value, 'chain': body.get('chain')}


def broadcast(tx, pk, rpc):
    """cast send; success = transactionHash-anchored regex only."""
    try:
        cmd = ['cast', 'send', tx['to'], '--data', tx['data'],
               '--value', tx['value'], '--private-key', pk,
               '--rpc-url', rpc, '--gas-limit', '300000']
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        out = r.stdout + r.stderr
        m = re.search(r'transactionHash\s+0x[0-9a-fA-F]{64}', out)
        if m:
            return {'ok': True, 'tx': re.search(r'0x[0-9a-fA-F]{64}', m.group(0)).group(0)}
        return {'ok': False, 'error': out[-300:].replace('\n', ' ')}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:200]}


def now_utc():
    return datetime.now(timezone.utc).strftime('%H:%M:%S')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sets', default='1-10')
    ap.add_argument('--quantity', type=int, default=1)
    ap.add_argument('--stage', choices=['wl', 'public'], default='wl')
    ap.add_argument('--slug', default='onchainsketches')
    ap.add_argument('--wl-start', type=int, default=0, help='UTC epoch WL open')
    ap.add_argument('--wl-end', type=int, default=0, help='UTC epoch WL close')
    ap.add_argument('--pub-start', type=int, default=0, help='UTC epoch public open')
    ap.add_argument('--pub-end', type=int, default=0, help='UTC epoch public close')
    ap.add_argument('--rpc', default=None, help='RPC URL (default: Alchemy RH)')
    ap.add_argument('--dry', action='store_true', help='build only, no broadcast')
    ap.add_argument('--watch', action='store_true', help='poll until open then mint')
    ap.add_argument('--watch-interval', type=float, default=10.0)
    ap.add_argument('--until', default='18:00:00', help='HH:MM:SS UTC stop time')
    ap.add_argument('--parallel', type=int, default=5)
    args = ap.parse_args()

    rpc = args.rpc
    if not rpc:
        for line in open(os.path.expanduser('~/.hermes/.env')):
            if line.startswith('ALCHEMY_API_KEY='):
                key = line.strip().split('=', 1)[1]
                if key:
                    rpc = f'https://robinhood-mainnet.g.alchemy.com/v2/{key}'
                    break
        if not rpc:
            rpc = 'https://rpc.mainnet.chain.robinhood.com'

    stage_epochs = {
        'wl': (args.wl_start, args.wl_end),
        'public': (args.pub_start, args.pub_end),
    }

    m = re.match(r'(\d+)-(\d+)', args.sets)
    if not m:
        print('--sets must be like 1-10')
        return
    s_lo, s_hi = int(m.group(1)), int(m.group(2))
    targets = list(range(s_lo, s_hi + 1))

    sets = load_sets()
    wallets = json.load(open(WALLETS_PATH))

    print(f'[{now_utc()}] Mode: {"DRY" if args.dry else "LIVE"} sets={s_lo}-{s_hi} '
          f'qty={args.quantity} stage={args.stage} slug={args.slug}')

    def mint_one(n):
        addr = wallets[n - 1]
        pk = get_pk(sets, n)
        print(f'[{now_utc()}] Set {n}: SIWE login...', flush=True)
        try:
            client = siwe_login(addr, pk)
            client.cookies.set('connected-account-server-hint',
                               Account.from_key(pk).address, domain='opensea.io')
            tx = build_mint_tx(client, addr, args.quantity, args.slug)
            if 'error' in tx:
                print(f'  ❌ Set {n}: {tx["error"]}')
                return {'set': n, 'ok': False, 'error': tx['error']}
            print(f'  ✅ Set {n}: tx built value={int(tx["value"],16)/1e18:.4f} ETH')
            if args.dry:
                return {'set': n, 'ok': True, 'dry': True, 'tx': tx}
            res = broadcast(tx, pk, rpc)
            if not res.get('ok'):
                time.sleep(2)
                res = broadcast(tx, pk, rpc)
            if res.get('ok'):
                print(f'  🚀 Set {n} MINTED: {res["tx"]}')
                return {'set': n, 'ok': True, 'tx': res['tx']}
            print(f'  ❌ Set {n} broadcast failed: {res.get("error","")[:120]}')
            return {'set': n, 'ok': False, 'error': res.get('error', '')}
        except Exception as e:
            print(f'  ❌ Set {n}: {str(e)[:120]}')
            return {'set': n, 'ok': False, 'error': str(e)[:120]}

    def run_once():
        results = []
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            futures = {ex.submit(mint_one, n): n for n in targets}
            for fut in as_completed(futures):
                try:
                    results.append(fut.result())
                except Exception as e:
                    n = futures[fut]
                    results.append({'set': n, 'ok': False, 'error': str(e)[:100]})
        results.sort(key=lambda r: r.get('set', 0))
        return results

    if args.watch:
        print(f'[{now_utc()}] 🎯 WATCHING {args.stage} until {args.until} UTC '
              f'(every {args.watch_interval}s)')
        attempts = 0
        while True:
            if now_utc() >= args.until:
                print(f'[{now_utc()}] Timeout — stopping without minting.')
                break
            active, info = probe_drop_active(args.stage, stage_epochs, args.slug)
            if not active:
                attempts += 1
                print(f'[{now_utc()}] ⏳ {args.stage} not active (attempt {attempts} · {info})', flush=True)
                time.sleep(args.watch_interval)
                continue
            print(f'[{now_utc()}] 🚀 {args.stage.upper()} ACTIVE! ({info}) minting...', flush=True)
            results = run_once()
            ok = sum(1 for r in results if r.get('ok'))
            print(f'[{now_utc()}] DONE: {ok}/{len(targets)} ok')
            print(json.dumps(results, indent=2, default=str))
            return

    results = run_once()
    ok = sum(1 for r in results if r.get('ok'))
    print(f'\n[{now_utc()}] DONE: {ok}/{len(targets)} ok')
    print(json.dumps(results, indent=2, default=str))


if __name__ == '__main__':
    main()
