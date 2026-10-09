#!/usr/bin/env python3
"""L1 suite code audit: is the implementation canonical, who holds the upgrade key,
and can bridged funds leave?

Assembled from individually-verified calls (bytecode-hash baseline, EIP-1967 admin walk,
Safe owner/funder trace, DisputeGameFactory liveness). Edit TARGETS for the chain under
audit, then: python3 l1_suite_audit.py

Reads ALCHEMY_API_KEY from the environment or ~/.hermes/.env (never hardcode it).
"""
import os, sys, json, time
import requests
from Crypto.Hash import keccak

# ---------------------------------------------------------------- config
TARGETS = {
    # label: proxy address on Ethereum mainnet (EIP-1967 impl resolved automatically)
    "L1StandardBridgeProxy": "0xb8A393Ef40E6B8e1ca394a58D3CFB52C87756B4c",
    "OptimismPortal2Proxy":  "0xbA9938C0b96A70E6479661B915e7E481fE435ab2",
    "SystemConfigProxy":     "0xea20564c9cca1b2e35e88e7a75babcc74f7765c8",
    "SuperchainConfigProxy": "0x00811e2baea25111ca4b3b82d69af63b66f59197",
}
# which baseline contract each target corresponds to in the superchain registry
BASELINE_KEY = {
    "L1StandardBridgeProxy": "L1StandardBridgeProxy",
    "OptimismPortal2Proxy":  "OptimismPortalProxy",
    "SystemConfigProxy":     "SystemConfigProxy",
}
MAINNET_CHAIN_IDS = {"10": "OP", "8453": "Base", "7777777": "Zora", "480": "Worldchain",
                     "130": "Unichain", "1868": "Soneium", "57073": "Ink", "34443": "Mode",
                     "1135": "Lisk", "1750": "Metal", "5330": "Superseed"}

IMPL_SLOT  = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
ADMIN_SLOT = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
ZERO32 = "0x" + "0" * 64


def env(key):
    if os.environ.get(key):
        return os.environ[key]
    path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit(f"missing {key}")


RPC = "https://eth-mainnet.g.alchemy.com/v2/" + env("ALCHEMY_API_KEY")
_err = object()


def rpc(method, params, tries=6):
    """Returns _err on failure -- NEVER silently returns 0/[]. Zeros are the dangerous answer."""
    for a in range(tries):
        try:
            r = requests.post(RPC, json={"jsonrpc": "2.0", "id": 1,
                                         "method": method, "params": params}, timeout=45)
            if r.status_code == 429:
                time.sleep(1.0 + a); continue
            j = r.json()
            if "error" in j:
                return _err
            return j.get("result")
        except Exception:
            time.sleep(0.8)
    return _err


def keccak256_bytes(b):
    k = keccak.new(digest_bits=256); k.update(b); return "0x" + k.hexdigest()


def sel(sig):
    k = keccak.new(digest_bits=256); k.update(sig.encode()); return "0x" + k.hexdigest()[:8]


def topic(sig):
    k = keccak.new(digest_bits=256); k.update(sig.encode()); return "0x" + k.hexdigest()


def call(to, sig, args=""):
    r = rpc("eth_call", [{"to": to, "data": sel(sig) + args}, "latest"])
    return r if r is not _err else None


def code(addr):
    c = rpc("eth_getCode", [addr, "latest"])
    return c if (c is not _err and c and c != "0x") else None


def storage(addr, slot):
    v = rpc("eth_getStorageAt", [addr, slot, "latest"])
    if v is _err or not isinstance(v, str) or v == ZERO32:
        return None
    return "0x" + v[-40:]


def dec_addr(d):
    if not isinstance(d, str) or len(d) < 66:
        return None
    a = "0x" + d[-40:]
    return None if a == "0x" + "0" * 40 else a


def dec_uint(d):
    if not isinstance(d, str) or d in ("0x", ""):
        return None
    try:
        return int(d, 16)
    except Exception:
        return None


def dec_str(d):
    if not isinstance(d, str) or len(d) < 130:
        return None
    try:
        n = int(d[66:130], 16)
        return bytes.fromhex(d[130:130 + n * 2]).decode("utf-8", "ignore")
    except Exception:
        return None


def dec_addr_arr(d):
    if not isinstance(d, str) or len(d) < 130:
        return []
    off = int(d[2:66], 16) * 2 + 2
    n = int(d[off:off + 64], 16)
    return ["0x" + d[off + 64 + i * 64 + 24: off + 64 + i * 64 + 64] for i in range(n)]


# ---------------------------------------------------------------- 1. impls + hashes
print("=" * 70); print("1. IMPLEMENTATIONS"); print("=" * 70)
ours = {}
for label, proxy in TARGETS.items():
    impl = storage(proxy, IMPL_SLOT)
    ic = code(impl) if impl else None
    rec = {"proxy": proxy, "admin": storage(proxy, ADMIN_SLOT), "impl": impl,
           "impl_hash": keccak256_bytes(bytes.fromhex(ic[2:])) if ic else None,
           "impl_bytes": (len(ic) - 2) // 2 if ic else 0}
    ours[label] = rec
    print(f"  {label:24} proxy {proxy}")
    print(f"  {'':24} impl  {impl}  ({rec['impl_bytes']} B)")
    print(f"  {'':24} hash  {rec['impl_hash']}")
    print(f"  {'':24} admin {rec['admin']}")

# ---------------------------------------------------------------- 2. canonical baseline
print(); print("=" * 70); print("2. CANONICAL BASELINE (superchain registry)"); print("=" * 70)
try:
    reg = requests.get("https://raw.githubusercontent.com/ethereum-optimism/superchain-registry/"
                       "main/superchain/extra/addresses/addresses.json", timeout=60).json()
except Exception as e:
    reg = None
    print(f"  registry fetch failed: {e}")

baseline = {}   # registry key -> {impl_hash: [chains]}
if reg:
    for cid, name in MAINNET_CHAIN_IDS.items():
        entry = reg.get(cid) or {}
        for key in set(BASELINE_KEY.values()):
            addr = entry.get(key)
            if not addr:
                continue
            impl = storage(addr, IMPL_SLOT)
            ic = code(impl) if impl else None
            h = keccak256_bytes(bytes.fromhex(ic[2:])) if ic else None
            if h:
                baseline.setdefault(key, {}).setdefault(h, []).append(f"{name}({cid})")
    matched = {}
    for label, rec in ours.items():
        bkey = BASELINE_KEY.get(label)
        if not bkey:
            continue
        hits = baseline.get(bkey, {}).get(rec["impl_hash"])
        if hits:
            matched[label] = hits
            print(f"  {label}: IDENTICAL to {len(hits)} official chain(s): {', '.join(hits)}")
        else:
            print(f"  {label}: NO MATCH. Hashes seen in the wild:")
            for h, who in sorted(baseline.get(bkey, {}).items(),
                                 key=lambda x: -len(x[1]))[:6]:
                print(f"      {h}  x{len(who):2}  {who[0]}")
            print("      (a version difference is not automatically a red flag -- say so)")

# ---------------------------------------------------------------- 3. admin / safe / funders
print(); print("=" * 70); print("3. UPGRADE AUTHORITY"); print("=" * 70)


def trace_funders(addr):
    r = rpc("alchemy_getAssetTransfers",
            [{"toAddress": addr, "category": ["external", "internal"], "order": "asc",
              "maxCount": "0x19", "withMetadata": True}])
    if r is _err:
        return None
    return (r or {}).get("transfers", [])


seen_safe = set()
for label, rec in ours.items():
    pa = rec["admin"]
    if not pa or pa in seen_safe:
        continue
    seen_safe.add(pa)
    owner = dec_addr(call(pa, "owner()"))
    print(f"\n  ProxyAdmin {pa}")
    print(f"    owner() = {owner}")
    if not owner:
        print("    (no owner() -- check whether this ProxyAdmin is even the real admin)")
        continue
    thr = dec_uint(call(owner, "getThreshold()"))
    owners = dec_addr_arr(call(owner, "getOwners()"))
    print(f"    Safe version={dec_str(call(owner, 'VERSION()'))}  threshold={thr} of {len(owners)}")
    funders = {}
    for o in owners:
        oc = code(o)
        kind = "EOA" if not oc else f"CONTRACT {len(oc)//2-1}B"
        nonce = dec_uint(rpc("eth_getTransactionCount", [o, "latest"]))
        bal = rpc("eth_getBalance", [o, "latest"])
        bal = int(bal, 16) / 1e18 if isinstance(bal, str) else None
        print(f"      - {o}  {kind:16} nonce={nonce} bal={None if bal is None else round(bal,4)}")
        tf = trace_funders(o)
        if tf is None:
            print("        (funder trace failed -- do NOT report 'no funder')")
            continue
        for t in tf:
            f = (t.get("from") or "").lower()
            funders.setdefault(f, []).append(t.get("value") or 0)
    for f, vals in sorted(funders.items(), key=lambda x: -sum(x[1])):
        shared = "  <== SHARED BY MULTIPLE OWNERS" if len(vals) > 1 else ""
        print(f"        funder {f}  {sum(vals):.6f} ETH ({len(vals)}x){shared}")
    allf = [f for f, v in funders.items() if len(v) > 1]
    if allf and thr == len(owners) and len(owners) > 1:
        print(f"    !! {thr}-of-{len(owners)} Safe whose owners share funder {allf[0]}")
        print("       -> effectively a SINGLE KEY. The threshold is theatre.")

# ---------------------------------------------------------------- 4. withdrawal liveness
print(); print("=" * 70); print("4. WITHDRAWAL LIVENESS (can funds leave?)"); print("=" * 70)
portal = TARGETS.get("OptimismPortal2Proxy")
if portal:
    print(f"  paused()            = {dec_uint(call(portal, 'paused()'))}")
    gt = dec_uint(call(portal, "respectedGameType()"))
    print(f"  respectedGameType() = {gt}")
    dgf = dec_addr(call(portal, "disputeGameFactory()"))
    print(f"  disputeGameFactory  = {dgf}")
    print(f"  anchorStateRegistry = {dec_addr(call(portal, 'anchorStateRegistry()'))}")
    if dgf and gt is not None:
        n = dec_uint(call(dgf, "gameCount()"))
        print(f"  gameCount()         = {n}")
        impl = dec_addr(call(dgf, "gameImpls(uint32)", f"{gt:064x}"))
        print(f"  gameImpls({gt})      = {impl}")
        if n == 0:
            print("  ==> NO game ever created => NO withdrawal can be proven => FUNDS ONE-WAY.")
            print("      (contracts being fully wired does not mean a proposer is running)")
    else:
        print("  (could not resolve DGF / game type -- investigate, do not assume 0)")

# ---------------------------------------------------------------- 5. upgrade history
print(); print("=" * 70); print("5. UPGRADE HISTORY (zero from a FAILED call is not zero)"); print("=" * 70)
UPG = topic("Upgraded(address)")
print("  Read these from tx RECEIPTS or an Etherscan-compatible endpoint with a topic0 filter:")
print(f"    {UPG}")
for label, rec in ours.items():
    txs = rpc("eth_getLogs", [{"address": rec["proxy"], "topics": [UPG],
                               "fromBlock": "0x0", "toBlock": "latest"}])
    if txs is _err:
        print(f"  {label:24} !! getLogs FAILED (range too large) -- do not report as 0")
        continue
    print(f"  {label:24} {len(txs)} Upgraded event(s)")
    for l in txs[:6]:
        print(f"      blk {int(l['blockNumber'],16)} tx {l['transactionHash'][:18]}… "
              f"impl 0x{l['topics'][1][-40:]}")
print("\n  Reminder: 2 Upgraded in ONE tx at the DEPLOY block is the OPContractsManagerV2")
print("  placeholder->real pattern, NOT an upgrade. Only a LATER block is an upgrade.")

json.dump({"ours": ours, "matched": locals().get("matched", {})},
          open("/tmp/l1_suite_audit.json", "w"), indent=1)
print("\n-> /tmp/l1_suite_audit.json")
