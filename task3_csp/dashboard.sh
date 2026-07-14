#!/usr/bin/env bash
# Launch coral ui dashboard for the CSP Task 3 ablation.
# Usage: ./dashboard.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "Starting coral ui on http://127.0.0.1:8420 ..."
uv run --project ../coral-upstream coral ui --port 8420
