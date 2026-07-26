#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:?usage: rollback.sh <staging|production>}"
LAST_GOOD_SHA_FILE=".last_deployed_sha_${ENVIRONMENT}"

if [[ ! -f "$LAST_GOOD_SHA_FILE" ]]; then
  echo "No recorded last-good SHA for ${ENVIRONMENT}. Check deploy history manually."
  exit 1
fi

PREVIOUS_SHA=$(cat "$LAST_GOOD_SHA_FILE")
echo "Rolling ${ENVIRONMENT} back to ${PREVIOUS_SHA}..."

git checkout "$PREVIOUS_SHA"
./deploy.sh "$ENVIRONMENT"

echo "Rollback triggered. Now verify:"
echo "  curl -f https://${ENVIRONMENT}.example.com/healthz"
echo "Then check error-rate dashboard before declaring the incident resolved."
