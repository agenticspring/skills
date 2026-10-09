#!/bin/bash
# Generate 9Router CLI authentication token
# Usage: source this file or run directly
# Output: CLI_TOKEN env var

MACHINE_ID=$(cat ~/.9router/machine-id 2>/dev/null)
CLI_SECRET=$(cat ~/.9router/auth/cli-secret 2>/dev/null)

if [ -z "$MACHINE_ID" ] || [ -z "$CLI_SECRET" ]; then
  echo "ERROR: Could not read machine-id or cli-secret from ~/.9router/" >&2
  exit 1
fi

export CLI_TOKEN=$(echo -n "${MACHINE_ID}9r-cli-auth${CLI_SECRET}" | sha256sum | cut -c1-16)
echo "$CLI_TOKEN"
