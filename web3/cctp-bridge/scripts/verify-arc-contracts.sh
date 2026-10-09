#!/bin/bash
# Verify ARC Mainnet CCTP contracts via raw JSON-RPC calls
# Usage: bash verify-arc-contracts.sh [RPC_URL]
#
# Outputs: chain info, USDC metadata, contract deployment status, proxy details
set -euo pipefail
RPC="${1:-https://real-pump-soon-trust-me-bro-again.poptyedev.com/}"
call() {
    local data="$1" label="$2"
    local result=$(curl -sf -X POST "$RPC" -H "Content-Type: application/json" \
        -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_call\",\"params\":[{\"to\":\"${data%%|*}\",\"data\":\"${data##*|}\"},\"latest\"],\"id\":1}" 2>/dev/null)
    if echo "$result" | grep -q '"error"'; then
        echo "  $label: REVERTED"
    else
        local hex=$(echo "$result" | grep -o '"result":"[^"]*"' | cut -d'"' -f4)
        echo "  $label: $hex"
    fi
}
echo "=== ARC Mainnet Contract Verification ==="
echo "RPC: $RPC"
echo ""
echo "--- Chain Info ---"
CHAIN=$(curl -sf -X POST "$RPC" -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' | grep -o '"result":"[^"]*"' | cut -d'"' -f4)
echo "  Chain ID: $CHAIN"
BLOCK=$(curl -sf -X POST "$RPC" -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' | grep -o '"result":"[^"]*"' | cut -d'"' -f4)
echo "  Block: $BLOCK"
echo ""
USDC="0x3600000000000000000000000000000000000000"
echo "--- USDC ($USDC) ---"
call "${USDC}|0x06fdde03" "name()"
call "${USDC}|0x95d89b41" "symbol()"
call "${USDC}|0x313ce567" "decimals()"
call "${USDC}|0x18160ddd" "totalSupply()"
echo ""
TM="0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d"
echo "--- TokenMessengerV2 ---"
call "${TM}|0x5c60da1b" "implementation()"
call "${TM}|0x8da5cb5b" "owner()"
call "${TM}|0xe30c3978" "pendingImplementation()"
call "${TM}|0x21121c76" "localMessageTransmitter()"
call "${TM}|0x39f9a10b" "tokenMinter()"
echo ""
MT="0x81D40F21F12A8F0E3252Bccb954D722d4c464B64"
echo "--- MessageTransmitterV2 ---"
call "${MT}|0x5c60da1b" "implementation()"
call "${MT}|0x8da5cb5b" "owner()"
call "${MT}|0x54fd4d50" "version()"
call "${MT}|0xe38be128" "localDomain()"
call "${MT}|0x2398e36a" "messageBodyVersion()"
call "${MT}|0xf19873ee" "maxMessageBodySize()"
echo ""
TMI="0xfd78EE919681417d192449715b2594ab58f5D002"
echo "--- TokenMinterV2 ---"
call "${TMI}|0x8da5cb5b" "owner()"
echo ""
echo "--- USDC Balance in TokenMessengerV2 ---"
BAL=$(curl -sf -X POST "$RPC" -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_call\",\"params\":[{\"to\":\"$USDC\",\"data\":\"0x70a0823100000000000000000000000028b5a0e9c621a5badaa536219b3a228c8168cf5d\"},\"latest\"],\"id\":1}" | grep -o '"result":"[^"]*"' | cut -d'"' -f4)
echo "  balanceOf(TM): $(printf '%d' "$BAL") raw units"
echo "Done."
