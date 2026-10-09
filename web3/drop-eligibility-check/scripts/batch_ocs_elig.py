#!/usr/bin/env python3
"""
Batch OpenSea drop eligibility check for Hermes wallet sets (Set 1..N).

Derives PKs from the mnemonic file, SIWE-logins per wallet, and queries the
OpenSea DropEligibilityQuery persisted hash. Writes structured JSON results.

Usage:
  python3 batch_ocs_elig.py <slug> [--start 1] [--end 100] [--delay 3]

Requires: pip install httpx eth-account
"""
import sys, os, json, time, re, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opensea_eligibility import siwe_login, check_eligibility_graphql

from eth_account import Account
Account.enable_unaudited_hdwallet_features()  # needed for from_mnemonic

MNE_PATH = '/root/.hermes/.credintial/.springwallet'
WALLETS_PATH = '/tmp/ocs_wallets.json'  # list of expected addresses, index 0 = Set 1


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('slug')
    ap.add_argument('--start', type=int, default=1)
    ap.add_argument('--end', type=int, default=100)
    ap.add_argument('--delay', type=float, default=3.0)
    ap.add_argument('--out', default='/tmp/ocs_eligibility_results.json')
    args = ap.parse_args()

    sets = load_sets()
    wallets = json.load(open(WALLETS_PATH))
    assert len(wallets) >= args.end, 'manifest too short'

    results = []
    for i in range(args.start, args.end + 1):
        mnemonic = sets.get(i)
        if not mnemonic:
            results.append({'set': i, 'error': 'no mnemonic'})
            continue
        acct = Account.from_mnemonic(mnemonic)
        pk = acct.key.hex()
        addr = acct.address.lower()
        expected = wallets[i - 1].lower()
        if addr != expected:
            results.append({'set': i, 'error': f'ADDR_MISMATCH expected={expected} got={addr}'})
            print(f'SET {i}: ADDR MISMATCH', flush=True)
            continue
        try:
            client = siwe_login(acct.address, pk)  # sets access_token + hint cookie
            data = check_eligibility_graphql(client, acct.address, args.slug)
            drop = data.get('dropBySlug') or data.get('drop') or {}
            stages = []
            for s in drop.get('stages', []):
                price = s.get('eligiblePrice') or {}
                stages.append({
                    'type': s.get('stageType', '?'),
                    'eligible': bool(s.get('isEligible')),
                    'max': s.get('maxTotalMintableByWallet'),
                    'price_wei': (price.get('token') or {}).get('unit', 0),
                })
            results.append({'set': i, 'address': addr, 'stages': stages})
            summary = '/'.join('Y' if s['eligible'] else 'N' for s in stages)
            print(f'SET {i}: {summary} | {addr[:10]}...', flush=True)
        except Exception as e:
            results.append({'set': i, 'address': addr, 'error': str(e)[:100]})
            print(f'SET {i}: ERROR {e}', flush=True)
        time.sleep(args.delay)

    with open(args.out, 'w') as f:
        json.dump(results, f, indent=2)

    ok = [r for r in results if 'stages' in r]
    err = [r for r in results if 'error' in r]
    elig = sum(1 for r in ok if any(s['eligible'] for s in r['stages']))
    print(f'\nTotal: {len(ok)}, Errors: {len(err)}, Eligible (any stage): {elig}')
    print(f'Results saved to {args.out}')


if __name__ == '__main__':
    main()
