#!/usr/bin/env python3
"""Sign a SeaDrop v1.0 mint voucher for allowlist minting on Robinhood Chain.

Usage (invoke through the `terminal` tool):
  python3 sign_voucher.py --creator-pk 0x... --nft 0x... --minter 0x... \
      [--price 1] [--max-wallet 2] [--max-supply 100] [--salt 12345]

Outputs JSON to stdout: {"signature", "salt", "mint_params_list"}

EIP712 details (must match SeaDrop.sol exactly):
  domain:   name="SeaDrop" version="1.0" chainId=4663 verifyingContract=SeaDrop addr
  types:    MintParams(mintPrice, maxTotalMintableByWallet, startTime, endTime,
                       dropStageIndex, maxTokenSupplyForStage, feeBps,
                       restrictFeeRecipients)
            SignedMint(nftContract, minter, feeRecipient, mintParams, salt)
"""
import argparse
import json
import time

from eth_account import Account, messages

SEADROP = "0x00005EA00Ac477B1030CE78506496e8C2dE24bf5"
CHAIN_ID = 4663


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--creator-pk", required=True)
    ap.add_argument("--nft", required=True)
    ap.add_argument("--minter", required=True)
    ap.add_argument("--price", type=int, default=1)
    ap.add_argument("--max-wallet", type=int, default=2)
    ap.add_argument("--max-supply", type=int, default=100)
    ap.add_argument("--window-hours", type=int, default=24 * 37)
    ap.add_argument("--start-offset-sec", type=int, default=-3600,
                    help="voucher start = now + offset; must be <= stored validation start")
    ap.add_argument("--drop-stage-index", type=int, default=1)
    ap.add_argument("--salt", type=int, required=True)
    args = ap.parse_args()

    now = int(time.time())
    params = [
        args.price,
        args.max_wallet,
        now + args.start_offset_sec,
        now + args.window_hours * 3600,
        args.drop_stage_index,
        args.max_supply,
        0,       # feeBps
        True,    # restrictFeeRecipients — REQUIRED true by SeaDrop
    ]

    domain = {"name": "SeaDrop", "version": "1.0",
              "chainId": CHAIN_ID, "verifyingContract": SEADROP}
    types = {
        "MintParams": [
            {"name": "mintPrice", "type": "uint256"},
            {"name": "maxTotalMintableByWallet", "type": "uint256"},
            {"name": "startTime", "type": "uint256"},
            {"name": "endTime", "type": "uint256"},
            {"name": "dropStageIndex", "type": "uint256"},
            {"name": "maxTokenSupplyForStage", "type": "uint256"},
            {"name": "feeBps", "type": "uint256"},
            {"name": "restrictFeeRecipients", "type": "bool"},
        ],
        "SignedMint": [
            {"name": "nftContract", "type": "address"},
            {"name": "minter", "type": "address"},
            {"name": "feeRecipient", "type": "address"},
            {"name": "mintParams", "type": "MintParams"},
            {"name": "salt", "type": "uint256"},
        ],
    }
    names = [t["name"] for t in types["MintParams"]]
    message = {
        "nftContract": args.nft,
        "minter": args.minter,
        "feeRecipient": SEADROP,
        "mintParams": dict(zip(names, params)),
        "salt": args.salt,
    }
    msg = messages.encode_typed_data(full_message={
        "types": types, "primaryType": "SignedMint",
        "domain": domain, "message": message,
    })
    signed = Account.sign_message(msg, args.creator_pk)

    print(json.dumps({
        "signature": signed.signature.hex(),
        "salt": args.salt,
        "mint_params_list": params,
        "minter": args.minter,
    }))


if __name__ == "__main__":
    main()
