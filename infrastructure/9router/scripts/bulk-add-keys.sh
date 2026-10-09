#!/bin/bash
# Bulk add API keys to a 9Router provider
# Usage: bash bulk-add-keys.sh <provider_id> <keys_file> [name_prefix]
#
# Examples:
#   bash bulk-add-keys.sh xiaomi-mimo keys.txt mimo
#   bash bulk-add-keys.sh openai-compatible-chat-xxx... bai_keys.txt bai
#
# Features:
#   - Strips \r (Windows line endings) automatically
#   - Ensures trailing newline
#   - Progress reporting every 100 keys
#   - Error logging

set -euo pipefail

PROVIDER="${1:?Usage: $0 <provider_id> <keys_file> [name_prefix]}"
KEYS_FILE="${2:?Usage: $0 <provider_id> <keys_file> [name_prefix]}"
NAME_PREFIX="${3:-key}"

if [ ! -f "$KEYS_FILE" ]; then
    echo "ERROR: File not found: $KEYS_FILE"
    exit 1
fi

# Strip Windows line endings
sed -i 's/\r//g' "$KEYS_FILE"

# Ensure trailing newline
tail -c 1 "$KEYS_FILE" | grep -q '^$' || echo "" >> "$KEYS_FILE"

# Get CLI token
MACHINE_ID=$(cat ~/.9router/machine-id)
CLI_SECRET=$(cat ~/.9router/auth/cli-secret)
CLI_TOKEN=$(echo -n "${MACHINE_ID}9r-cli-auth${CLI_SECRET}" | sha256sum | cut -c1-16)

TOTAL=$(wc -l < "$KEYS_FILE")
echo "Adding $TOTAL keys to provider: $PROVIDER"
echo "Name prefix: $NAME_PREFIX"
echo "---"

SUCCESS=0
FAILED=0
COUNT=0

while IFS= read -r key; do
    [ -z "$key" ] && continue
    COUNT=$((COUNT + 1))
    
    RESPONSE=$(curl -s --max-time 5 -X POST http://localhost:20128/api/providers \
        -H "Content-Type: application/json" \
        -H "x-9r-cli-token: $CLI_TOKEN" \
        -d "{\"provider\": \"$PROVIDER\", \"name\": \"${NAME_PREFIX}-${COUNT}\", \"apiKey\": \"$key\"}" 2>&1)
    
    if echo "$RESPONSE" | grep -q '"id"'; then
        SUCCESS=$((SUCCESS + 1))
    else
        FAILED=$((FAILED + 1))
        if [ $FAILED -le 5 ]; then
            echo "FAIL [$COUNT]: $(echo "$RESPONSE" | head -c 100)"
        fi
    fi
    
    if [ $((COUNT % 100)) -eq 0 ]; then
        echo "Progress: $COUNT/$TOTAL (✅$SUCCESS ❌$FAILED)"
    fi
done < "$KEYS_FILE"

echo "---"
echo "COMPLETE: ✅$SUCCESS ❌$FAILED (Total: $COUNT)"
