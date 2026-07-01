#!/usr/bin/env bash
set -euo pipefail
curl --fail --silent http://localhost:8000/health
echo
curl --fail --silent 'http://localhost:8000/api/v1/tracks?limit=1'
echo
