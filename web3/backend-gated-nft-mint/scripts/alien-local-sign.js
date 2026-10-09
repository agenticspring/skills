#!/usr/bin/env node
/**
 * Local signer for backend-gated mints.
 *
 * Reads:
 *   /dev/shm/<keyfile>            private key (0600, in-memory staging)
 *   /tmp/alien-unsigned.json      {to, data, value, chainId} from backend /solve
 * Writes signed raw tx to stdout.
 *
 * Usage: NODE_PATH=/tmp/node_modules node alien-local-sign.js <keyfile>
 */
const { ethers } = require("ethers");
const fs = require("fs");

const KEYFILE = process.argv[2] || "/dev/shm/alien-pk";
const UNSIGNED_FILE = process.argv[3] || "/tmp/alien-unsigned.json";

const PK = fs.readFileSync(KEYFILE, "utf8").trim();
const unsigned = JSON.parse(fs.readFileSync(UNSIGNED_FILE, "utf8"));

// On Robinhood use the public RPC; swap for the project's chain RPC.
const provider = new ethers.JsonRpcProvider("https://rpc.mainnet.chain.robinhood.com");
const wallet = new ethers.Wallet(PK, provider);

(async () => {
  const fee = await provider.getFeeData();
  const nonce = await provider.getTransactionCount(wallet.address);
  const signed = await wallet.signTransaction({
    ...unsigned,
    gasLimit: 250000,
    maxFeePerGas: (fee.maxFeePerGas ?? fee.gasPrice) * 2n,
    maxPriorityFeePerGas: fee.maxPriorityFeePerGas ?? 10000000n,
    nonce,
    type: 2,
  });
  console.log(signed);
})().catch((e) => {
  console.error("SIGN_ERR " + String(e).slice(0, 300));
  process.exit(1);
});
