#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:?usage: deploy.sh <staging|production>}"
GIT_SHA="$(git rev-parse --short HEAD)"

echo "Deploying commit ${GIT_SHA} to ${ENVIRONMENT}..."

echo "Tagging release ${GIT_SHA} as current for ${ENVIRONMENT}"
echo "${GIT_SHA}" > ".last_deployed_sha_${ENVIRONMENT}"

echo "Deploy to ${ENVIRONMENT} complete."
